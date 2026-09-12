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

// Package main implements a standalone MCP server for Gemini 3.5 Transcribe.
//
// This handler is byte-for-byte the same thin wrapper the all-in-one
// mcp-gemini-go server uses: it parses/validates the tool arguments via
// common.ParseTranscribeToolArgs, calls the shared common.Transcribe entry point
// with the global genai client, and renders the response via
// common.RenderTranscribeResult. All real logic lives once in mcp-common so the
// two servers can never drift.

package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/genai"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// geminiTranscribeHandler is a thin MCP wrapper around the shared mcp-common
// transcription plumbing.
func geminiTranscribeHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "gemini_transcribe")
	defer span.End()

	parsed, err := common.ParseTranscribeToolArgs(request.GetArguments())
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	span.SetAttributes(
		attribute.String("model", parsed.Params.Model),
		attribute.String("mime_type", parsed.Params.MimeType),
		attribute.Bool("diarization", parsed.Params.Diarization),
		attribute.Bool("word_timestamps", parsed.Params.WordTimestamps),
		attribute.Bool("smart_formatting", parsed.Params.SmartFormatting),
		attribute.Int("language_codes", len(parsed.Params.LanguageCodes)),
		attribute.String("output_directory", parsed.OutputDir),
		attribute.String("gcs_bucket_uri", parsed.GCSBucketURI),
	)

	// Detach from any short inherited client/request deadline: transcription of a
	// multi-minute file can take a while. Cap it generously.
	callCtx, cancel := context.WithTimeout(ctx, 10*time.Minute)
	defer cancel()

	log.Printf("Calling Transcribe Model=%s mime=%s diarization=%t word_timestamps=%t smart=%t", parsed.Params.Model, parsed.Params.MimeType, parsed.Params.Diarization, parsed.Params.WordTimestamps, parsed.Params.SmartFormatting)
	startTime := time.Now()

	result, err := common.Transcribe(callCtx, client, parsed.Params)

	apiCallDuration := time.Since(startTime)
	log.Printf("Transcribe call took: %v", apiCallDuration)
	span.SetAttributes(attribute.Float64("duration_ms", float64(apiCallDuration.Milliseconds())))

	if err != nil {
		span.RecordError(err)
		return mcp.NewToolResultError(fmt.Sprintf("error transcribing audio: %v", err)), nil
	}
	span.SetAttributes(attribute.Int("segments", len(result.Segments)))

	content, err := common.RenderTranscribeResult(ctx, result, parsed.OutputDir, parsed.GCSBucketURI, parsed.OutputFilename)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	return &mcp.CallToolResult{Content: content}, nil
}
