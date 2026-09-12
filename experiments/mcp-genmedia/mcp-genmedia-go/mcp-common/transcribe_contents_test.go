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
	"testing"
)

// TestBuildTranscribeContentsErrors exercises the guard branches of
// buildTranscribeContents: missing mime type, both sources supplied, no source
// supplied, an unreadable file, and an empty file.
func TestBuildTranscribeContentsErrors(t *testing.T) {
	t.Run("missing mime type", func(t *testing.T) {
		if _, err := buildTranscribeContents(TranscribeParams{LocalPath: "/tmp/x.wav"}); err == nil {
			t.Fatal("expected error for empty mime type, got nil")
		}
	})

	t.Run("both sources rejected", func(t *testing.T) {
		_, err := buildTranscribeContents(TranscribeParams{
			LocalPath: "/tmp/x.wav",
			GCSURI:    "gs://bucket/x.wav",
			MimeType:  "audio/wav",
		})
		if err == nil {
			t.Fatal("expected error when both local path and gs:// URI are set, got nil")
		}
	})

	t.Run("no source rejected", func(t *testing.T) {
		if _, err := buildTranscribeContents(TranscribeParams{MimeType: "audio/wav"}); err == nil {
			t.Fatal("expected error when no audio source is provided, got nil")
		}
	})

	t.Run("unreadable local file", func(t *testing.T) {
		missing := filepath.Join(t.TempDir(), "does-not-exist.wav")
		if _, err := buildTranscribeContents(TranscribeParams{LocalPath: missing, MimeType: "audio/wav"}); err == nil {
			t.Fatal("expected error for missing local file, got nil")
		}
	})

	t.Run("empty local file", func(t *testing.T) {
		empty := filepath.Join(t.TempDir(), "empty.wav")
		if err := os.WriteFile(empty, nil, 0o600); err != nil {
			t.Fatalf("failed to create empty file: %v", err)
		}
		if _, err := buildTranscribeContents(TranscribeParams{LocalPath: empty, MimeType: "audio/wav"}); err == nil {
			t.Fatal("expected error for empty local file, got nil")
		}
	})

	t.Run("valid gcs source", func(t *testing.T) {
		contents, err := buildTranscribeContents(TranscribeParams{GCSURI: "gs://bucket/clip.wav", MimeType: "audio/wav"})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if len(contents) != 1 || len(contents[0].Parts) != 1 {
			t.Fatalf("unexpected contents shape: %+v", contents)
		}
	})
}

// TestTranscribeNilClient verifies Transcribe fails fast with a clear error when
// the genai client was never initialized (e.g. client construction was deferred
// to runtime and never succeeded).
func TestTranscribeNilClient(t *testing.T) {
	_, err := Transcribe(context.Background(), nil, TranscribeParams{
		GCSURI:   "gs://bucket/clip.wav",
		MimeType: "audio/wav",
	})
	if err == nil {
		t.Fatal("expected error for nil genai client, got nil")
	}
}
