// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Characterization tests for the Lyria-3 Interactions route.
//
// These tests capture the CURRENT (pre-refactor) behavior of the Lyria-3
// generation path so that a subsequent behavior-preserving refactor onto the
// shared mcp-common Interactions seam can be proven to preserve it (parity):
// they pass on unmodified `main` AND must pass unchanged after the refactor.
//
// They drive the real production code path — including ADC / oauth2 — without a
// real GCP backend by:
//   - minting a self-signed service-account credential (RSA key generated in the
//     test) whose token_uri points at a local httptest server, so
//     google.FindDefaultCredentials succeeds and mints a token from our fake
//     token endpoint; and
//   - injecting that same TLS test server's http.Client via the standard
//     oauth2.HTTPClient context key, so every request (token mint + the
//     Interactions POST) is routed to the test server and trusts its cert.
//
// The request-envelope assertions deliberately do NOT assert the ABSENCE of the
// "Api-Revision" header: the shared seam always sends it (the one intended,
// benign wire delta introduced by the refactor), so leaving it unasserted keeps
// these tests green both pre- and post-refactor.
package main

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"

	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"golang.org/x/oauth2"
)

const (
	testProjectID = "test-project"
	// The Lyria-3 route pins the location to "global" ("Cardolan"); the request
	// path is asserted against this.
	wantInteractionsPath = "/v1beta1/projects/" + testProjectID + "/locations/global/interactions"
)

// capturedRequest records what the fake Interactions endpoint observed so the
// tests can assert the request envelope.
type capturedRequest struct {
	method        string
	path          string
	userProject   string
	contentType   string
	authorization string
	body          map[string]interface{}
}

// interactionsTestServer is a fake that serves BOTH the oauth2 token endpoint
// (/token) and the Interactions endpoint (everything else). It returns the
// provided interactions response body and, when sherlogLink != "", the
// x-goog-sherlog-link response header.
func newInteractionsTestServer(t *testing.T, respBody string, sherlogLink string) (*httptest.Server, *capturedRequest) {
	t.Helper()
	captured := &capturedRequest{}
	mux := http.NewServeMux()
	mux.HandleFunc("/token", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"access_token":"fake-access-token","token_type":"Bearer","expires_in":3600}`))
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		captured.method = r.Method
		captured.path = r.URL.Path
		captured.userProject = r.Header.Get("x-goog-user-project")
		captured.contentType = r.Header.Get("Content-Type")
		captured.authorization = r.Header.Get("Authorization")
		var body map[string]interface{}
		_ = json.NewDecoder(r.Body).Decode(&body)
		captured.body = body

		w.Header().Set("Content-Type", "application/json")
		if sherlogLink != "" {
			w.Header().Set("x-goog-sherlog-link", sherlogLink)
		}
		_, _ = w.Write([]byte(respBody))
	})
	ts := httptest.NewTLSServer(mux)
	t.Cleanup(ts.Close)
	return ts, captured
}

// fakeADCContext wires up a service-account credential whose token endpoint is
// the given test server, and returns a context whose oauth2 HTTP client is the
// test server's (cert-trusting) client. It also sets the global appConfig to
// point at the test server as the Interactions API endpoint. Both are the exact
// mechanisms the production code threads through, so this exercises the real
// path without a real backend.
func fakeADCContext(t *testing.T, ts *httptest.Server, cfg *common.Config) context.Context {
	t.Helper()

	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("rsa.GenerateKey: %v", err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(key),
	})

	sa := map[string]string{
		"type":                        "service_account",
		"project_id":                  testProjectID,
		"private_key_id":              "test-key-id",
		"private_key":                 string(keyPEM),
		"client_email":                "test-sa@" + testProjectID + ".iam.gserviceaccount.com",
		"client_id":                   "1234567890",
		"auth_uri":                    ts.URL + "/o/oauth2/auth",
		"token_uri":                   ts.URL + "/token",
		"auth_provider_x509_cert_url": ts.URL + "/oauth2/v1/certs",
		"client_x509_cert_url":        ts.URL + "/robot/v1/metadata/x509/test-sa",
	}
	saJSON, err := json.Marshal(sa)
	if err != nil {
		t.Fatalf("marshal sa: %v", err)
	}
	credPath := filepath.Join(t.TempDir(), "sa.json")
	if err := os.WriteFile(credPath, saJSON, 0600); err != nil {
		t.Fatalf("write sa: %v", err)
	}
	t.Setenv("GOOGLE_APPLICATION_CREDENTIALS", credPath)

	// The Interactions route builds its URL as https://<ApiEndpoint>/v1beta1/...
	// so ApiEndpoint must be host:port only (no scheme).
	cfg.ApiEndpoint = strings.TrimPrefix(ts.URL, "https://")
	if cfg.ProjectID == "" {
		cfg.ProjectID = testProjectID
	}
	appConfig = cfg

	// Route both the token mint and the Interactions POST through the test
	// server's cert-trusting client via the standard oauth2 context key.
	return context.WithValue(context.Background(), oauth2.HTTPClient, ts.Client())
}

// flatAudioResponse builds a Lyria-style flat outputs[] response body carrying
// base64 audio.
func flatAudioResponse(mimeType string, audio []byte) string {
	b64 := base64.StdEncoding.EncodeToString(audio)
	return fmt.Sprintf(`{
		"id": "lyria-char-1",
		"object": "interaction",
		"status": "completed",
		"role": "model",
		"outputs": [{"type": "audio", "mime_type": %q, "data": %q}]
	}`, mimeType, b64)
}

// TestChar_Lyria3_RequestEnvelope pins the CURRENT request envelope of the
// Lyria-3 Interactions route: POST to the global interactions path with body
// {model, input:[{type:"text", text:<prompt>}], store:false} and the
// x-goog-user-project header. It intentionally does not assert the Api-Revision
// header's absence (the shared seam adds it — the one documented wire delta).
func TestChar_Lyria3_RequestEnvelope(t *testing.T) {
	audio := []byte("RIFFchar-envelope-wav")
	ts, captured := newInteractionsTestServer(t, flatAudioResponse("audio/wav", audio), "")
	ctx := fakeADCContext(t, ts, &common.Config{ProjectID: testProjectID})

	const prompt = "a calm piano melody"
	_, _, err := generateAudioWithInteractions(ctx, "lyria-3-clip-preview", prompt)
	if err != nil {
		t.Fatalf("generateAudioWithInteractions returned error: %v", err)
	}

	if captured.method != http.MethodPost {
		t.Errorf("method = %q, want POST", captured.method)
	}
	if captured.path != wantInteractionsPath {
		t.Errorf("path = %q, want %q", captured.path, wantInteractionsPath)
	}
	if captured.userProject != testProjectID {
		t.Errorf("x-goog-user-project = %q, want %q", captured.userProject, testProjectID)
	}
	if captured.contentType != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", captured.contentType)
	}
	if got, _ := captured.body["model"].(string); got != "lyria-3-clip-preview" {
		t.Errorf("body.model = %q, want lyria-3-clip-preview", got)
	}
	if store, ok := captured.body["store"].(bool); !ok || store {
		t.Errorf("body.store = %v, want false", captured.body["store"])
	}
	input, ok := captured.body["input"].([]interface{})
	if !ok || len(input) != 1 {
		t.Fatalf("body.input = %v, want a single-element array", captured.body["input"])
	}
	item, _ := input[0].(map[string]interface{})
	if got, _ := item["type"].(string); got != "text" {
		t.Errorf("body.input[0].type = %q, want text", got)
	}
	if got, _ := item["text"].(string); got != prompt {
		t.Errorf("body.input[0].text = %q, want %q", got, prompt)
	}
}

// TestChar_Lyria3_AudioDecoded pins that flat outputs[] base64 audio is decoded
// to the exact original bytes.
func TestChar_Lyria3_AudioDecoded(t *testing.T) {
	audio := []byte{0x52, 0x49, 0x46, 0x46, 0x00, 0x01, 0x02, 0x03, 0xFF, 0xFE}
	ts, _ := newInteractionsTestServer(t, flatAudioResponse("audio/wav", audio), "")
	ctx := fakeADCContext(t, ts, &common.Config{ProjectID: testProjectID})

	got, _, err := generateAudioWithInteractions(ctx, "lyria-3-clip-preview", "prompt")
	if err != nil {
		t.Fatalf("generateAudioWithInteractions returned error: %v", err)
	}
	if string(got) != string(audio) {
		t.Errorf("decoded audio = %v, want %v", got, audio)
	}
}

// TestChar_Lyria3_SherlogCaptureEnabled pins that x-goog-sherlog-link is
// captured when ENABLE_OPTIONAL_HEADER_CAPTURE is enabled, and that an
// Authorization bearer header is injected on that path.
func TestChar_Lyria3_SherlogCaptureEnabled(t *testing.T) {
	const wantSherlog = "https://sherlog.example/abc123"
	audio := []byte("sherlog-on")
	ts, captured := newInteractionsTestServer(t, flatAudioResponse("audio/wav", audio), wantSherlog)
	ctx := fakeADCContext(t, ts, &common.Config{ProjectID: testProjectID, EnableOptionalHeaderCapture: true})

	_, sherlog, err := generateAudioWithInteractions(ctx, "lyria-3-clip-preview", "prompt")
	if err != nil {
		t.Fatalf("generateAudioWithInteractions returned error: %v", err)
	}
	if sherlog != wantSherlog {
		t.Errorf("sherlogLink = %q, want %q", sherlog, wantSherlog)
	}
	if !strings.HasPrefix(captured.authorization, "Bearer ") {
		t.Errorf("Authorization = %q, want a Bearer token when header capture is enabled", captured.authorization)
	}
}

// TestChar_Lyria3_SherlogCaptureDisabled pins that with header capture disabled
// the sherlog link is NOT captured (returned empty).
func TestChar_Lyria3_SherlogCaptureDisabled(t *testing.T) {
	const sherlogHeader = "https://sherlog.example/should-be-ignored"
	audio := []byte("sherlog-off")
	ts, _ := newInteractionsTestServer(t, flatAudioResponse("audio/wav", audio), sherlogHeader)
	ctx := fakeADCContext(t, ts, &common.Config{ProjectID: testProjectID, EnableOptionalHeaderCapture: false})

	_, sherlog, err := generateAudioWithInteractions(ctx, "lyria-3-clip-preview", "prompt")
	if err != nil {
		t.Fatalf("generateAudioWithInteractions returned error: %v", err)
	}
	if sherlog != "" {
		t.Errorf("sherlogLink = %q, want empty when header capture is disabled", sherlog)
	}
}

// TestChar_Lyria3_HandlerResultAndFilename pins the end-to-end tool behavior of
// the Lyria-3 route through the public handler: the result text, the direct
// audio content (when neither GCS nor local path is set), and the generated
// output filename pattern (lyria_output_<id>.wav) via a local save.
func TestChar_Lyria3_HandlerResultAndFilename(t *testing.T) {
	audio := []byte("handler-level-audio-bytes")
	ts, _ := newInteractionsTestServer(t, flatAudioResponse("audio/wav", audio), "")
	ctx := fakeADCContext(t, ts, &common.Config{ProjectID: testProjectID})

	// (1) No GCS, no local path -> direct audio content returned + result text.
	reqDirect := mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Arguments: map[string]interface{}{
				"prompt":   "a bright melody",
				"model_id": "lyria-3-clip-preview",
			},
		},
	}
	res, err := lyriaGenerateMusicHandler(ctx, reqDirect)
	if err != nil {
		t.Fatalf("handler returned error: %v", err)
	}
	if res.IsError {
		t.Fatalf("handler result IsError=true: %+v", res.Content)
	}
	var sawText, sawAudio bool
	for _, c := range res.Content {
		switch cc := c.(type) {
		case mcp.TextContent:
			sawText = true
			if !strings.Contains(cc.Text, "Music generation completed in") {
				t.Errorf("result text = %q, want it to contain 'Music generation completed in'", cc.Text)
			}
		case mcp.AudioContent:
			sawAudio = true
			if cc.MIMEType != audioMIMEType {
				t.Errorf("audio MIME = %q, want %q", cc.MIMEType, audioMIMEType)
			}
			decoded, decErr := base64.StdEncoding.DecodeString(cc.Data)
			if decErr != nil {
				t.Errorf("audio content not valid base64: %v", decErr)
			} else if string(decoded) != string(audio) {
				t.Errorf("returned audio = %q, want %q", decoded, audio)
			}
		}
	}
	if !sawText {
		t.Error("expected a text content part")
	}
	if !sawAudio {
		t.Error("expected direct audio content when neither GCS nor local path is set")
	}

	// (2) Local path, no file_name -> generated filename pattern lyria_output_<id>.wav.
	dir := t.TempDir()
	reqLocal := mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Arguments: map[string]interface{}{
				"prompt":     "a bright melody",
				"model_id":   "lyria-3-clip-preview",
				"local_path": dir,
			},
		},
	}
	resLocal, err := lyriaGenerateMusicHandler(ctx, reqLocal)
	if err != nil {
		t.Fatalf("handler(local) returned error: %v", err)
	}
	if resLocal.IsError {
		t.Fatalf("handler(local) IsError=true: %+v", resLocal.Content)
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("read local dir: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("local dir has %d files, want 1", len(entries))
	}
	filenamePattern := regexp.MustCompile(`^lyria_output_.+\.wav$`)
	if name := entries[0].Name(); !filenamePattern.MatchString(name) {
		t.Errorf("generated filename = %q, want to match %s", name, filenamePattern)
	}
	saved, err := os.ReadFile(filepath.Join(dir, entries[0].Name()))
	if err != nil {
		t.Fatalf("read saved file: %v", err)
	}
	if string(saved) != string(audio) {
		t.Errorf("saved audio = %q, want %q", saved, audio)
	}
	// When local path IS set, audio must NOT be returned directly.
	for _, c := range resLocal.Content {
		if _, ok := c.(mcp.AudioContent); ok {
			t.Error("audio content should NOT be returned directly when local_path is set")
		}
	}
}

// TestChar_Lyria_DispatchGuard pins the two-route dispatch key: the Lyria-3
// models route via "interactions" while the Lyria-2 (:predict) model routes via
// "prediction". This guards that the refactor does NOT fold the Lyria-2 predict
// route onto the shared seam.
func TestChar_Lyria_DispatchGuard(t *testing.T) {
	cases := []struct {
		model            string
		wantEndpointType string
	}{
		{"lyria-002", "prediction"},              // Lyria-2 :predict route — must stay
		{"lyria-3-clip-preview", "interactions"}, // Lyria-3 route — moves to the seam
		{"lyria-3-pro-preview", "interactions"},
	}
	for _, tc := range cases {
		info, found := common.ResolveLyriaModel(tc.model, false)
		if !found {
			t.Errorf("ResolveLyriaModel(%q) not found", tc.model)
			continue
		}
		if info.EndpointType != tc.wantEndpointType {
			t.Errorf("model %q EndpointType = %q, want %q", tc.model, info.EndpointType, tc.wantEndpointType)
		}
	}
}
