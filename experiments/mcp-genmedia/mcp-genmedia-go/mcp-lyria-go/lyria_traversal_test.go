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

// TestSaveLyriaLocalFileRejectsDirTraversal is the per-server directory-traversal
// regression test for the lyria sink (saveLyriaLocalFile, CWE-22). It pins the
// OUTPUT_DIRECTORY half of the fix — distinct from the existing lyria "traversal"
// case which only exercises the FILENAME half. A caller-supplied local directory
// that is absolute or contains ".." must be rejected with NO write and NO
// out-of-root file, while a confined relative dir still writes under the root.
//
// The write seam (writeFileFn) is a recorder that also performs the real write, so
// a regression (deletion of the ResolveConfinedOutputDir guard) would both record a
// call and leave a file outside the root — either assertion would then fail.
func TestSaveLyriaLocalFileRejectsDirTraversal(t *testing.T) {
	root := t.TempDir()
	t.Setenv("MCP_OUTPUT_ROOT", root)
	resolvedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		resolvedRoot = root
	}

	origWrite := writeFileFn
	t.Cleanup(func() { writeFileFn = origWrite })
	var writes []string
	writeFileFn = func(path string, data []byte, perm os.FileMode) error {
		writes = append(writes, path)
		return os.WriteFile(path, data, perm)
	}

	const baseFilename = "track.wav"
	outsideAbs := t.TempDir() // absolute, outside root

	t.Run("absolute directory rejected", func(t *testing.T) {
		writes = nil
		full, saveErr := saveLyriaLocalFile(outsideAbs, baseFilename, []byte("audio"))
		if saveErr == nil {
			t.Fatalf("expected error for absolute local dir, got nil (path=%q)", full)
		}
		if len(writes) != 0 {
			t.Fatalf("traversal triggered a write: %v", writes)
		}
		if _, statErr := os.Stat(filepath.Join(outsideAbs, baseFilename)); statErr == nil {
			t.Fatalf("file written outside root via absolute dir — traversal not blocked")
		}
	})

	t.Run("dot-dot directory rejected", func(t *testing.T) {
		writes = nil
		full, saveErr := saveLyriaLocalFile("../../escape", baseFilename, []byte("audio"))
		if saveErr == nil {
			t.Fatalf("expected error for '..' local dir, got nil (path=%q)", full)
		}
		if len(writes) != 0 {
			t.Fatalf("traversal triggered a write: %v", writes)
		}
		if _, statErr := os.Stat(filepath.Join(root, "..", "escape", baseFilename)); statErr == nil {
			t.Fatalf("file written outside root via '..' dir — traversal not blocked")
		}
	})

	t.Run("confined relative directory succeeds under root", func(t *testing.T) {
		writes = nil
		full, saveErr := saveLyriaLocalFile("sub", baseFilename, []byte("audio"))
		if saveErr != nil {
			t.Fatalf("unexpected error for confined dir: %v", saveErr)
		}
		if !strings.HasPrefix(full, resolvedRoot+string(os.PathSeparator)) {
			t.Fatalf("confined save path %q escaped root %q", full, resolvedRoot)
		}
		if _, statErr := os.Stat(full); statErr != nil {
			t.Fatalf("expected confined file at %q: %v", full, statErr)
		}
	})
}
