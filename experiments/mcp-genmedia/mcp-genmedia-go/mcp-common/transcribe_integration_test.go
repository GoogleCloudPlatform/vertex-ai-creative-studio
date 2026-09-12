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

//go:build integration

// This file is guarded by the `integration` build tag so it never runs in the
// default `go test ./...` / CI path. It provides a committed, reproducible
// harness for the empirical live-transcription claim: it makes a real
// synchronous call against Gemini 3.5 Transcribe on Vertex AI.
//
// Run it explicitly with real credentials, e.g.:
//
//	GOOGLE_CLOUD_PROJECT=your-project \
//	TRANSCRIBE_TEST_AUDIO=gs://your-bucket/sample.wav \
//	go test -tags integration -run TestTranscribeLive -v ./...
//
// It skips (rather than fails) when GOOGLE_CLOUD_PROJECT or TRANSCRIBE_TEST_AUDIO
// is unset, so it is safe to invoke in environments without credentials.

package common

import (
	"context"
	"os"
	"strings"
	"testing"
	"time"

	"google.golang.org/genai"
)

func TestTranscribeLive(t *testing.T) {
	project := strings.TrimSpace(os.Getenv("GOOGLE_CLOUD_PROJECT"))
	if project == "" {
		t.Skip("GOOGLE_CLOUD_PROJECT not set; skipping live transcription integration test")
	}
	audio := strings.TrimSpace(os.Getenv("TRANSCRIBE_TEST_AUDIO"))
	if audio == "" {
		t.Skip("TRANSCRIBE_TEST_AUDIO not set (local path or gs:// URI); skipping live transcription integration test")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  project,
		Location: "global", // Gemini 3.5 Transcribe is served only in "global".
	})
	if err != nil {
		t.Fatalf("failed to create genai client: %v", err)
	}

	params := TranscribeParams{MimeType: InferAudioMIMEType(audio)}
	if strings.HasPrefix(audio, "gs://") {
		params.GCSURI = audio
	} else {
		params.LocalPath = audio
	}
	if params.MimeType == "" {
		t.Fatalf("could not infer MIME type for %q; use a recognized extension", audio)
	}

	result, err := Transcribe(ctx, client, params)
	if err != nil {
		t.Fatalf("Transcribe failed: %v", err)
	}
	if strings.TrimSpace(result.Transcript) == "" {
		t.Fatalf("expected a non-empty transcript, got empty result: %+v", result)
	}
	t.Logf("transcript: %s", result.Transcript)
}
