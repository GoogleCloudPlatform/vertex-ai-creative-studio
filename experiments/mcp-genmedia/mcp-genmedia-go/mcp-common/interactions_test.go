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

package common

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	interactions "github.com/ghchinoy/cloud-interactions-go"
)

// newTestClient builds a libInteractionsClient whose adopted library client points
// at the given test server, mirroring the production wiring (BaseURL, injected
// HTTPClient, x-goog-user-project, pinned Api-Revision) without ADC or real network.
func newTestClient(baseURL string, httpClient *http.Client) *libInteractionsClient {
	inner := interactions.NewClient(baseURL)
	inner.HTTPClient = httpClient
	inner.WithUserProject("test-project")
	inner.WithAPIRevision(DefaultInteractionsAPIRevision)
	return &libInteractionsClient{inner: inner}
}

// TestInteractionsClientCreate exercises the library-backed transport against a
// TLS httptest server: it verifies the request path, load-bearing headers, and
// body shape, and that the drift-shaped response is translated and mapped (no ADC
// / no network required).
func TestInteractionsClientCreate(t *testing.T) {
	b64 := base64.StdEncoding.EncodeToString(sampleMP4)

	var gotPath, gotUserProject, gotAPIRevision, gotContentType string
	var gotBody InteractionRequest

	ts := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotUserProject = r.Header.Get("x-goog-user-project")
		gotAPIRevision = r.Header.Get("Api-Revision")
		gotContentType = r.Header.Get("Content-Type")
		body, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(body, &gotBody)

		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, omniResponseJSON(b64))
	}))
	defer ts.Close()

	baseURL := ts.URL + "/v1beta1/projects/test-project/locations/global/interactions"
	c := newTestClient(baseURL, ts.Client())

	req := buildOmniRequest("gemini-omni-flash-preview", OmniParams{Prompt: "a red balloon"})
	resp, err := c.Create(context.Background(), req)
	if err != nil {
		t.Fatalf("Create returned error: %v", err)
	}

	if gotPath != "/v1beta1/projects/test-project/locations/global/interactions" {
		t.Errorf("request path = %q", gotPath)
	}
	if gotUserProject != "test-project" {
		t.Errorf("x-goog-user-project = %q, want test-project", gotUserProject)
	}
	if gotAPIRevision != DefaultInteractionsAPIRevision {
		t.Errorf("Api-Revision = %q, want %q", gotAPIRevision, DefaultInteractionsAPIRevision)
	}
	if gotContentType != "application/json" {
		t.Errorf("Content-Type = %q", gotContentType)
	}
	if len(gotBody.ResponseModalities) != 2 || gotBody.ResponseModalities[0] != "text" {
		t.Errorf("server saw response_modalities = %v, want lowercase [text video]", gotBody.ResponseModalities)
	}

	result, err := mapOmniResponse(resp)
	if err != nil {
		t.Fatalf("mapOmniResponse returned error: %v", err)
	}
	if len(result.Videos) != 1 || !hasFtypBox(result.Videos[0]) {
		t.Errorf("expected 1 ftyp-valid video, got %d", len(result.Videos))
	}
}

// TestInteractionsClientCreateAPIError verifies a 4xx body is surfaced verbatim by
// the adopted library and preserved through the seam.
func TestInteractionsClientCreateAPIError(t *testing.T) {
	ts := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
		_, _ = io.WriteString(w, `{"error":{"code":400,"message":"invalid_request"}}`)
	}))
	defer ts.Close()

	c := newTestClient(ts.URL, ts.Client())

	_, err := c.Create(context.Background(), buildOmniRequest("m", OmniParams{Prompt: "x"}))
	if err == nil {
		t.Fatal("expected an error for a 400 response, got nil")
	}
	if !strings.Contains(err.Error(), "invalid_request") {
		t.Errorf("error should surface the API body verbatim, got: %v", err)
	}
}

// TestFromLibResponseDrift proves the adopted library decodes the observed live
// drift (findings §3) and that fromLibResponse + mapOmniResponse recover the video.
// The library ignores the wire's created/updated timestamps and the thought step's
// array "summary"/"signature" (unknown fields), which must not be fatal.
func TestFromLibResponseDrift(t *testing.T) {
	b64 := base64.StdEncoding.EncodeToString(sampleMP4)

	var libResp interactions.InteractionResponse
	if err := json.Unmarshal([]byte(omniResponseJSON(b64)), &libResp); err != nil {
		t.Fatalf("library failed to decode drift response: %v", err)
	}
	if libResp.CreateTime != nil || libResp.UpdateTime != nil {
		t.Errorf("expected library to drop created/updated (create_time/update_time tags); got %v/%v", libResp.CreateTime, libResp.UpdateTime)
	}

	resp := fromLibResponse(&libResp)
	if resp.Status != "completed" {
		t.Errorf("Status = %q, want completed", resp.Status)
	}
	if len(resp.Steps) != 2 {
		t.Fatalf("len(Steps) = %d, want 2", len(resp.Steps))
	}

	result, err := mapOmniResponse(resp)
	if err != nil {
		t.Fatalf("mapOmniResponse returned error: %v", err)
	}
	if result.ThoughtSteps != 1 {
		t.Errorf("ThoughtSteps = %d, want 1", result.ThoughtSteps)
	}
	if len(result.Videos) != 1 || !hasFtypBox(result.Videos[0]) {
		t.Fatalf("expected 1 ftyp-valid video recovered via the library path, got %d", len(result.Videos))
	}
	if result.VideoMimeTypes[0] != "video/mp4" {
		t.Errorf("VideoMimeTypes[0] = %q, want video/mp4", result.VideoMimeTypes[0])
	}
}
