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
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestProcessOutputAfterFFmpegRejectsTraversal is the prove-it test for shared sink
// family A (mcp-common/file_utils.go). BEFORE the fix the caller-supplied output
// directory flowed unsanitized into os.MkdirAll + os.Rename, so an absolute or ".."
// directory wrote the file outside any confinement (arbitrary file write, CWE-22).
// AFTER the fix the directory is confined to MCP_OUTPUT_ROOT and traversal is
// rejected with an error and no out-of-root write.
func TestProcessOutputAfterFFmpegRejectsTraversal(t *testing.T) {
	base := t.TempDir()
	t.Setenv(OutputRootEnvVar, base)

	newSrc := func(t *testing.T) string {
		t.Helper()
		src := filepath.Join(t.TempDir(), "out.mp3")
		if err := os.WriteFile(src, []byte("payload"), 0644); err != nil {
			t.Fatalf("seed src: %v", err)
		}
		return src
	}

	t.Run("absolute directory rejected", func(t *testing.T) {
		escape := t.TempDir() // absolute, OUTSIDE base
		_, _, err := ProcessOutputAfterFFmpeg(context.Background(), newSrc(t), "evil.mp3", escape, "", "")
		if err == nil {
			t.Fatalf("expected error for absolute output dir, got nil")
		}
		if _, statErr := os.Stat(filepath.Join(escape, "evil.mp3")); statErr == nil {
			t.Fatalf("file written outside base via absolute dir — traversal not blocked")
		}
	})

	t.Run("dot-dot directory rejected", func(t *testing.T) {
		_, _, err := ProcessOutputAfterFFmpeg(context.Background(), newSrc(t), "evil.mp3", "../../escape", "", "")
		if err == nil {
			t.Fatalf("expected error for '..' output dir, got nil")
		}
		if _, statErr := os.Stat(filepath.Join(base, "..", "escape", "evil.mp3")); statErr == nil {
			t.Fatalf("file written outside base via '..' dir — traversal not blocked")
		}
	})

	t.Run("confined directory succeeds", func(t *testing.T) {
		final, _, err := ProcessOutputAfterFFmpeg(context.Background(), newSrc(t), "ok.mp3", "sub", "", "")
		if err != nil {
			t.Fatalf("unexpected error for confined dir: %v", err)
		}
		if _, statErr := os.Stat(final); statErr != nil {
			t.Fatalf("expected confined file to exist at %q: %v", final, statErr)
		}
		resolvedBase, _ := filepath.EvalSymlinks(base)
		rel, relErr := filepath.Rel(resolvedBase, final)
		if relErr != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
			t.Fatalf("confined output %q not under base %q (rel=%q, err=%v)", final, resolvedBase, rel, relErr)
		}
	})
}

// TestPersistMediaOutputsRejectsTraversal is the prove-it test for shared sink
// family B (mcp-common/media_output.go). BEFORE the fix outputDir flowed
// unsanitized into os.MkdirAll + os.WriteFile.
func TestPersistMediaOutputsRejectsTraversal(t *testing.T) {
	base := t.TempDir()
	t.Setenv(OutputRootEnvVar, base)

	art := MediaArtifact{Data: []byte("payload"), MimeType: "image/png", FileName: "evil.png"}

	t.Run("absolute directory rejected", func(t *testing.T) {
		escape := t.TempDir()
		_, err := PersistMediaOutputs(context.Background(), art, escape, "", 0)
		if err == nil {
			t.Fatalf("expected error for absolute output dir, got nil")
		}
		if _, statErr := os.Stat(filepath.Join(escape, "evil.png")); statErr == nil {
			t.Fatalf("file written outside base via absolute dir — traversal not blocked")
		}
	})

	t.Run("dot-dot directory rejected", func(t *testing.T) {
		_, err := PersistMediaOutputs(context.Background(), art, "../../escape", "", 0)
		if err == nil {
			t.Fatalf("expected error for '..' output dir, got nil")
		}
		if _, statErr := os.Stat(filepath.Join(base, "..", "escape", "evil.png")); statErr == nil {
			t.Fatalf("file written outside base via '..' dir — traversal not blocked")
		}
	})

	t.Run("confined directory succeeds", func(t *testing.T) {
		out, err := PersistMediaOutputs(context.Background(), art, "sub", "", 0)
		if err != nil {
			t.Fatalf("unexpected error for confined dir: %v", err)
		}
		if _, statErr := os.Stat(out.LocalPath); statErr != nil {
			t.Fatalf("expected confined file to exist at %q: %v", out.LocalPath, statErr)
		}
	})
}
