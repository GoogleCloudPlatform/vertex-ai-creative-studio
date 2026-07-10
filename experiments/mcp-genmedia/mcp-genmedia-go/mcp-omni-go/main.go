// Copyright 2026 Google LLC
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
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/ghchinoy/cloud-interactions-go"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"golang.org/x/oauth2/google"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

const (
	serviceName = "mcp-omni-go"
	version     = "3.9.1"
)

var (
	transport string
	port      int
	appConfig *common.Config
)

func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
	flag.IntVar(&port, "p", 0, "Port for SSE/HTTP server (defaults to PORT env var or 8080/8081)")
	flag.IntVar(&port, "port", 0, "Port for SSE/HTTP server (defaults to PORT env var or 8080/8081)")
	flag.Parse()
}

func main() {
	var cleanup func()
	appConfig, cleanup = common.Init(serviceName, version)
	defer cleanup()

	if os.Getenv("LOCATION") == "" && os.Getenv("GOOGLE_CLOUD_LOCATION") == "" && os.Getenv("OMNI_LOCATION") == "" {
		log.Printf("LOCATION environment variable not set. Defaulting to 'global' for mcp-omni-go.")
		appConfig.Location = "global"
	}

	location := appConfig.Location
	if location == "" {
		location = "global"
	}

	var baseURL string
	if location == "global" {
		baseURL = fmt.Sprintf("https://aiplatform.googleapis.com/v1beta1/projects/%s/locations/global/interactions", appConfig.ProjectID)
	} else {
		baseURL = fmt.Sprintf("https://%s-aiplatform.googleapis.com/v1beta1/projects/%s/locations/%s/interactions", location, appConfig.ProjectID, location)
	}
	log.Printf("Initializing Interactions client with baseURL: %s", baseURL)

	interactionsClient := interactions.NewClient(baseURL)
	if interactionsClient.HTTPClient != nil {
		interactionsClient.HTTPClient.Timeout = 15 * time.Minute
	}

	ctx := context.Background()
	if apiKey := os.Getenv("GEMINI_API_KEY"); apiKey != "" {
		interactionsClient.WithAPIKey(apiKey)
	} else if apiKey := os.Getenv("GOOGLE_API_KEY"); apiKey != "" {
		interactionsClient.WithAPIKey(apiKey)
	} else {
		creds, err := google.FindDefaultCredentials(ctx, "https://www.googleapis.com/auth/cloud-platform")
		if err == nil {
			if token, err := creds.TokenSource.Token(); err == nil {
				interactionsClient.WithBearerToken(token.AccessToken)
			}
		} else {
			log.Printf("Warning: Could not find default credentials for bearer token: %v", err)
		}
	}

	s := server.NewMCPServer("Omni", version, server.WithResourceCapabilities(true, false))

	tool := mcp.NewTool("omni_video_generation",
		mcp.WithDescription("Generates or edits videos using Google's Gemini Omni Interactions API. Supports Text-to-Video (t2v), Image-to-Video (i2v), Reference-to-Video (ref2v), and conversational video editing (edit)."),
		mcp.WithString("prompt", mcp.Required(), mcp.Description("The text prompt describing the video to generate or edit.")),
		mcp.WithString("model", mcp.DefaultString("gemini-omni-flash-preview"), mcp.Description("The specific Gemini Omni model version ID. Defaults to gemini-omni-flash-preview.")),
		mcp.WithString("mode", mcp.DefaultString("t2v"), mcp.Description("Generation mode: 't2v' (Text-to-Video), 'i2v' (Image-to-Video), 'ref2v' (Reference-to-Video), or 'edit' (Video Editing). Defaults to 't2v'.")),
		mcp.WithString("aspect_ratio", mcp.DefaultString("16:9"), mcp.Description("Aspect ratio of the generated video ('16:9' or '9:16'). Defaults to '16:9'.")),
		mcp.WithNumber("duration_seconds", mcp.DefaultNumber(10), mcp.Description("Duration of the video in seconds. Defaults to 10.")),
		mcp.WithArray("images", mcp.Description("Optional list of image file paths or GCS URIs for starting frames (i2v), reference character consistency (ref2v), or style reference (edit)."), mcp.Items(map[string]any{"type": "string"})),
		mcp.WithArray("videos", mcp.Description("Optional list of video file paths or GCS URIs to edit (for 'edit' mode)."), mcp.Items(map[string]any{"type": "string"})),
		mcp.WithString("previous_interaction_id", mcp.Description("Optional ID of a previous interaction turn for multi-turn conversational video editing.")),
		mcp.WithString("output_directory", mcp.Description("Optional local directory path to download and save the generated video MP4 file.")),
		mcp.WithString("gcs_bucket_uri", mcp.Description("Optional GCS URI prefix to store the generated video MP4 file.")),
	)

	s.AddTool(tool, func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return omniVideoGenerationHandler(interactionsClient, ctx, request)
	})

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
		log.Fatalf("Invalid transport type: %s. Supported types are stdio, sse, and http.", transport)
	}
}
