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
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
)

// TestGeminiResourceLinkMatrix completes the cross-cutting sink matrix for the
// gemini image handler (design #483 P4 Test Plan). The GCS-sink and inline legs
// are already covered by handlers_resource_link_test.go; this adds the local-only
// and both-local+GCS legs plus an explicit byte-for-byte back-compat assertion on
// the GCS text summary. All legs are network-free (write/upload seams stubbed).
func TestGeminiResourceLinkMatrix(t *testing.T) {
	// output_directory is now confined to MCP_OUTPUT_ROOT (CWE-22): use a relative
	// dir under a configured temp root; savedShot is the confined absolute path the
	// saved-file summary is expected to reference.
	root := t.TempDir()
	t.Setenv("MCP_OUTPUT_ROOT", root)
	const outDir = "out"
	resolvedRoot, evalErr := filepath.EvalSymlinks(root)
	if evalErr != nil {
		resolvedRoot = root
	}
	savedShot := filepath.Join(resolvedRoot, outDir, "shot.png")

	resourceLinks := func(res *mcp.CallToolResult) []mcp.ResourceLink {
		var links []mcp.ResourceLink
		for _, c := range res.Content {
			if rl, ok := c.(mcp.ResourceLink); ok {
				links = append(links, rl)
			}
		}
		return links
	}
	inlineImages := func(res *mcp.CallToolResult) int {
		n := 0
		for _, c := range res.Content {
			if _, ok := c.(mcp.ImageContent); ok {
				n++
			}
		}
		return n
	}
	firstText := func(t *testing.T, res *mcp.CallToolResult) string {
		t.Helper()
		text, ok := res.Content[0].(mcp.TextContent)
		if !ok {
			t.Fatalf("content[0] is %T, want mcp.TextContent", res.Content[0])
		}
		return text.Text
	}

	// Local-only sink: image is written locally (write seam stubbed), NO inline
	// image content is returned, and NO resource_link is emitted (no file:// links).
	t.Run("local-only sink -> no resource_link, no inline image", func(t *testing.T) {
		origWrite := writeFileFn
		t.Cleanup(func() { writeFileFn = origWrite })
		writeFileFn = func(string, []byte, os.FileMode) error { return nil }

		resp := imageResponse(textPart("hi"), imagePart("image/png", []byte("a")))
		res, err := processGeminiImageResponse(context.Background(), resp, map[string]any{"output_filename": "shot.png"}, outDir, "", "", "")
		if err != nil {
			t.Fatalf("error: %v", err)
		}
		if got := len(resourceLinks(res)); got != 0 {
			t.Errorf("local-only produced %d resource_link(s), want 0", got)
		}
		if got := inlineImages(res); got != 0 {
			t.Errorf("local-only returned %d inline image(s), want 0", got)
		}
		if text := firstText(t, res); !strings.Contains(text, "Generated and saved 1 image(s): "+savedShot) {
			t.Errorf("local-only text missing saved-file line; got %q", text)
		}
	})

	// Both local+GCS: resource_link IS emitted (GCS identity); the local saved
	// line is preserved alongside the GCS uploaded line.
	t.Run("both local+GCS -> resource_link present, local text preserved", func(t *testing.T) {
		origWrite := writeFileFn
		origUpload := uploadToGCSFn
		t.Cleanup(func() { writeFileFn = origWrite; uploadToGCSFn = origUpload })
		writeFileFn = func(string, []byte, os.FileMode) error { return nil }
		uploadToGCSFn = func(context.Context, string, string, string, []byte) error { return nil }

		resp := imageResponse(textPart("hi"), imagePart("image/png", []byte("a")))
		res, err := processGeminiImageResponse(context.Background(), resp, map[string]any{"output_filename": "shot.png"}, outDir, "gs://test-bucket/pfx", "test-bucket", "pfx")
		if err != nil {
			t.Fatalf("error: %v", err)
		}
		links := resourceLinks(res)
		if len(links) != 1 {
			t.Fatalf("both sink produced %d resource_link(s), want 1", len(links))
		}
		if links[0].URI != "gs://test-bucket/pfx/shot.png" {
			t.Errorf("resource_link URI = %q, want gs://test-bucket/pfx/shot.png", links[0].URI)
		}
		text := firstText(t, res)
		if !strings.Contains(text, "Generated and saved 1 image(s): "+savedShot) {
			t.Errorf("both sink text lost local saved line; got %q", text)
		}
		if !strings.Contains(text, "Generated and uploaded 1 image(s) to GCS: gs://test-bucket/pfx/shot.png") {
			t.Errorf("both sink text lost GCS uploaded line; got %q", text)
		}
	})

	// GCS sink back-compat: content[0] is byte-for-byte the pre-#483 text summary
	// (model text + GCS uploaded line). #483 only appends the resource_link.
	t.Run("GCS sink -> text byte-identical (back-compat)", func(t *testing.T) {
		origUpload := uploadToGCSFn
		t.Cleanup(func() { uploadToGCSFn = origUpload })
		uploadToGCSFn = func(context.Context, string, string, string, []byte) error { return nil }

		resp := imageResponse(textPart("here you go"), imagePart("image/png", []byte("a")))
		res, err := processGeminiImageResponse(context.Background(), resp, map[string]any{"output_filename": "shot.png"}, "", "gs://test-bucket/pfx", "test-bucket", "pfx")
		if err != nil {
			t.Fatalf("error: %v", err)
		}
		if got := len(resourceLinks(res)); got != 1 {
			t.Fatalf("GCS sink produced %d resource_link(s), want 1", got)
		}
		want := "here you go\n\nGenerated and uploaded 1 image(s) to GCS: gs://test-bucket/pfx/shot.png"
		if got := firstText(t, res); got != want {
			t.Errorf("back-compat text drift:\n got=%q\nwant=%q", got, want)
		}
	})
}
