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
	"encoding/base64"
	"testing"
)

// sampleMP4 is a tiny byte sequence with a valid MP4 "ftyp" box, used to verify
// the steps[] -> decoded bytes mapping without a live call.
var sampleMP4 = []byte{
	0x00, 0x00, 0x00, 0x18, 'f', 't', 'y', 'p', 'i', 's', 'o', 'm',
	0x00, 0x00, 0x02, 0x00, 'i', 's', 'o', 'm',
}

// omniResponseJSON reproduces the observed live Omni response drift (findings §3):
// results in steps[] (not outputs[]), a leading thought step, created/updated
// timestamps, lowercase status, and extra usage fields — all of which the mapper
// must tolerate while still recovering the video bytes.
func omniResponseJSON(b64video string) string {
	// Mirrors the observed live wire (2026-05-20): RFC3339 created/updated, a
	// thought step whose "summary" is an ARRAY of parts (not a string) plus a
	// "signature" string, usage fields with *_by_modality arrays, and results in
	// steps[]. A tolerant decode must ignore all of these and still recover video.
	return `{
		"id": "abc123",
		"object": "interaction",
		"model": "gemini-omni-flash-preview",
		"status": "completed",
		"role": "model",
		"created": "2026-08-10T14:41:24Z",
		"updated": "2026-08-10T14:41:24Z",
		"steps": [
			{"type": "thought", "signature": "AY89a1RDWvi", "summary": [{"type": "text", "text": "thinking about balloons"}]},
			{"type": "model_output", "content": [
				{"type": "text", "text": "Here is your video."},
				{"type": "video", "mime_type": "video/mp4", "data": "` + b64video + `"}
			]}
		],
		"usage": {"total_tokens": 17560, "total_input_tokens": 15, "input_tokens_by_modality": [{"modality": "text", "tokens": 15}], "total_output_tokens": 17376, "output_tokens_by_modality": [{"modality": "video", "tokens": 17376}], "total_tool_use_tokens": 0, "total_thought_tokens": 169}
	}`
}

func TestDecodeAndMapOmniResponse(t *testing.T) {
	b64 := base64.StdEncoding.EncodeToString(sampleMP4)
	resp, err := decodeInteractionResponse([]byte(omniResponseJSON(b64)))
	if err != nil {
		t.Fatalf("decodeInteractionResponse returned error: %v", err)
	}

	if resp.Status != "completed" {
		t.Errorf("status = %q, want completed", resp.Status)
	}
	if len(resp.Steps) != 2 {
		t.Fatalf("len(Steps) = %d, want 2", len(resp.Steps))
	}

	result, err := mapOmniResponse(resp)
	if err != nil {
		t.Fatalf("mapOmniResponse returned error: %v", err)
	}
	if result.ThoughtSteps != 1 {
		t.Errorf("ThoughtSteps = %d, want 1", result.ThoughtSteps)
	}
	if result.Text != "Here is your video." {
		t.Errorf("Text = %q, want %q", result.Text, "Here is your video.")
	}
	if len(result.Videos) != 1 {
		t.Fatalf("len(Videos) = %d, want 1", len(result.Videos))
	}
	if string(result.Videos[0]) != string(sampleMP4) {
		t.Errorf("decoded video bytes do not match the source bytes")
	}
	if !hasFtypBox(result.Videos[0]) {
		t.Errorf("decoded video is missing an ftyp box")
	}
	if len(result.VideoMimeTypes) != 1 || result.VideoMimeTypes[0] != "video/mp4" {
		t.Errorf("VideoMimeTypes = %v, want [video/mp4]", result.VideoMimeTypes)
	}
}

func TestMapOmniResponseNoVideo(t *testing.T) {
	resp := &InteractionResponse{
		Status: "completed",
		Steps: []Step{
			{Type: "model_output", Content: []Part{{Type: "text", Text: "sorry, no video"}}},
		},
	}
	if _, err := mapOmniResponse(resp); err == nil {
		t.Errorf("expected an error when no video part is present, got nil")
	}
}

func TestBuildOmniRequest(t *testing.T) {
	req := buildOmniRequest("gemini-omni-flash-preview", OmniParams{Prompt: "a red balloon"})
	if req.Model != "gemini-omni-flash-preview" {
		t.Errorf("Model = %q", req.Model)
	}
	if len(req.ResponseModalities) != 2 || req.ResponseModalities[0] != "text" || req.ResponseModalities[1] != "video" {
		t.Errorf("ResponseModalities = %v, want lowercase [text video]", req.ResponseModalities)
	}
	if len(req.Input) != 1 || req.Input[0].Type != "user_input" {
		t.Fatalf("Input shape unexpected: %+v", req.Input)
	}
	if len(req.Input[0].Content) != 1 || req.Input[0].Content[0].Text != "a red balloon" {
		t.Errorf("Input content unexpected: %+v", req.Input[0].Content)
	}
}

func TestResolveOmniModel(t *testing.T) {
	cases := []struct {
		in    string
		want  string
		found bool
	}{
		{"", "gemini-omni-flash-preview", true},
		{"gemini-omni-flash-preview", "gemini-omni-flash-preview", true},
		{"Omni", "gemini-omni-flash-preview", true},
		{"nonexistent-model", "", false},
	}
	for _, c := range cases {
		info, found := ResolveOmniModel(c.in, false)
		if found != c.found {
			t.Errorf("ResolveOmniModel(%q) found = %v, want %v", c.in, found, c.found)
			continue
		}
		if found && info.CanonicalName != c.want {
			t.Errorf("ResolveOmniModel(%q) = %q, want %q", c.in, info.CanonicalName, c.want)
		}
	}

	// allowUnsafe passes through an unknown model.
	info, found := ResolveOmniModel("some-future-omni", true)
	if !found || info.CanonicalName != "some-future-omni" {
		t.Errorf("allowUnsafe fallback failed: found=%v info=%+v", found, info)
	}
}

// hasFtypBox reports whether the bytes contain an MP4 "ftyp" box marker in the
// first 12 bytes (bytes 4-8), matching the acceptance-gate ftyp check.
func hasFtypBox(b []byte) bool {
	return len(b) >= 8 && string(b[4:8]) == "ftyp"
}
