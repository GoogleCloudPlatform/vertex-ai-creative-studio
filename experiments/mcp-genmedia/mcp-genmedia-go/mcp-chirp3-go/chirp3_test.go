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
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestSaveChirpAudioWiring is a handler-level wiring test: it drives saveChirpAudio
// (the function the handler calls to persist audio) with the os.WriteFile seam
// (writeFileFn) replaced by a recorder, and asserts the resolved output_filename
// actually reaches the write with the extension forced to .wav, precedence honored,
// and traversal sanitized. chirp3 synthesizes one selected voice, so only the n==1
// (<stem>.wav) case occurs; the shared _1..n suffix rule is covered where
// multi-output actually happens (imagen/veo/nanobanana/gemini-image/omni) and in
// mcp-common's BuildOutputFilenames tests.
func TestSaveChirpAudioWiring(t *testing.T) {
	const (
		voice = "en-US-Chirp3-HD-Zephyr"
		dir   = "/out"
	)
	origWrite := writeFileFn
	t.Cleanup(func() { writeFileFn = origWrite })

	var gotPath string
	var gotBytes []byte
	writeFileFn = func(name string, data []byte, _ os.FileMode) error {
		gotPath, gotBytes = name, data
		return nil
	}

	cases := []struct {
		name string
		args map[string]any
		want string
	}{
		{"single artifact, ext kept", map[string]any{"output_filename": "greeting.wav"}, "greeting.wav"},
		{"wrong extension forced to .wav", map[string]any{"output_filename": "greeting.mp3"}, "greeting.wav"},
		{"missing extension gets forced", map[string]any{"output_filename": "greeting"}, "greeting.wav"},
		{"output_filename wins over legacy prefix", map[string]any{"output_filename": "greeting.wav", "output_filename_prefix": "legacy"}, "greeting.wav"},
		{"traversal sanitized before write", map[string]any{"output_filename": "../../etc/greeting.wav"}, "greeting.wav"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			gotPath, gotBytes = "", nil
			saved, nameErr, writeErr := saveChirpAudio(tc.args, []byte("audio"), dir, voice)
			if nameErr != nil || writeErr != nil {
				t.Fatalf("unexpected errors: name=%v write=%v", nameErr, writeErr)
			}
			want := filepath.Clean(filepath.Join(dir, tc.want))
			if saved != want || gotPath != want {
				t.Errorf("saved=%q writeTarget=%q, want %q", saved, gotPath, want)
			}
			if string(gotBytes) != "audio" {
				t.Errorf("bytes written = %q, want %q", gotBytes, "audio")
			}
		})
	}

	t.Run("legacy prefix scheme preserved when output_filename unset", func(t *testing.T) {
		saved, nameErr, writeErr := saveChirpAudio(map[string]any{"output_filename_prefix": "custom"}, []byte("a"), dir, voice)
		if nameErr != nil || writeErr != nil {
			t.Fatalf("unexpected errors: name=%v write=%v", nameErr, writeErr)
		}
		base := filepath.Base(saved)
		if !strings.HasPrefix(base, "custom-"+voice+"-") || !strings.HasSuffix(base, ".wav") {
			t.Errorf("legacy scheme not wired to write: got %q", saved)
		}
	})

	t.Run("write error surfaced separately from name error", func(t *testing.T) {
		writeFileFn = func(string, []byte, os.FileMode) error { return fmt.Errorf("disk full") }
		t.Cleanup(func() {
			writeFileFn = func(name string, data []byte, _ os.FileMode) error { gotPath, gotBytes = name, data; return nil }
		})
		saved, nameErr, writeErr := saveChirpAudio(map[string]any{"output_filename": "greeting.wav"}, []byte("a"), dir, voice)
		if nameErr != nil {
			t.Fatalf("unexpected name error: %v", nameErr)
		}
		if writeErr == nil {
			t.Fatalf("expected write error")
		}
		if saved != filepath.Clean(filepath.Join(dir, "greeting.wav")) {
			t.Errorf("saved path should still be reported on write error, got %q", saved)
		}
	})
}

// TestResolveChirpOutputFilename covers the chirp3 naming decision: output_filename
// wins over the deprecated output_filename_prefix, the extension is forced to the
// audio MIME (.wav), traversal is sanitized, and the legacy prefix scheme is
// preserved (with the voice component) when output_filename is unset.
func TestResolveChirpOutputFilename(t *testing.T) {
	const voice = "en-US-Chirp3-HD-Zephyr"

	t.Run("output_filename honored, extension kept", func(t *testing.T) {
		got, err := resolveChirpOutputFilename(map[string]any{"output_filename": "greeting.wav"}, voice)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "greeting.wav" {
			t.Errorf("got %q, want %q", got, "greeting.wav")
		}
	})

	t.Run("wrong extension forced to audio MIME", func(t *testing.T) {
		got, err := resolveChirpOutputFilename(map[string]any{"output_filename": "greeting.mp3"}, voice)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "greeting.wav" {
			t.Errorf("got %q, want %q", got, "greeting.wav")
		}
	})

	t.Run("missing extension gets forced", func(t *testing.T) {
		got, err := resolveChirpOutputFilename(map[string]any{"output_filename": "greeting"}, voice)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "greeting.wav" {
			t.Errorf("got %q, want %q", got, "greeting.wav")
		}
	})

	t.Run("output_filename wins over legacy prefix", func(t *testing.T) {
		got, err := resolveChirpOutputFilename(map[string]any{
			"output_filename":        "greeting.wav",
			"output_filename_prefix": "legacy",
		}, voice)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "greeting.wav" {
			t.Errorf("got %q, want %q", got, "greeting.wav")
		}
	})

	t.Run("traversal sanitized", func(t *testing.T) {
		got, err := resolveChirpOutputFilename(map[string]any{"output_filename": "../../etc/greeting.wav"}, voice)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "greeting.wav" {
			t.Errorf("got %q, want %q", got, "greeting.wav")
		}
	})

	t.Run("dot-only base errors", func(t *testing.T) {
		if _, err := resolveChirpOutputFilename(map[string]any{"output_filename": "..."}, voice); err == nil {
			t.Fatalf("expected error for dot-only base")
		}
	})

	t.Run("legacy prefix scheme preserved when output_filename unset", func(t *testing.T) {
		got, err := resolveChirpOutputFilename(map[string]any{"output_filename_prefix": "custom"}, "en-US/Chirp3:HD")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !strings.HasPrefix(got, "custom-en-US_Chirp3_HD-") || !strings.HasSuffix(got, ".wav") {
			t.Errorf("legacy scheme not preserved: got %q", got)
		}
	})

	t.Run("default prefix when neither set", func(t *testing.T) {
		got, err := resolveChirpOutputFilename(map[string]any{}, voice)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !strings.HasPrefix(got, "chirp_audio-") || !strings.HasSuffix(got, ".wav") {
			t.Errorf("default prefix scheme not applied: got %q", got)
		}
	})
}
