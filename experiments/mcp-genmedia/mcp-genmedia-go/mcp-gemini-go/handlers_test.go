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
	"context"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"google.golang.org/genai"
)

func imageResponse(parts ...*genai.Part) *genai.GenerateContentResponse {
	return &genai.GenerateContentResponse{
		Candidates: []*genai.Candidate{{Content: &genai.Content{Parts: parts}}},
	}
}

func textPart(s string) *genai.Part { return &genai.Part{Text: s} }

func imagePart(mime string, data []byte) *genai.Part {
	return &genai.Part{InlineData: &genai.Blob{MIMEType: mime, Data: data}}
}

// TestProcessGeminiImageResponseNaming exercises the actual handler response path
// (two-pass count/assign, imgIdx, output_filename -> local write target) with an
// injected write seam, so the naming wiring is validated without a live client.
func TestProcessGeminiImageResponseNaming(t *testing.T) {
	orig := writeFileFn
	t.Cleanup(func() { writeFileFn = orig })

	capture := func() *[]string {
		var got []string
		writeFileFn = func(path string, _ []byte, _ os.FileMode) error {
			got = append(got, filepath.Base(path))
			return nil
		}
		return &got
	}

	t.Run("output_filename single, extension forced", func(t *testing.T) {
		got := capture()
		// output_directory is confined to MCP_OUTPUT_ROOT (CWE-22): pass a relative
		// dir under a configured root instead of an absolute temp dir.
		dir := t.TempDir()
		t.Setenv("MCP_OUTPUT_ROOT", filepath.Dir(dir))
		resp := imageResponse(textPart("hi"), imagePart("image/png", []byte("a")))
		// Wrong client extension (.jpeg) must be forced to the true MIME (.png).
		if _, err := processGeminiImageResponse(context.Background(), resp, map[string]any{"output_filename": "hero.jpeg"}, filepath.Base(dir), "", "", ""); err != nil {
			t.Fatalf("error: %v", err)
		}
		if want := []string{"hero.png"}; !reflect.DeepEqual(*got, want) {
			t.Errorf("written names = %v, want %v", *got, want)
		}
	})

	t.Run("output_filename multiple, 1-based suffix", func(t *testing.T) {
		got := capture()
		dir := t.TempDir()
		t.Setenv("MCP_OUTPUT_ROOT", filepath.Dir(dir))
		resp := imageResponse(
			imagePart("image/png", []byte("a")),
			imagePart("image/png", []byte("b")),
			imagePart("image/png", []byte("c")),
		)
		if _, err := processGeminiImageResponse(context.Background(), resp, map[string]any{"output_filename": "hero"}, filepath.Base(dir), "", "", ""); err != nil {
			t.Fatalf("error: %v", err)
		}
		want := []string{"hero_1.png", "hero_2.png", "hero_3.png"}
		if !reflect.DeepEqual(*got, want) {
			t.Errorf("written names = %v, want %v", *got, want)
		}
	})

	t.Run("unset output_filename keeps legacy gemini_* scheme", func(t *testing.T) {
		got := capture()
		dir := t.TempDir()
		t.Setenv("MCP_OUTPUT_ROOT", filepath.Dir(dir))
		resp := imageResponse(imagePart("image/jpeg", []byte("a")))
		if _, err := processGeminiImageResponse(context.Background(), resp, map[string]any{}, filepath.Base(dir), "", "", ""); err != nil {
			t.Fatalf("error: %v", err)
		}
		if len(*got) != 1 || filepath.Ext((*got)[0]) != ".jpg" || (*got)[0][:7] != "gemini_" {
			t.Errorf("expected legacy gemini_*.jpg name, got %v", *got)
		}
	})
}
