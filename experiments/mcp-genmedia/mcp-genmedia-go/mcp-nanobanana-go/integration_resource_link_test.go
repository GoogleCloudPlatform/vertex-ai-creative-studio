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

package main

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"

	common "github.com/GoogleCloudPlatform/genmedia-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// TestIntegrationNanobananaResourceLinks asserts the #483 Phase-1 contract on a
// GCS sink: the result content is [text, resource_link, ...], one resource_link
// per generated image, each with the gs:// uri as identity and the correct
// mimeType — and the leading TextContent is preserved.
//
// The default run is network-free: it injects the persistence seam
// (persistMediaOutputs) with a fake that simulates a successful GCS upload, so
// CI without credentials still exercises the full response-building wiring. The
// live leg (real genai + real GCS upload) is gated behind GENMEDIA_BUCKET so it
// only runs where creds/bucket exist (project ghchinoy-genai-sa).
func TestIntegrationNanobananaResourceLinks(t *testing.T) {
	t.Run("network-free GCS sink -> text + resource_link per image", func(t *testing.T) {
		orig := persistMediaOutputs
		t.Cleanup(func() { persistMediaOutputs = orig })

		// Fake seam: simulate a GCS upload, returning a gs:// URI derived from the
		// requested FileName so the resource_link uri/name are deterministic.
		persistMediaOutputs = func(_ context.Context, art common.MediaArtifact, _, gcsBucketURI string, _ time.Duration) (common.PersistedMedia, error) {
			return common.PersistedMedia{
				GCSURI:    fmt.Sprintf("%s/%s", strings.TrimSuffix(gcsBucketURI, "/"), art.FileName),
				GCSBucket: "fake-bucket",
				GCSObject: art.FileName,
				SignedURL: "https://storage.googleapis.com/fake-signed-url",
			}, nil
		}

		resp := imageResponse(
			textPart("here you go"),
			imagePart("image/png", []byte("alpha")),
			imagePart("image/png", []byte("bravo")),
		)
		res, err := processImageResponse(context.Background(), resp,
			map[string]any{"output_filename": "hero.png"}, "", "gs://fake-bucket/nanobanana_outputs")
		if err != nil {
			t.Fatalf("processImageResponse error: %v", err)
		}

		if len(res.Content) != 3 {
			t.Fatalf("content len = %d, want 3 (text + 2 links)", len(res.Content))
		}

		// content[0] is the (unchanged) text summary.
		text, ok := res.Content[0].(mcp.TextContent)
		if !ok {
			t.Fatalf("content[0] is %T, want mcp.TextContent", res.Content[0])
		}
		if !strings.Contains(text.Text, "here you go") {
			t.Errorf("text summary missing model text; got %q", text.Text)
		}

		// content[1..n] are resource_links, in order, with gs:// uri + mimeType.
		wantURIs := []string{
			"gs://fake-bucket/nanobanana_outputs/hero_1.png",
			"gs://fake-bucket/nanobanana_outputs/hero_2.png",
		}
		wantDescs := []string{"nanobanana output 1 of 2", "nanobanana output 2 of 2"}
		for i := 1; i < len(res.Content); i++ {
			rl, ok := res.Content[i].(mcp.ResourceLink)
			if !ok {
				t.Fatalf("content[%d] is %T, want mcp.ResourceLink", i, res.Content[i])
			}
			if rl.Type != mcp.ContentTypeLink {
				t.Errorf("content[%d].Type = %q, want %q", i, rl.Type, mcp.ContentTypeLink)
			}
			if rl.URI != wantURIs[i-1] {
				t.Errorf("content[%d].URI = %q, want %q", i, rl.URI, wantURIs[i-1])
			}
			if rl.MIMEType != "image/png" {
				t.Errorf("content[%d].MIMEType = %q, want image/png", i, rl.MIMEType)
			}
			if rl.Description != wantDescs[i-1] {
				t.Errorf("content[%d].Description = %q, want %q", i, rl.Description, wantDescs[i-1])
			}
		}
	})

	t.Run("live GCS sink (gated behind GENMEDIA_BUCKET)", func(t *testing.T) {
		bucket := strings.TrimSpace(os.Getenv("GENMEDIA_BUCKET"))
		if bucket == "" {
			t.Skip("GENMEDIA_BUCKET not set; skipping live GCS resource_link integration")
		}
		// This leg is a REAL live integration (#483 P4, resolves P1 review NB#2 —
		// the former placeholder only logged). It drives processImageResponse through
		// the REAL persistence seam (common.PersistMediaOutputs -> real GCS upload +
		// real V4 signed URL) using ambient credentials (ADC or
		// GOOGLE_APPLICATION_CREDENTIALS), then proves the emitted resource_link
		// identifies an object that genuinely exists in GCS by downloading it back
		// and comparing bytes.
		//
		// No genai call is needed: the resource_link contract lives entirely in the
		// GCS-persist + response-building step, which this exercises end-to-end with
		// real cloud I/O. The leg is fully gated behind GENMEDIA_BUCKET so it skips
		// cleanly in CI (no creds, no bucket). Objects are written under a unique,
		// self-cleaning prefix; cleanup is best-effort via `gcloud storage rm`.
		ctx := context.Background()

		// Normalize GENMEDIA_BUCKET to "gs://<bucket>[/prefix]" and append a unique
		// per-run prefix so parallel/repeat runs never collide and cleanup is scoped.
		base := strings.TrimSuffix(strings.TrimPrefix(bucket, "gs://"), "/")
		gcsBucketURI := fmt.Sprintf("gs://%s/nanobanana_outputs/live-483-%d", base, time.Now().UnixNano())
		t.Cleanup(func() {
			// Best-effort teardown; ignore errors (e.g. gcloud absent) so a passing
			// assertion is never masked by a cleanup failure.
			out, err := exec.Command("gcloud", "storage", "rm", "--recursive", gcsBucketURI).CombinedOutput()
			if err != nil {
				t.Logf("cleanup: could not remove %s: %v (%s)", gcsBucketURI, err, strings.TrimSpace(string(out)))
			}
		})

		// Use the REAL persistence seam for this leg (do NOT stub persistMediaOutputs).
		imgBytes := []byte("\x89PNG\r\n\x1a\n#483 live resource_link integration payload")
		resp := imageResponse(textPart("live leg"), imagePart("image/png", imgBytes))
		res, err := processImageResponse(ctx, resp, map[string]any{}, "", gcsBucketURI)
		if err != nil {
			t.Fatalf("processImageResponse (live) error: %v", err)
		}

		// The real upload must have succeeded (GCS errors are non-fatal and surfaced
		// as a warning line in the text — assert none appeared).
		text, ok := res.Content[0].(mcp.TextContent)
		if !ok {
			t.Fatalf("content[0] is %T, want mcp.TextContent", res.Content[0])
		}
		if strings.Contains(text.Text, "failed to upload") {
			t.Fatalf("live GCS upload reported a failure in the text summary: %q", text.Text)
		}

		// Exactly one image -> text + one resource_link.
		if len(res.Content) != 2 {
			t.Fatalf("content len = %d, want 2 (text + 1 link); text=%q", len(res.Content), text.Text)
		}
		rl, ok := res.Content[1].(mcp.ResourceLink)
		if !ok {
			t.Fatalf("content[1] is %T, want mcp.ResourceLink", res.Content[1])
		}
		if rl.Type != mcp.ContentTypeLink {
			t.Errorf("content[1].Type = %q, want %q", rl.Type, mcp.ContentTypeLink)
		}
		if !strings.HasPrefix(rl.URI, gcsBucketURI+"/") || !strings.HasSuffix(rl.URI, ".png") {
			t.Errorf("content[1].URI = %q, want %q/<name>.png", rl.URI, gcsBucketURI)
		}
		if rl.MIMEType != "image/png" {
			t.Errorf("content[1].MIMEType = %q, want image/png", rl.MIMEType)
		}
		if rl.Description != "nanobanana output 1 of 1" {
			t.Errorf("content[1].Description = %q, want %q", rl.Description, "nanobanana output 1 of 1")
		}

		// The decisive live assertion: the gs:// identity in the resource_link points
		// at a real object whose bytes round-trip. This is what the old placeholder
		// never did.
		got, err := common.DownloadFromGCSAsBytes(ctx, rl.URI)
		if err != nil {
			t.Fatalf("downloading the linked object %s failed (object should exist): %v", rl.URI, err)
		}
		if !bytes.Equal(got, imgBytes) {
			t.Errorf("linked object bytes (%d) != uploaded bytes (%d)", len(got), len(imgBytes))
		}
		t.Logf("live resource_link verified: %s (%d bytes round-tripped)", rl.URI, len(got))
	})
}
