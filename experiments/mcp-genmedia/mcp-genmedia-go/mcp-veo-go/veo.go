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

// Package main implements an MCP server for Google's Veo models.

package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/rs/cors"
	"google.golang.org/genai"
)

var (
	appConfig    *common.Config
	genAIClient  *genai.Client // Global GenAI client
	transport    string
	port         int
	otel_enabled bool
)

const (
	serviceName = "mcp-veo-go"
	version     = "1.13.0" // generate audio and Veo 3.1
)

// init handles command-line flags and initial logging setup.
func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
	flag.IntVar(&port, "p", 0, "Port for SSE/HTTP server (defaults to PORT env var or 8080/8081)")
	flag.IntVar(&port, "port", 0, "Port for SSE/HTTP server (defaults to PORT env var or 8080/8081)")
	flag.Parse()
}

// main is the entry point for the mcp-veo-go service.
// It initializes the configuration, OpenTelemetry, and the Google GenAI client.
// It then creates an MCP server, registers the 'veo_t2v' and 'veo_i2v' tools,
// and starts listening for requests on the configured transport.
func main() {
	var err error
	appConfig = common.LoadConfig()

	// Initialize OpenTelemetry
	tp, err := common.InitTracerProvider(serviceName, version)
	if err != nil {
		log.Fatalf("failed to initialize tracer provider: %v", err)
	}
	if tp != nil {
		defer func() {
			if err := tp.Shutdown(context.Background()); err != nil {
				log.Printf("Error shutting down tracer provider: %v", err)
			}
		}()
	}
	

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

	genAIClient, err = genai.NewClient(clientCtx, clientConfig)
	if err != nil {
		log.Fatalf("Error creating global GenAI client: %v", err)
	}
	log.Printf("Global GenAI client initialized successfully.")

	s := server.NewMCPServer(
		"Veo", // Standardized name
		version,
	)

	commonVideoParams := []mcp.ToolOption{
		mcp.WithString("bucket",
			mcp.Description("Google Cloud Storage bucket where the API will save the generated video(s) (e.g., your-bucket/output-folder or gs://your-bucket/output-folder). If not provided, GENMEDIA_BUCKET env var will be used. One of them is required."),
		),
		mcp.WithString("output_directory",
			mcp.Description("Optional. If provided, specifies a local directory to download the generated video(s) to. Filenames will be generated automatically."),
		),
		mcp.WithString("model",
			mcp.DefaultString("veo-2.0-generate-001"),
			mcp.Description(common.BuildVeoModelDescription()),
		),
		mcp.WithNumber("num_videos",
			mcp.DefaultNumber(1),
			mcp.Description("Number of videos to generate. Note: the maximum is model-dependent."),
		),
		mcp.WithString("aspect_ratio",
			mcp.DefaultString("16:9"),
			mcp.Description("Aspect ratio of the generated videos. Note: supported aspect ratios are model-dependent."),
		),
		mcp.WithNumber("duration",
			mcp.DefaultNumber(5),
			mcp.Description("Duration of the generated video in seconds. Note: the supported duration range is model-dependent."),
		),
		mcp.WithBoolean("generate_audio",
			mcp.DefaultBool(true),
			mcp.Description("Optional. Generate audio for the video. Only supported by Veo 3 models. Defaults to true."),
		),
	}

	var textToVideoToolParams []mcp.ToolOption
	textToVideoToolParams = append(textToVideoToolParams,
		mcp.WithDescription("Generate a video from a text prompt using Veo. Video is saved to GCS and optionally downloaded locally."),
		mcp.WithString("prompt",
			mcp.Required(),
			mcp.Description("Text prompt for video generation."),
		),
	)
	textToVideoToolParams = append(textToVideoToolParams, commonVideoParams...)

	textToVideoTool := mcp.NewTool("veo_t2v",
		textToVideoToolParams...,
	)
	s.AddTool(textToVideoTool, func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return veoTextToVideoHandler(genAIClient, ctx, request)
	})

	var imageToVideoToolParams []mcp.ToolOption
	imageToVideoToolParams = append(imageToVideoToolParams,
		mcp.WithDescription("Generate a video from an input image (and optional prompt) using Veo. Video is saved to GCS and optionally downloaded locally. Supported image MIME types: image/jpeg, image/png."),
		mcp.WithString("image_uri",
			mcp.Required(),
			mcp.Description("GCS URI of the input image for video generation (e.g., gs://your-bucket/input-image.png)."),
		),
		mcp.WithString("mime_type",
			mcp.Description("MIME type of the input image. Supported types are 'image/jpeg' and 'image/png'. If not provided, an attempt will be made to infer it from the image_uri extension."),
		),
		mcp.WithString("prompt",
			mcp.Description("Optional text prompt to guide video generation from the image."),
		),
	)
	imageToVideoToolParams = append(imageToVideoToolParams, commonVideoParams...)

	imageToVideoTool := mcp.NewTool("veo_i2v",
		imageToVideoToolParams...,
	)
	s.AddTool(imageToVideoTool, func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return veoImageToVideoHandler(genAIClient, ctx, request)
	})

	s.AddPrompt(mcp.NewPrompt("generate-video",
		mcp.WithPromptDescription("Generates a video from a text prompt."),
		mcp.WithArgument("prompt", mcp.ArgumentDescription("The text prompt to generate a video from."), mcp.RequiredArgument()),
		mcp.WithArgument("duration", mcp.ArgumentDescription("The duration of the video in seconds.")),
		mcp.WithArgument("aspect_ratio", mcp.ArgumentDescription("The aspect ratio of the generated video.")),
		mcp.WithArgument("model", mcp.ArgumentDescription("The model to use for generation.")),
	), func(ctx context.Context, request mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		prompt, ok := request.Params.Arguments["prompt"]
		if !ok || strings.TrimSpace(prompt) == "" {
			return mcp.NewGetPromptResult(
				"Missing Prompt",
				[]mcp.PromptMessage{
					mcp.NewPromptMessage(mcp.RoleAssistant, mcp.NewTextContent("What video would you like me to generate?")),
				},
			), nil
		}

		// Call the existing handler logic
		args := make(map[string]interface{}, len(request.Params.Arguments))
		for k, v := range request.Params.Arguments {
			args[k] = v
		}
		toolRequest := mcp.CallToolRequest{
			Params: mcp.CallToolParams{Arguments: args},
		}
		result, err := veoTextToVideoHandler(genAIClient, ctx, toolRequest)
		if err != nil {
			return nil, err
		}

		var responseText string
		for _, content := range result.Content {
			if textContent, ok := content.(mcp.TextContent); ok {
				responseText += textContent.Text + "\n"
			}
		}

		return mcp.NewGetPromptResult(
			"Video Generation Result",
			[]mcp.PromptMessage{
				mcp.NewPromptMessage(mcp.RoleAssistant, mcp.NewTextContent(strings.TrimSpace(responseText))),
			},
		), nil
	})

	switch transport {
	case "sse":
		ssePort := 8081 // Default SSE port
		if port != 0 {
			ssePort = port
		} else if p, err := strconv.Atoi(common.GetEnv("PORT", "")); err == nil {
			ssePort = p
		}
		log.Printf("Starting Veo MCP Server (Version: %s, Transport: sse, Port: %d)", version, ssePort)
		sseServer := server.NewSSEServer(s, server.WithBaseURL(fmt.Sprintf("http://localhost:%d", ssePort)))
		if err := sseServer.Start(fmt.Sprintf(":%d", ssePort)); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
	case "http":
		httpPort := 8080 // Default HTTP port
		if port != 0 {
			httpPort = port
		} else if p, err := strconv.Atoi(common.GetEnv("PORT", "")); err == nil {
			httpPort = p
		}
		log.Printf("Starting Veo MCP Server (Version: %s, Transport: http, Port: %d)", version, httpPort)
		mcpHTTPHandler := server.NewStreamableHTTPServer(s) // Base path /mcp
		c := cors.New(cors.Options{
			AllowedOrigins:   []string{"*"},
			AllowedMethods:   []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodDelete, http.MethodOptions, http.MethodHead},
			AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-MCP-Progress-Token"},
			ExposedHeaders:   []string{"Link"},
			AllowCredentials: true,
			MaxAge:           300,
		})
		handlerWithCORS := c.Handler(mcpHTTPHandler)
		listenAddr := fmt.Sprintf(":%d", httpPort)
		if err := http.ListenAndServe(listenAddr, handlerWithCORS); err != nil {
			log.Fatalf("HTTP Server error: %v", err)
		}
	case "stdio":
		log.Printf("Starting Veo MCP Server (Version: %s, Transport: stdio)", version)
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	default:
		log.Fatalf("Unsupported transport type: %s. Please use 'stdio', 'sse', or 'http'.", transport)
	}

	log.Println("Veo Server has stopped.")
}
