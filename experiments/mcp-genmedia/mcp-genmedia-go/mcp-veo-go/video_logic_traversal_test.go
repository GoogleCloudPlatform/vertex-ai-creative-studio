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
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestConfineVeoOutputDirRejectsTraversal is the per-server directory-traversal
// regression test for the veo local-download sink (CWE-22). callGenerateVideosAPI's
// download loop is gated by confineVeoOutputDir, the behavior-preserving extraction of
// the confinement block; this test drives that function with output_directory = an
// absolute path AND with "../../escape" and asserts (a) local download is DISABLED
// (attempt=false) with the rejection reason surfaced, and (b) NO file is created
// outside the configured root when the handler's guarded-download wiring runs.
//
// To assert (b) faithfully, each case replays the exact handler control flow:
// `if attempt { DownloadFromGCS(... join(dir,name)) }` — modeled here as a direct
// write into the resolved target since the download's only local effect is a file at
// that path. A regression that removed the confinement (attempt would stay true, dir
// would stay raw) would land the file outside the root and fail the assertion.
func TestConfineVeoOutputDirRejectsTraversal(t *testing.T) {
	root := t.TempDir()
	t.Setenv("MCP_OUTPUT_ROOT", root)
	resolvedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		resolvedRoot = root
	}

	const fileName = "clip.mp4"
	payload := []byte("video-bytes")

	// replayHandlerDownload mirrors the guarded local-download wiring: a file lands at
	// join(dir,name) only when attempt is true, into the (already confined) dir.
	replayHandlerDownload := func(t *testing.T, dir string, attempt bool) {
		t.Helper()
		if !attempt {
			return
		}
		if mkErr := os.MkdirAll(dir, 0755); mkErr != nil {
			t.Fatalf("MkdirAll(%q): %v", dir, mkErr)
		}
		if wErr := os.WriteFile(filepath.Join(dir, fileName), payload, 0644); wErr != nil {
			t.Fatalf("WriteFile: %v", wErr)
		}
	}

	t.Run("absolute directory disabled, no out-of-root write", func(t *testing.T) {
		outsideAbs := t.TempDir() // absolute, outside root
		dir, attempt, errs := confineVeoOutputDir(outsideAbs, true, nil)
		if attempt {
			t.Fatalf("expected local download DISABLED for absolute dir, attempt=true")
		}
		if len(errs) != 1 {
			t.Fatalf("expected 1 rejection reason, got %v", errs)
		}
		replayHandlerDownload(t, dir, attempt)
		if _, statErr := os.Stat(filepath.Join(outsideAbs, fileName)); statErr == nil {
			t.Fatalf("file written outside root via absolute dir — traversal not blocked")
		}
	})

	t.Run("dot-dot directory disabled, no out-of-root write", func(t *testing.T) {
		dir, attempt, errs := confineVeoOutputDir("../../escape", true, nil)
		if attempt {
			t.Fatalf("expected local download DISABLED for '..' dir, attempt=true")
		}
		if len(errs) != 1 {
			t.Fatalf("expected 1 rejection reason, got %v", errs)
		}
		replayHandlerDownload(t, dir, attempt)
		if _, statErr := os.Stat(filepath.Join(root, "..", "escape", fileName)); statErr == nil {
			t.Fatalf("file written outside root via '..' dir — traversal not blocked")
		}
	})

	t.Run("confined relative directory enabled, writes under root", func(t *testing.T) {
		dir, attempt, errs := confineVeoOutputDir("sub", true, nil)
		if !attempt {
			t.Fatalf("expected local download ENABLED for confined dir, attempt=false (errs=%v)", errs)
		}
		if len(errs) != 0 {
			t.Fatalf("expected no rejection reasons for confined dir, got %v", errs)
		}
		if !strings.HasPrefix(dir, resolvedRoot+string(os.PathSeparator)) {
			t.Fatalf("confined dir %q escaped root %q", dir, resolvedRoot)
		}
		replayHandlerDownload(t, dir, attempt)
		if _, statErr := os.Stat(filepath.Join(dir, fileName)); statErr != nil {
			t.Fatalf("expected confined file under root at %q: %v", filepath.Join(dir, fileName), statErr)
		}
	})

	t.Run("already-disabled is a no-op pass-through", func(t *testing.T) {
		dir, attempt, errs := confineVeoOutputDir("../../escape", false, nil)
		if attempt {
			t.Fatalf("attempt should remain false")
		}
		if dir != "../../escape" || errs != nil {
			t.Fatalf("expected pass-through (dir unchanged, no errs), got dir=%q errs=%v", dir, errs)
		}
	})
}
