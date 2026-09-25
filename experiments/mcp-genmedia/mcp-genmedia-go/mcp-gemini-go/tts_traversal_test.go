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

// TestSaveGeminiTTSAudioRejectsDirTraversal is the per-server directory-traversal
// regression test for the gemini-TTS sink (saveGeminiTTSAudio, CWE-22). It pins the
// OUTPUT_DIRECTORY half of the fix — distinct from TestSaveGeminiTTSAudioWiring /
// TestResolveGeminiTTSFilename which only exercise the FILENAME half
// (output_filename -> SanitizeBaseFilename). A caller-supplied output_directory that
// is absolute or contains ".." must be rejected (nameErr) with NO write and NO
// out-of-root file, while a confined relative dir still writes under the root.
//
// The write seam (writeFileFn) is a recorder that also performs the real write, so
// a regression (deletion of the ResolveConfinedOutputDir guard) would both record a
// call and leave a file outside the root — either assertion would then fail.
func TestSaveGeminiTTSAudioRejectsDirTraversal(t *testing.T) {
	const (
		voice     = "Callirrhoe"
		legacyExt = ".wav"
		mimeType  = "audio/wav"
	)
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

	args := map[string]any{"output_filename": "speech.wav"}
	outsideAbs := t.TempDir() // absolute, outside root

	t.Run("absolute directory rejected", func(t *testing.T) {
		writes = nil
		saved, nameErr, writeErr := saveGeminiTTSAudio(args, []byte("audio"), outsideAbs, voice, legacyExt, mimeType)
		if nameErr == nil {
			t.Fatalf("expected nameErr for absolute output dir, got nil (saved=%q writeErr=%v)", saved, writeErr)
		}
		if saved != "" {
			t.Errorf("saved path should be empty on rejection, got %q", saved)
		}
		if len(writes) != 0 {
			t.Fatalf("traversal triggered a write: %v", writes)
		}
		if _, statErr := os.Stat(filepath.Join(outsideAbs, "speech.wav")); statErr == nil {
			t.Fatalf("file written outside root via absolute dir — traversal not blocked")
		}
	})

	t.Run("dot-dot directory rejected", func(t *testing.T) {
		writes = nil
		saved, nameErr, _ := saveGeminiTTSAudio(args, []byte("audio"), "../../escape", voice, legacyExt, mimeType)
		if nameErr == nil {
			t.Fatalf("expected nameErr for '..' output dir, got nil (saved=%q)", saved)
		}
		if len(writes) != 0 {
			t.Fatalf("traversal triggered a write: %v", writes)
		}
		if _, statErr := os.Stat(filepath.Join(root, "..", "escape", "speech.wav")); statErr == nil {
			t.Fatalf("file written outside root via '..' dir — traversal not blocked")
		}
	})

	t.Run("confined relative directory succeeds under root", func(t *testing.T) {
		writes = nil
		saved, nameErr, writeErr := saveGeminiTTSAudio(args, []byte("audio"), "sub", voice, legacyExt, mimeType)
		if nameErr != nil || writeErr != nil {
			t.Fatalf("unexpected errors for confined dir: name=%v write=%v", nameErr, writeErr)
		}
		if !strings.HasPrefix(saved, resolvedRoot+string(os.PathSeparator)) {
			t.Fatalf("confined save path %q escaped root %q", saved, resolvedRoot)
		}
		if _, statErr := os.Stat(saved); statErr != nil {
			t.Fatalf("expected confined file at %q: %v", saved, statErr)
		}
	})
}
