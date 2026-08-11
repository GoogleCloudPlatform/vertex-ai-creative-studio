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
	"testing"
)

// TestSaveLyriaLocalFileWiring is a handler-level wiring test: it drives
// saveLyriaLocalFile (the function the handler calls to persist audio locally) with
// the os.WriteFile seam (writeFileFn) replaced by a recorder, and asserts that the
// resolved output_filename actually reaches the write. It pairs resolveLyriaOutputFilename
// with the write so the assertion covers the full name→write path: output_filename
// wins over the legacy file_name alias, the extension is forced to .wav, and the
// name is single-artifact (<stem>.wav — lyria returns one artifact; the shared
// _1..n suffix rule is covered where multi-output happens and in mcp-common).
func TestSaveLyriaLocalFileWiring(t *testing.T) {
	const dir = "/out"

	origWrite := writeFileFn
	t.Cleanup(func() { writeFileFn = origWrite })

	var gotPath string
	var gotBytes []byte
	writeFileFn = func(name string, data []byte, _ os.FileMode) error {
		gotPath, gotBytes = name, data
		return nil
	}

	cases := []struct {
		name   string
		params map[string]any
		want   string
	}{
		{"single artifact, ext kept", map[string]any{"output_filename": "song.wav"}, "song.wav"},
		{"wrong extension forced to .wav", map[string]any{"output_filename": "song.mp3"}, "song.wav"},
		{"legacy file_name alias used when output_filename unset", map[string]any{"file_name": "legacy.wav"}, "legacy.wav"},
		{"output_filename wins over legacy file_name", map[string]any{"output_filename": "new.wav", "file_name": "legacy.wav"}, "new.wav"},
		{"traversal sanitized before write", map[string]any{"output_filename": "../../etc/song.wav"}, "song.wav"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			gotPath, gotBytes = "", nil
			base, err := resolveLyriaOutputFilename(tc.params)
			if err != nil {
				t.Fatalf("resolveLyriaOutputFilename error: %v", err)
			}
			fullPath, werr := saveLyriaLocalFile(dir, base, []byte("audio"))
			if werr != nil {
				t.Fatalf("saveLyriaLocalFile error: %v", werr)
			}
			want := filepath.Join(dir, tc.want)
			if fullPath != want || gotPath != want {
				t.Errorf("fullPath=%q writeTarget=%q, want %q", fullPath, gotPath, want)
			}
			if string(gotBytes) != "audio" {
				t.Errorf("bytes written = %q, want %q", gotBytes, "audio")
			}
		})
	}

	t.Run("write error surfaced with the intended path", func(t *testing.T) {
		writeFileFn = func(string, []byte, os.FileMode) error { return fmt.Errorf("disk full") }
		t.Cleanup(func() {
			writeFileFn = func(name string, data []byte, _ os.FileMode) error { gotPath, gotBytes = name, data; return nil }
		})
		base, err := resolveLyriaOutputFilename(map[string]any{"output_filename": "song.wav"})
		if err != nil {
			t.Fatalf("resolve error: %v", err)
		}
		fullPath, werr := saveLyriaLocalFile(dir, base, []byte("a"))
		if werr == nil {
			t.Fatalf("expected write error")
		}
		if fullPath != filepath.Join(dir, "song.wav") {
			t.Errorf("path should still be reported on write error, got %q", fullPath)
		}
	})
}

// TestResolveLyriaOutputFilename covers the lyria naming decision: output_filename
// wins over the legacy file_name alias, the extension is forced to the audio MIME,
// traversal is sanitized, and unset -> "" (caller uses the shortid default).
func TestResolveLyriaOutputFilename(t *testing.T) {
	tests := []struct {
		name    string
		params  map[string]any
		want    string
		wantErr bool
	}{
		{
			name:   "output_filename honored, extension kept",
			params: map[string]any{"output_filename": "song.wav"},
			want:   "song.wav",
		},
		{
			name:   "wrong extension forced to audio MIME",
			params: map[string]any{"output_filename": "song.mp3"},
			want:   "song.wav",
		},
		{
			name:   "missing extension gets forced",
			params: map[string]any{"output_filename": "song"},
			want:   "song.wav",
		},
		{
			name:   "legacy file_name alias used when output_filename unset",
			params: map[string]any{"file_name": "legacy.wav"},
			want:   "legacy.wav",
		},
		{
			name:   "output_filename wins over legacy file_name",
			params: map[string]any{"output_filename": "new.wav", "file_name": "legacy.wav"},
			want:   "new.wav",
		},
		{
			name:   "traversal sanitized",
			params: map[string]any{"output_filename": "../../etc/song.wav"},
			want:   "song.wav",
		},
		{
			name:   "unset -> empty (shortid default)",
			params: map[string]any{},
			want:   "",
		},
		{
			name:    "dot-only base errors",
			params:  map[string]any{"output_filename": "..."},
			wantErr: true,
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := resolveLyriaOutputFilename(tc.params)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("resolveLyriaOutputFilename(%v) = %q, want error", tc.params, got)
				}
				return
			}
			if err != nil {
				t.Fatalf("resolveLyriaOutputFilename(%v) unexpected error: %v", tc.params, err)
			}
			if got != tc.want {
				t.Errorf("resolveLyriaOutputFilename(%v) = %q, want %q", tc.params, got, tc.want)
			}
		})
	}
}
