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
	"testing"
)

// TestSaveChirpAudioRejectsTraversal is the prove-it test for the chirp3 per-server
// sink (family C). BEFORE the fix saveChirpAudio used filepath.Clean(filepath.Join(...))
// which does NOT confine, so an absolute or ".." output_directory wrote outside any
// base. AFTER the fix the directory is confined to MCP_OUTPUT_ROOT and traversal is
// rejected (nameErr) with no out-of-root write.
func TestSaveChirpAudioRejectsTraversal(t *testing.T) {
	const voice = "en-US-Chirp3-HD-Zephyr"
	base := t.TempDir()
	t.Setenv("MCP_OUTPUT_ROOT", base)

	// Real writer so an escape would leave an observable file on disk.
	origWrite := writeFileFn
	t.Cleanup(func() { writeFileFn = origWrite })
	writeFileFn = os.WriteFile

	args := map[string]any{"output_filename": "greeting.wav"}

	t.Run("absolute directory rejected", func(t *testing.T) {
		escape := t.TempDir()
		_, nameErr, writeErr := saveChirpAudio(args, []byte("audio"), escape, voice)
		if nameErr == nil {
			t.Fatalf("expected rejection error for absolute output dir, got nameErr=nil writeErr=%v", writeErr)
		}
		if _, statErr := os.Stat(filepath.Join(escape, "greeting.wav")); statErr == nil {
			t.Fatalf("audio written outside base via absolute dir — traversal not blocked")
		}
	})

	t.Run("dot-dot directory rejected", func(t *testing.T) {
		_, nameErr, _ := saveChirpAudio(args, []byte("audio"), "../../escape", voice)
		if nameErr == nil {
			t.Fatalf("expected rejection error for '..' output dir, got nil")
		}
		if _, statErr := os.Stat(filepath.Join(base, "..", "escape", "greeting.wav")); statErr == nil {
			t.Fatalf("audio written outside base via '..' dir — traversal not blocked")
		}
	})

	t.Run("confined directory succeeds", func(t *testing.T) {
		saved, nameErr, writeErr := saveChirpAudio(args, []byte("audio"), "sub", voice)
		if nameErr != nil || writeErr != nil {
			t.Fatalf("unexpected errors for confined dir: name=%v write=%v", nameErr, writeErr)
		}
		if _, statErr := os.Stat(saved); statErr != nil {
			t.Fatalf("expected confined file at %q: %v", saved, statErr)
		}
	})
}
