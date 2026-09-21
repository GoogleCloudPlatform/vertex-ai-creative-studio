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
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"

	common "github.com/GoogleCloudPlatform/genmedia-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// TestNanobananaResourceLinkMatrix is the cross-cutting sink matrix for nanobanana
// (design #483 P4 Test Plan): it asserts the resource_link contract across the
// inline (no sink), local-only, both-local+GCS, and GCS-only paths, plus an
// explicit byte-for-byte back-compat check of the text summary on the GCS path.
// Every leg is network-free: the persistence seam is stubbed to return a
// deterministic PersistedMedia for the requested sink, so the whole matrix runs
// in CI without credentials.
func TestNanobananaResourceLinkMatrix(t *testing.T) {
	// Pin the signed-URL expiry so the back-compat text is deterministic.
	t.Setenv("NANOBANANA_SIGNED_URL_EXPIRY_HOURS", "24")

	// resourceLinks returns just the resource_link items in res.Content.
	resourceLinks := func(t *testing.T, res *mcp.CallToolResult) []mcp.ResourceLink {
		t.Helper()
		var links []mcp.ResourceLink
		for _, c := range res.Content {
			if rl, ok := c.(mcp.ResourceLink); ok {
				links = append(links, rl)
			}
		}
		return links
	}
	firstText := func(t *testing.T, res *mcp.CallToolResult) string {
		t.Helper()
		text, ok := res.Content[0].(mcp.TextContent)
		if !ok {
			t.Fatalf("content[0] is %T, want mcp.TextContent", res.Content[0])
		}
		return text.Text
	}

	// Inline sink (no output_directory, no gcs_bucket_uri): nanobanana persists
	// nothing, so there is NO resource_link and no signed-URL / saved-files line.
	t.Run("inline sink -> no resource_link", func(t *testing.T) {
		orig := persistMediaOutputs
		t.Cleanup(func() { persistMediaOutputs = orig })
		persistMediaOutputs = func(_ context.Context, _ common.MediaArtifact, _, _ string, _ time.Duration) (common.PersistedMedia, error) {
			return common.PersistedMedia{}, nil // nothing saved
		}

		resp := imageResponse(textPart("hello"), imagePart("image/png", []byte("x")))
		res, err := processImageResponse(context.Background(), resp, map[string]any{}, "", "")
		if err != nil {
			t.Fatalf("processImageResponse error: %v", err)
		}
		if links := resourceLinks(t, res); len(links) != 0 {
			t.Errorf("inline sink produced %d resource_link(s), want 0", len(links))
		}
		text := firstText(t, res)
		if !strings.Contains(text, "hello") {
			t.Errorf("text missing model output; got %q", text)
		}
		if strings.Contains(text, "Signed URL") || strings.Contains(text, "Generated and saved") {
			t.Errorf("inline sink text should not mention a saved file / signed URL; got %q", text)
		}
	})

	// Local-only sink (output_directory set, no GCS): a local file is written but
	// there is NO resource_link (this PR does not emit file:// links); the local
	// saved-files line is present and unchanged.
	t.Run("local-only sink -> no resource_link, local text preserved", func(t *testing.T) {
		orig := persistMediaOutputs
		t.Cleanup(func() { persistMediaOutputs = orig })
		persistMediaOutputs = func(_ context.Context, art common.MediaArtifact, outputDir, _ string, _ time.Duration) (common.PersistedMedia, error) {
			return common.PersistedMedia{LocalPath: outputDir + "/" + art.FileName}, nil
		}

		resp := imageResponse(textPart("hello"), imagePart("image/png", []byte("x")))
		res, err := processImageResponse(context.Background(), resp, map[string]any{"output_filename": "shot.png"}, "/tmp/out", "")
		if err != nil {
			t.Fatalf("processImageResponse error: %v", err)
		}
		if links := resourceLinks(t, res); len(links) != 0 {
			t.Errorf("local-only sink produced %d resource_link(s), want 0", len(links))
		}
		text := firstText(t, res)
		if !strings.Contains(text, "Generated and saved 1 image(s): /tmp/out/shot.png") {
			t.Errorf("local-only text missing saved-file line; got %q", text)
		}
	})

	// Both local+GCS: a resource_link IS emitted (GCS identity) and the local
	// saved-files line is preserved in the (unchanged) text.
	t.Run("both local+GCS -> resource_link present, local text preserved", func(t *testing.T) {
		orig := persistMediaOutputs
		t.Cleanup(func() { persistMediaOutputs = orig })
		persistMediaOutputs = func(_ context.Context, art common.MediaArtifact, outputDir, gcsBucketURI string, _ time.Duration) (common.PersistedMedia, error) {
			return common.PersistedMedia{
				LocalPath: outputDir + "/" + art.FileName,
				GCSURI:    strings.TrimSuffix(gcsBucketURI, "/") + "/" + art.FileName,
				GCSObject: art.FileName,
				SignedURL: "https://signed.example/" + art.FileName,
			}, nil
		}

		resp := imageResponse(textPart("hello"), imagePart("image/png", []byte("x")))
		res, err := processImageResponse(context.Background(), resp, map[string]any{"output_filename": "shot.png"}, "/tmp/out", "gs://bkt/pfx")
		if err != nil {
			t.Fatalf("processImageResponse error: %v", err)
		}
		links := resourceLinks(t, res)
		if len(links) != 1 {
			t.Fatalf("both sink produced %d resource_link(s), want 1", len(links))
		}
		if links[0].URI != "gs://bkt/pfx/shot.png" {
			t.Errorf("resource_link URI = %q, want gs://bkt/pfx/shot.png", links[0].URI)
		}
		text := firstText(t, res)
		if !strings.Contains(text, "/tmp/out/shot.png") {
			t.Errorf("both sink text lost the local path; got %q", text)
		}
		if !strings.Contains(text, "gs://bkt/pfx/shot.png") {
			t.Errorf("both sink text lost the gs:// summary line; got %q", text)
		}
	})

	// GCS sink back-compat: the text summary is byte-for-byte what the pre-#483
	// code produced (model text, signed-URL line, saved-files line). #483 only
	// APPENDS the resource_link after content[0]; content[0] must be identical.
	t.Run("GCS sink -> text byte-identical (back-compat)", func(t *testing.T) {
		orig := persistMediaOutputs
		t.Cleanup(func() { persistMediaOutputs = orig })
		persistMediaOutputs = func(_ context.Context, art common.MediaArtifact, _, gcsBucketURI string, _ time.Duration) (common.PersistedMedia, error) {
			return common.PersistedMedia{
				GCSURI:    strings.TrimSuffix(gcsBucketURI, "/") + "/" + art.FileName,
				GCSObject: "pfx/" + art.FileName,
				SignedURL: "https://signed.example/x",
			}, nil
		}

		resp := imageResponse(textPart("here you go"), imagePart("image/png", []byte("x")))
		res, err := processImageResponse(context.Background(), resp, map[string]any{"output_filename": "shot.png"}, "", "gs://bkt/pfx")
		if err != nil {
			t.Fatalf("processImageResponse error: %v", err)
		}
		if links := resourceLinks(t, res); len(links) != 1 {
			t.Fatalf("GCS sink produced %d resource_link(s), want 1", len(links))
		}

		// The exact text the unchanged builder emits: model text, then the signed-URL
		// line, then the saved-files summary — all TrimSpace'd.
		want := fmt.Sprintf(
			"here you go\n\nSigned URL for pfx/shot.png (valid %s):\nhttps://signed.example/x\n\nGenerated and saved 1 image(s): gs://bkt/pfx/shot.png",
			(24 * time.Hour).String(),
		)
		if got := firstText(t, res); got != want {
			t.Errorf("back-compat text drift:\n got=%q\nwant=%q", got, want)
		}
	})
}
