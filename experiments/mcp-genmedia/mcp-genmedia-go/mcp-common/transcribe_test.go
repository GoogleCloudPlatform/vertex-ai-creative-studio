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
	"testing"

	"google.golang.org/genai"
)

func TestParseTranscribeToolArgs(t *testing.T) {
	tests := []struct {
		name    string
		args    map[string]any
		wantErr bool
		check   func(t *testing.T, p *ParsedTranscribeArgs)
	}{
		{
			name:    "missing input_audio",
			args:    map[string]any{},
			wantErr: true,
		},
		{
			name: "local path infers wav mime and defaults model",
			args: map[string]any{"input_audio": "/tmp/sample.wav"},
			check: func(t *testing.T, p *ParsedTranscribeArgs) {
				if p.Params.LocalPath != "/tmp/sample.wav" {
					t.Errorf("LocalPath = %q", p.Params.LocalPath)
				}
				if p.Params.GCSURI != "" {
					t.Errorf("GCSURI should be empty, got %q", p.Params.GCSURI)
				}
				if p.Params.MimeType != "audio/wav" {
					t.Errorf("MimeType = %q, want audio/wav", p.Params.MimeType)
				}
				if p.Params.Model != DefaultTranscribeModel {
					t.Errorf("Model = %q, want %q", p.Params.Model, DefaultTranscribeModel)
				}
			},
		},
		{
			name: "gs uri routed to GCSURI",
			args: map[string]any{"input_audio": "gs://bucket/clip.mp3"},
			check: func(t *testing.T, p *ParsedTranscribeArgs) {
				if p.Params.GCSURI != "gs://bucket/clip.mp3" {
					t.Errorf("GCSURI = %q", p.Params.GCSURI)
				}
				if p.Params.LocalPath != "" {
					t.Errorf("LocalPath should be empty, got %q", p.Params.LocalPath)
				}
				if p.Params.MimeType != "audio/mpeg" {
					t.Errorf("MimeType = %q, want audio/mpeg", p.Params.MimeType)
				}
			},
		},
		{
			name:    "unknown extension without mime_type errors",
			args:    map[string]any{"input_audio": "/tmp/sample.xyz"},
			wantErr: true,
		},
		{
			name: "explicit mime_type overrides inference",
			args: map[string]any{"input_audio": "/tmp/sample.xyz", "mime_type": "audio/wav"},
			check: func(t *testing.T, p *ParsedTranscribeArgs) {
				if p.Params.MimeType != "audio/wav" {
					t.Errorf("MimeType = %q, want audio/wav", p.Params.MimeType)
				}
			},
		},
		{
			name: "smart_formatting with diarization is rejected",
			args: map[string]any{
				"input_audio":        "/tmp/sample.wav",
				"smart_formatting":   true,
				"enable_diarization": true,
			},
			wantErr: true,
		},
		{
			name: "feature flags and arrays parsed",
			args: map[string]any{
				"input_audio":            "/tmp/sample.wav",
				"language_codes":         []any{"en-US", " es-ES ", ""},
				"custom_vocabulary":      "oatmilk, oz ,",
				"enable_diarization":     true,
				"enable_word_timestamps": "true",
				"output_directory":       "/out",
				"gcs_bucket_uri":         "my-bucket/transcripts/",
				"output_filename":        "meeting.txt",
			},
			check: func(t *testing.T, p *ParsedTranscribeArgs) {
				if len(p.Params.LanguageCodes) != 2 || p.Params.LanguageCodes[0] != "en-US" || p.Params.LanguageCodes[1] != "es-ES" {
					t.Errorf("LanguageCodes = %v", p.Params.LanguageCodes)
				}
				if len(p.Params.CustomVocabulary) != 2 || p.Params.CustomVocabulary[0] != "oatmilk" || p.Params.CustomVocabulary[1] != "oz" {
					t.Errorf("CustomVocabulary = %v", p.Params.CustomVocabulary)
				}
				if !p.Params.Diarization || !p.Params.WordTimestamps {
					t.Errorf("expected diarization and word timestamps enabled")
				}
				if p.OutputDir != "/out" {
					t.Errorf("OutputDir = %q", p.OutputDir)
				}
				if p.GCSBucketURI != "gs://my-bucket/transcripts/" {
					t.Errorf("GCSBucketURI = %q", p.GCSBucketURI)
				}
				if p.OutputFilename != "meeting.txt" {
					t.Errorf("OutputFilename = %q", p.OutputFilename)
				}
			},
		},
		{
			name: "custom vocabulary over limit rejected",
			args: map[string]any{
				"input_audio":       "/tmp/sample.wav",
				"custom_vocabulary": makeStrings(maxTranscribeCustomVocabulary + 1),
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseTranscribeToolArgs(tt.args)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error, got nil")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if tt.check != nil {
				tt.check(t, got)
			}
		})
	}
}

func TestBuildTranscribeConfig(t *testing.T) {
	p := TranscribeParams{
		LanguageCodes:    []string{"en-US"},
		CustomVocabulary: []string{"oatmilk"},
		Diarization:      true,
		WordTimestamps:   true,
	}
	cfg := buildTranscribeConfig(p)
	atc := cfg.AudioTranscriptionConfig
	if atc == nil {
		t.Fatal("AudioTranscriptionConfig is nil")
	}
	if len(atc.LanguageCodes) != 1 || atc.LanguageCodes[0] != "en-US" {
		t.Errorf("LanguageCodes = %v", atc.LanguageCodes)
	}
	if len(atc.CustomVocabulary) != 1 || atc.CustomVocabulary[0] != "oatmilk" {
		t.Errorf("CustomVocabulary = %v", atc.CustomVocabulary)
	}
	if atc.Diarization == nil || !*atc.Diarization {
		t.Errorf("Diarization not set true")
	}
	if atc.WordTimestamp == nil || !*atc.WordTimestamp {
		t.Errorf("WordTimestamp not set true")
	}
	if atc.Mode != "" {
		t.Errorf("Mode should be unset without smart formatting, got %q", atc.Mode)
	}

	smart := buildTranscribeConfig(TranscribeParams{SmartFormatting: true})
	if smart.AudioTranscriptionConfig.Mode != genai.AudioTranscriptionConfigModeSmart {
		t.Errorf("Mode = %q, want SMART", smart.AudioTranscriptionConfig.Mode)
	}
}

func TestMapTranscribeResponse(t *testing.T) {
	t.Run("plain text parts", func(t *testing.T) {
		resp := &genai.GenerateContentResponse{
			Candidates: []*genai.Candidate{
				{Content: &genai.Content{Parts: []*genai.Part{
					{Text: "hello"},
					{Text: "world"},
				}}},
			},
		}
		got := mapTranscribeResponse("m", resp)
		if got.Transcript != "hello world" {
			t.Errorf("Transcript = %q, want %q", got.Transcript, "hello world")
		}
		if got.HasStructuredDetail() {
			t.Errorf("expected no structured detail")
		}
	})

	t.Run("diarized parts", func(t *testing.T) {
		resp := &genai.GenerateContentResponse{
			Candidates: []*genai.Candidate{
				{Content: &genai.Content{Parts: []*genai.Part{
					{AudioTranscription: &genai.Transcription{Text: "one oatmilk please", SpeakerLabel: "spk_1"}},
					{AudioTranscription: &genai.Transcription{Text: "coming right up", SpeakerLabel: "spk_2"}},
				}}},
			},
		}
		got := mapTranscribeResponse("m", resp)
		want := "spk_1: one oatmilk please\nspk_2: coming right up"
		if got.Transcript != want {
			t.Errorf("Transcript = %q, want %q", got.Transcript, want)
		}
		if !got.HasStructuredDetail() {
			t.Errorf("expected structured detail for diarized output")
		}
		if len(got.Segments) != 2 || got.Segments[0].SpeakerLabel != "spk_1" {
			t.Errorf("Segments = %+v", got.Segments)
		}
	})

	t.Run("word timestamps", func(t *testing.T) {
		resp := &genai.GenerateContentResponse{
			Candidates: []*genai.Candidate{
				{Content: &genai.Content{Parts: []*genai.Part{
					{
						Text: "hi there",
						AudioTranscription: &genai.Transcription{Words: []*genai.WordInfo{
							{Word: "hi", StartOffset: "0s", EndOffset: "0.5s"},
							{Word: "there", StartOffset: "0.5s", EndOffset: "1s"},
						}},
					},
				}}},
			},
		}
		got := mapTranscribeResponse("m", resp)
		if got.Transcript != "hi there" {
			t.Errorf("Transcript = %q", got.Transcript)
		}
		if len(got.Segments) != 1 || len(got.Segments[0].Words) != 2 {
			t.Fatalf("Segments = %+v", got.Segments)
		}
		if got.Segments[0].Words[0].Word != "hi" || got.Segments[0].Words[0].StartOffset != "0s" {
			t.Errorf("Words[0] = %+v", got.Segments[0].Words[0])
		}
	})

	t.Run("nil response", func(t *testing.T) {
		got := mapTranscribeResponse("m", nil)
		if got.Transcript != "" || len(got.Segments) != 0 {
			t.Errorf("expected empty result, got %+v", got)
		}
	})
}

func TestInferAudioMIMEType(t *testing.T) {
	cases := map[string]string{
		"/a/b/c.wav":      "audio/wav",
		"clip.MP3":        "audio/mpeg",
		"gs://x/y.ogg":    "audio/ogg",
		"song.flac":       "audio/flac",
		"voice.m4a":       "audio/mp4",
		"note.unknownext": "",
		"noextension":     "",
	}
	for in, want := range cases {
		if got := InferAudioMIMEType(in); got != want {
			t.Errorf("InferAudioMIMEType(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestTranscribeOutputFilename(t *testing.T) {
	if got := transcribeOutputFilename("meeting.txt"); got != "meeting.json" {
		t.Errorf("got %q, want meeting.json", got)
	}
	if got := transcribeOutputFilename("../../etc/passwd"); got != "passwd.json" {
		t.Errorf("got %q, want passwd.json", got)
	}
	got := transcribeOutputFilename("")
	if len(got) < len("transcript-.json") || got[:11] != "transcript-" {
		t.Errorf("default filename = %q", got)
	}
}

func makeStrings(n int) []any {
	out := make([]any, n)
	for i := range out {
		out[i] = "term"
	}
	return out
}
