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

// Package main implements a standalone MCP server for Google's Gemini 3.5
// Transcribe speech-to-text model.
//
// This server exposes a single tool, gemini_transcribe, using the *synchronous*
// transcription API (generate_content on gemini-3.5-transcribe-preview), NOT the
// live/streaming API. It is the single-purpose sibling of the gemini_transcribe
// tool bundled into the all-in-one mcp-gemini-go server. Both share the exact
// same implementation via the mcp-common package, so the two can never drift.

package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"google.golang.org/genai"
)

var (
	appConfig   *common.Config
	genAIClient *genai.Client
	transport   string
	port        int
)

const (
	serviceName = "mcp-gemini-transcribe-go"
)

// version is overridden at build time via -ldflags "-X main.version=...".
// The single source of truth for the version is the VERSION file at the root
// of the mcp-genmedia-go tree (injected by the Makefile locally and by the git
// tag through goreleaser for releases). Defaults to "dev" for un-injected builds.
var version = "dev"

func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
	flag.IntVar(&port, "p", 0, "Port for SSE/HTTP server (defaults to PORT env var or 8080/8081)")
	flag.IntVar(&port, "port", 0, "Port for SSE/HTTP server (defaults to PORT env var or 8080/8081)")
}

func main() {
	flag.Parse() // Parse in main (not init) so `go test` flags are not consumed; matches sibling servers.

	var cleanup func()
	appConfig, cleanup = common.Init(serviceName, version)
	defer cleanup()

	// Gemini 3.5 Transcribe is served only in the "global" location. Default to
	// "global" if the location was not explicitly set (mirrors mcp-gemini-go).
	if os.Getenv("LOCATION") == "" && os.Getenv("GOOGLE_CLOUD_LOCATION") == "" {
		log.Printf("LOCATION not set. Defaulting to 'global' for %s.", serviceName)
		appConfig.Location = "global"
	}
	var err error

	log.Printf("Initializing global GenAI client...")
	clientCtx, clientCancel := context.WithTimeout(context.Background(), 1*time.Minute)
	defer clientCancel()

	clientConfig := &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  appConfig.ProjectID,
		Location: appConfig.Location,
	}
	if appConfig.ApiEndpoint != "" {
		log.Printf("Using custom Vertex AI endpoint: %s", appConfig.ApiEndpoint)
		clientConfig.HTTPOptions.BaseURL = appConfig.ApiEndpoint
	}

	if err := common.InjectCaptureHeaders(clientCtx, appConfig, clientConfig); err != nil {
		log.Printf("Warning: Failed to inject capture headers: %v", err)
	}

	genAIClient, err = genai.NewClient(clientCtx, clientConfig)
	if err != nil {
		log.Printf("Warning: Error creating global GenAI client: %v. Deferring initialization to runtime.", err)
	} else {
		log.Printf("Global GenAI client initialized successfully.")
	}

	s := server.NewMCPServer("Gemini Transcribe", version, server.WithResourceCapabilities(true, false))

	// --- Register Gemini Transcribe Tool ---
	// Synchronous speech-to-text via Gemini 3.5 Transcribe (the generate_content
	// path on gemini-3.5-transcribe-preview, NOT the live/streaming API). The
	// handler is a thin wrapper over the shared common.Transcribe helpers, so it
	// stays in lockstep with the bundled tool in mcp-gemini-go.
	transcribeTool := mcp.NewTool("gemini_transcribe",
		mcp.WithDescription("Transcribes a pre-recorded audio file to text using Google's Gemini 3.5 Transcribe model (synchronous mode). Supports language hints, custom vocabulary biasing, speaker diarization, word-level timestamps, and smart formatting. Audio must be <=15 minutes."),
		mcp.WithString("input_audio",
			mcp.Required(),
			mcp.Description("The audio to transcribe: either a local file path or a gs:// URI. Supported formats include WAV, MP3, OGG/Opus, FLAC, M4A/AAC, AIFF, AMR, WEBM, and PCM."),
		),
		mcp.WithString("mime_type",
			mcp.Description("Optional. The MIME type of the audio (e.g. audio/wav, audio/mpeg, audio/ogg). Inferred from the file extension when omitted."),
		),
		mcp.WithString("model",
			mcp.DefaultString(common.DefaultTranscribeModel),
			mcp.Description("Optional. The transcription model to use. Defaults to the synchronous gemini-3.5-transcribe-preview."),
		),
		mcp.WithArray("language_codes",
			mcp.Items(map[string]any{"type": "string"}),
			mcp.Description("Optional. BCP-47 language code hints (e.g. [\"en-US\", \"es-ES\"]). Omit for automatic language detection."),
		),
		mcp.WithArray("custom_vocabulary",
			mcp.Items(map[string]any{"type": "string"}),
			mcp.Description("Optional. Up to 1000 phrases (brand names, proper nouns, domain terms) that bias recognition. Most reliable when language_codes is also set."),
		),
		mcp.WithBoolean("enable_diarization",
			mcp.Description("Optional. Label individual speakers (up to 8). Incompatible with smart_formatting."),
		),
		mcp.WithBoolean("enable_word_timestamps",
			mcp.Description("Optional. Return word-level start/end offsets. Incompatible with smart_formatting."),
		),
		mcp.WithBoolean("smart_formatting",
			mcp.Description("Optional. Use SMART mode: filler-word removal, light grammatical cleanup, and automatic formatting. Incompatible with enable_diarization and enable_word_timestamps."),
		),
		mcp.WithString("output_directory",
			mcp.Description("Optional. Local directory to save the transcription result (JSON) to. When omitted, the transcript is returned in the response only."),
		),
		mcp.WithString("gcs_bucket_uri",
			mcp.Description("Optional. GCS URI prefix to store the transcription result (JSON), e.g. your-bucket/transcripts/."),
		),
		mcp.WithString("output_filename",
			mcp.Description("Optional. Client-predictable base name for the saved transcript. The extension is forced to .json. An existing file/object of the same name is overwritten."),
		),
	)
	s.AddTool(transcribeTool, func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return geminiTranscribeHandler(genAIClient, ctx, request)
	})
	// --- End of Gemini Transcribe Tool ---

	switch transport {
	case "sse":
		ssePort := 8081 // Default SSE port
		if port != 0 {
			ssePort = port
		} else if p, err := strconv.Atoi(os.Getenv("PORT")); err == nil {
			ssePort = p
		}
		log.Printf("Starting %s MCP Server (Version: %s, Transport: sse, Port: %d)", serviceName, version, ssePort)
		sseServer := server.NewSSEServer(s, server.WithBaseURL(fmt.Sprintf("http://localhost:%d", ssePort)))
		if err := sseServer.Start(fmt.Sprintf(":%d", ssePort)); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
	case "http":
		httpPort := 8080 // Default HTTP port
		if port != 0 {
			httpPort = port
		} else if p, err := strconv.Atoi(os.Getenv("PORT")); err == nil {
			httpPort = p
		}
		log.Printf("Starting %s MCP Server (Version: %s, Transport: http, Port: %d)", serviceName, version, httpPort)
		http.Handle("/mcp", server.NewStreamableHTTPServer(s))
		if err := http.ListenAndServe(fmt.Sprintf(":%d", httpPort), nil); err != nil {
			log.Fatalf("HTTP Server error: %v", err)
		}
	case "stdio":
		log.Printf("Starting %s MCP Server (Version: %s, Transport: stdio)", serviceName, version)
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	default:
		log.Fatalf("Unsupported transport type: %s. Please use 'stdio', 'sse', or 'http'.", transport)
	}
}
