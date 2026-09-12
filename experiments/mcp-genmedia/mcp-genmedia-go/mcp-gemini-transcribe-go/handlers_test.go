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
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
)

// newTranscribeRequest builds a gemini_transcribe CallToolRequest with the given
// arguments for handler-level smoke tests.
func newTranscribeRequest(args map[string]any) mcp.CallToolRequest {
	var req mcp.CallToolRequest
	req.Params.Name = "gemini_transcribe"
	req.Params.Arguments = args
	return req
}

// TestGeminiTranscribeHandlerInvalidArgs verifies the standalone wrapper surfaces
// argument-validation failures (from the shared common.ParseTranscribeToolArgs)
// as an MCP tool error rather than panicking or returning a transport error.
func TestGeminiTranscribeHandlerInvalidArgs(t *testing.T) {
	res, err := geminiTranscribeHandler(nil, context.Background(), newTranscribeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("handler returned transport error, want nil: %v", err)
	}
	if res == nil || !res.IsError {
		t.Fatalf("expected an MCP tool error result for missing input_audio, got %+v", res)
	}
}

// TestGeminiTranscribeHandlerNilClient verifies that, with otherwise-valid args, a
// nil genai client (deferred construction that never succeeded) is surfaced as a
// tool error via common.Transcribe's guard — not a panic.
func TestGeminiTranscribeHandlerNilClient(t *testing.T) {
	res, err := geminiTranscribeHandler(nil, context.Background(), newTranscribeRequest(map[string]any{
		"input_audio": "gs://bucket/clip.wav",
	}))
	if err != nil {
		t.Fatalf("handler returned transport error, want nil: %v", err)
	}
	if res == nil || !res.IsError {
		t.Fatalf("expected an MCP tool error result for nil client, got %+v", res)
	}
}
