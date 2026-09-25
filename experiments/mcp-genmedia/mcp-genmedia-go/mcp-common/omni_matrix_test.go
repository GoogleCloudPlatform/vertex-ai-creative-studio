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
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

// TestRenderOmniResultBothLocalAndGCS completes the cross-cutting sink matrix for
// the shared omni renderer (used by mcp-omni-go and mcp-gemini-go): when a call
// writes BOTH locally and to GCS, a resource_link is emitted for the GCS identity
// and the local saved-files line is preserved in the (unchanged) text (design
// #483 P4 Test Plan). The GCS upload / signing seams are stubbed; the local write
// is real (t.TempDir), so the leg is network-free.
func TestRenderOmniResultBothLocalAndGCS(t *testing.T) {
	origUpload := uploadToGCSFn
	origSign := generateV4SignedURLFn
	t.Cleanup(func() { uploadToGCSFn = origUpload; generateV4SignedURLFn = origSign })
	uploadToGCSFn = func(context.Context, string, string, string, []byte) error { return nil }
	generateV4SignedURLFn = func(_ context.Context, _, object string, _ time.Duration) (string, error) {
		return "https://signed.example/" + object, nil
	}

	// output_directory is now confined to MCP_OUTPUT_ROOT (CWE-22): make the temp
	// dir a child of the configured root and pass it as a relative dir.
	dir := t.TempDir()
	t.Setenv(OutputRootEnvVar, filepath.Dir(dir))
	relDir := filepath.Base(dir)
	result := &OmniResult{
		Videos:         [][]byte{[]byte("mp4-bytes")},
		VideoMimeTypes: []string{"video/mp4"},
		Text:           "here is your video",
	}
	content, err := RenderOmniResult(context.Background(), result, relDir, "my-bucket/prefix", "clip.mp4")
	if err != nil {
		t.Fatalf("RenderOmniResult error: %v", err)
	}

	if len(content) != 2 {
		t.Fatalf("expected 2 content items (text + 1 link), got %d", len(content))
	}
	link, ok := content[1].(mcp.ResourceLink)
	if !ok {
		t.Fatalf("content[1] = %T, want mcp.ResourceLink", content[1])
	}
	if link.URI != "gs://my-bucket/prefix/clip.mp4" {
		t.Errorf("resource_link URI = %q, want gs://my-bucket/prefix/clip.mp4", link.URI)
	}
	text, ok := content[0].(mcp.TextContent)
	if !ok {
		t.Fatalf("content[0] = %T, want mcp.TextContent", content[0])
	}
	// The local path and the gs:// URI both appear in the saved-files summary.
	if !strings.Contains(text.Text, dir) {
		t.Errorf("both sink text lost the local path %q; got %q", dir, text.Text)
	}
	if !strings.Contains(text.Text, "gs://my-bucket/prefix/clip.mp4") {
		t.Errorf("both sink text lost the gs:// URI; got %q", text.Text)
	}
}

// TestRenderOmniResultGCSBackCompat asserts the GCS-path text summary is
// byte-for-byte the pre-#483 output (model text, signed-URL line, saved-files
// line). #483 only APPENDS the resource_link after content[0]; content[0] must be
// identical. output_filename pins the object name and the expiry env is pinned so
// the whole summary is deterministic.
func TestRenderOmniResultGCSBackCompat(t *testing.T) {
	t.Setenv("OMNI_SIGNED_URL_EXPIRY_HOURS", "24")

	origUpload := uploadToGCSFn
	origSign := generateV4SignedURLFn
	t.Cleanup(func() { uploadToGCSFn = origUpload; generateV4SignedURLFn = origSign })
	uploadToGCSFn = func(context.Context, string, string, string, []byte) error { return nil }
	generateV4SignedURLFn = func(_ context.Context, _, object string, _ time.Duration) (string, error) {
		return "https://signed.example/" + object, nil
	}

	result := &OmniResult{
		Videos:         [][]byte{[]byte("mp4-bytes")},
		VideoMimeTypes: []string{"video/mp4"},
		Text:           "the video",
	}
	content, err := RenderOmniResult(context.Background(), result, "", "my-bucket/prefix", "clip.mp4")
	if err != nil {
		t.Fatalf("RenderOmniResult error: %v", err)
	}
	if len(content) != 2 {
		t.Fatalf("expected 2 content items (text + 1 link), got %d", len(content))
	}
	text, ok := content[0].(mcp.TextContent)
	if !ok {
		t.Fatalf("content[0] = %T, want mcp.TextContent", content[0])
	}
	want := "the video\n\n" +
		"Signed URL for prefix/clip.mp4 (valid " + (24 * time.Hour).String() + "):\n" +
		"https://signed.example/prefix/clip.mp4\n\n" +
		"Generated and saved 1 video(s): gs://my-bucket/prefix/clip.mp4"
	if text.Text != want {
		t.Errorf("back-compat text drift:\n got=%q\nwant=%q", text.Text, want)
	}
}
