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

// Package main implements an MCP server for Google's Gemini Omni video model.
//
// Omni (gemini-omni-flash-preview) is reachable only through the Vertex
// Interactions API, so this server calls the shared common.GenerateOmniVideo
// helper (which owns the Interactions client) rather than the shared genai.Client.

package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

var (
	appConfig *common.Config
	transport string
	port      int
)

const (
	serviceName = "mcp-omni-go"
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
	flag.Parse()

	var cleanup func()
	appConfig, cleanup = common.Init(serviceName, version)
	defer cleanup()

	// Omni is global-only via the Interactions API. Default the location to
	// "global" if not explicitly set (mirrors nanobanana/gemini main.go). The
	// interactions call hard-pins "global" regardless; this keeps config coherent.
	if os.Getenv("LOCATION") == "" && os.Getenv("OMNI_LOCATION") == "" && os.Getenv("GOOGLE_CLOUD_LOCATION") == "" {
		log.Printf("LOCATION not set. Defaulting to 'global' for %s.", serviceName)
		appConfig.Location = "global"
	}

	s := server.NewMCPServer("Gemini Omni", version, server.WithResourceCapabilities(true, false))

	tool := mcp.NewTool("omni_video_generation",
		mcp.WithDescription("Generates video (with optional embedded audio) from a text prompt using Google's Gemini Omni model via the Vertex Interactions API. Returns MP4(s) saved locally and/or to GCS."),
		mcp.WithString("prompt", mcp.Required(), mcp.Description("The text prompt describing the video to generate.")),
		mcp.WithString("output_directory", mcp.Description("Optional. Local directory to save the generated video(s) to.")),
		mcp.WithString("gcs_bucket_uri", mcp.Description("Optional. GCS URI prefix to store generated video(s) (e.g., your-bucket/outputs/). Falls back to GENMEDIA_BUCKET+/omni_outputs/ if set.")),
	)
	s.AddTool(tool, omniVideoGenerationHandler)

	switch transport {
	case "sse":
		ssePort := 8081
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
		httpPort := 8080
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
