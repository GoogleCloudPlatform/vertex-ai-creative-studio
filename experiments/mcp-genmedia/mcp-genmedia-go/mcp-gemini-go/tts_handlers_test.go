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

// TestSaveGeminiTTSAudioWiring is a handler-level wiring test: it drives
// saveGeminiTTSAudio (the function the handler calls to persist audio) with the
// os.WriteFile seam (writeFileFn) replaced by a recorder, and asserts the resolved
// output_filename actually reaches the write with the extension forced to the true
// audio MIME, precedence honored, and the collision path not erroring. gemini-TTS
// is single-artifact, so only the n==1 (<stem>.<ext>) case occurs; the shared
// _1..n suffix rule is covered where multi-output actually happens (imagen/veo/
// nanobanana/gemini-image/omni) and in mcp-common's BuildOutputFilenames tests.
func TestSaveGeminiTTSAudioWiring(t *testing.T) {
	const (
		voice = "Callirrhoe"
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
		name      string
		args      map[string]any
		legacyExt string
		mimeType  string
		want      string
	}{
		{"single artifact, ext kept", map[string]any{"output_filename": "speech.wav"}, ".wav", "audio/wav", "speech.wav"},
		{"extension forced to encoding MIME", map[string]any{"output_filename": "speech.wav"}, ".mp3", "audio/mpeg", "speech.mp3"},
		{"output_filename wins over legacy prefix", map[string]any{"output_filename": "speech.wav", "output_filename_prefix": "legacy"}, ".wav", "audio/wav", "speech.wav"},
		{"traversal sanitized before write", map[string]any{"output_filename": "../../etc/speech.wav"}, ".wav", "audio/wav", "speech.wav"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			gotPath, gotBytes = "", nil
			saved, nameErr, writeErr := saveGeminiTTSAudio(tc.args, []byte("audio"), dir, voice, tc.legacyExt, tc.mimeType)
			if nameErr != nil || writeErr != nil {
				t.Fatalf("unexpected errors: name=%v write=%v", nameErr, writeErr)
			}
			want := filepath.Join(dir, tc.want)
			if saved != want || gotPath != want {
				t.Errorf("saved=%q writeTarget=%q, want %q", saved, gotPath, want)
			}
			if string(gotBytes) != "audio" {
				t.Errorf("bytes written = %q, want %q", gotBytes, "audio")
			}
		})
	}

	t.Run("legacy prefix scheme preserved when output_filename unset", func(t *testing.T) {
		gotPath = ""
		saved, nameErr, writeErr := saveGeminiTTSAudio(map[string]any{"output_filename_prefix": "custom"}, []byte("a"), dir, voice, ".wav", "audio/wav")
		if nameErr != nil || writeErr != nil {
			t.Fatalf("unexpected errors: name=%v write=%v", nameErr, writeErr)
		}
		base := filepath.Base(saved)
		if !strings.HasPrefix(base, "custom-"+voice+"-") || !strings.HasSuffix(base, ".wav") {
			t.Errorf("legacy scheme not wired to write: got %q", saved)
		}
	})

	t.Run("write error is surfaced separately from name error", func(t *testing.T) {
		writeFileFn = func(string, []byte, os.FileMode) error { return fmt.Errorf("disk full") }
		t.Cleanup(func() {
			writeFileFn = func(name string, data []byte, _ os.FileMode) error { gotPath, gotBytes = name, data; return nil }
		})
		saved, nameErr, writeErr := saveGeminiTTSAudio(map[string]any{"output_filename": "speech.wav"}, []byte("a"), dir, voice, ".wav", "audio/wav")
		if nameErr != nil {
			t.Fatalf("unexpected name error: %v", nameErr)
		}
		if writeErr == nil {
			t.Fatalf("expected write error")
		}
		if saved != filepath.Join(dir, "speech.wav") {
			t.Errorf("saved path should still be reported on write error, got %q", saved)
		}
	})
}

// TestResolveGeminiTTSFilename covers the gemini-TTS naming decision: output_filename
// wins over the deprecated output_filename_prefix, the extension is forced to the
// true audio MIME of the selected encoding, traversal is sanitized, and the legacy
// <prefix>-<voice>-<timestamp><ext> scheme is preserved when output_filename is unset.
func TestResolveGeminiTTSFilename(t *testing.T) {
	const voice = "Callirrhoe"

	t.Run("output_filename honored, extension kept", func(t *testing.T) {
		got, err := resolveGeminiTTSFilename(map[string]any{"output_filename": "speech.wav"}, voice, ".wav", "audio/wav")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "speech.wav" {
			t.Errorf("got %q, want %q", got, "speech.wav")
		}
	})

	t.Run("extension forced to encoding MIME", func(t *testing.T) {
		// Client passes .wav but selected encoding is MP3 -> forced to .mp3.
		got, err := resolveGeminiTTSFilename(map[string]any{"output_filename": "speech.wav"}, voice, ".mp3", "audio/mpeg")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "speech.mp3" {
			t.Errorf("got %q, want %q", got, "speech.mp3")
		}
	})

	t.Run("missing extension gets forced", func(t *testing.T) {
		got, err := resolveGeminiTTSFilename(map[string]any{"output_filename": "speech"}, voice, ".ogg", "audio/ogg")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "speech.ogg" {
			t.Errorf("got %q, want %q", got, "speech.ogg")
		}
	})

	t.Run("output_filename wins over legacy prefix", func(t *testing.T) {
		got, err := resolveGeminiTTSFilename(map[string]any{
			"output_filename":        "speech.wav",
			"output_filename_prefix": "legacy",
		}, voice, ".wav", "audio/wav")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "speech.wav" {
			t.Errorf("got %q, want %q", got, "speech.wav")
		}
	})

	t.Run("traversal sanitized", func(t *testing.T) {
		got, err := resolveGeminiTTSFilename(map[string]any{"output_filename": "../../etc/speech.wav"}, voice, ".wav", "audio/wav")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != "speech.wav" {
			t.Errorf("got %q, want %q", got, "speech.wav")
		}
	})

	t.Run("dot-only base errors", func(t *testing.T) {
		if _, err := resolveGeminiTTSFilename(map[string]any{"output_filename": "..."}, voice, ".wav", "audio/wav"); err == nil {
			t.Fatalf("expected error for dot-only base")
		}
	})

	t.Run("legacy prefix scheme preserved when output_filename unset", func(t *testing.T) {
		got, err := resolveGeminiTTSFilename(map[string]any{"output_filename_prefix": "custom"}, voice, ".mp3", "audio/mpeg")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !strings.HasPrefix(got, "custom-"+voice+"-") || !strings.HasSuffix(got, ".mp3") {
			t.Errorf("legacy scheme not preserved: got %q", got)
		}
	})

	t.Run("default prefix when neither set", func(t *testing.T) {
		got, err := resolveGeminiTTSFilename(map[string]any{}, voice, ".wav", "audio/wav")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !strings.HasPrefix(got, "gemini_tts_audio-"+voice+"-") || !strings.HasSuffix(got, ".wav") {
			t.Errorf("default prefix scheme not applied: got %q", got)
		}
	})
}
