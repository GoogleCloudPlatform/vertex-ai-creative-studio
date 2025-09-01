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
	"flag"
	"log"
	"os"
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
)

const (
	serviceName = "mcp-gemini-go"
	version     = "0.2.0"
)

func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
	flag.Parse()
}

func main() {
	appConfig = common.LoadConfig()

	// Override default location for Gemini models if not explicitly set
	if os.Getenv("LOCATION") == "" {
		log.Printf("LOCATION environment variable not set. Defaulting to 'global' for mcp-gemini-go.")
		appConfig.Location = "global"
	}

	tp, err := common.InitTracerProvider(serviceName, version)
	if err != nil {
		log.Fatalf("failed to initialize tracer provider: %v", err)
	}
	defer func() {
		if err := tp.Shutdown(context.Background()); err != nil {
			log.Printf("Error shutting down tracer provider: %v", err)
		}
	}()

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

	s := server.NewMCPServer("Gemini", version)

	tool := mcp.NewTool("gemini_image_generation",
		mcp.WithDescription("Generates content (text and/or images) based on a multimodal prompt using Gemini 2.5 Flash Image generation. This model is also called nano-banana."),
		mcp.WithString("prompt", mcp.Required(), mcp.Description("The text prompt for content generation.")),
		mcp.WithString("model", mcp.DefaultString("gemini-2.5-flash-image-preview"), mcp.Description("The specific Gemini model to use.")),
		mcp.WithArray("images", mcp.Description("Optional. A list of local file paths or GCS URIs for input images.")),
		mcp.WithString("output_directory", mcp.Description("Optional. Local directory to save generated image(s) to.")),
		mcp.WithString("gcs_bucket_uri", mcp.Description("Optional. GCS URI prefix to store generated images (e.g., your-bucket/outputs/).")),
	)

	handlerWithClient := func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return geminiGenerateContentHandler(genAIClient, ctx, request)
	}
	s.AddTool(tool, handlerWithClient)

	// --- Register Gemini TTS Tools ---
	listVoicesTool := mcp.NewTool("list_gemini_voices",
		mcp.WithDescription("Lists the available single-speaker voices for use with the Gemini-TTS models."),
	)
	s.AddTool(listVoicesTool, listGeminiVoicesHandler)

	ttsTool := mcp.NewTool("gemini_audio_tts",
		mcp.WithDescription("Synthesizes speech from text using Gemini models, allowing for granular control over style, pace, tone, and emotional expression through natural-language prompts."),
		mcp.WithString("text",
			mcp.Required(),
			mcp.Description("The text to synthesize (up to 800 characters)."),
		),
		mcp.WithString("prompt",
			mcp.Description("Stylistic instructions on how to synthesize the content. You can adapt delivery, adopt specific accents, and produce a range of tones and expressions."),
		),
		mcp.WithString("voice_name",
			mcp.DefaultString(defaultGeminiTTSVoice),
			mcp.Description("The voice to use. Use 'list_gemini_voices' to see available voices."),
			mcp.Enum(availableGeminiVoices...),
		),
		mcp.WithString("model_name",
			mcp.DefaultString(defaultGeminiTTSModel),
			mcp.Description("The model to use."),
			mcp.Enum("gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"),
		),
		mcp.WithString("output_filename_prefix",
			mcp.DefaultString("gemini_tts_audio"),
			mcp.Description("Optional. A prefix for the output WAV filename if saving locally. A timestamp and .wav extension will be appended."),
		),
		mcp.WithString("output_directory",
			mcp.Description("Optional. If provided, specifies a local directory to save the generated audio file to. If not provided, audio data is returned in the response."),
		),
	)
	s.AddTool(ttsTool, geminiAudioTTSHandler)
	// --- End of TTS Tools ---

	// --- Register Gemini Resources ---
	s.AddResource(mcp.NewResource(
		"gemini://language_codes",
		"Gemini TTS Language Codes",
		mcp.WithResourceDescription("A list of supported languages and their BCP-47 codes for Gemini TTS."),
		mcp.WithMIMEType("application/json"),
	), geminiLanguageCodesHandler)
	// --- End of Gemini Resources ---

	log.Printf("Starting %s MCP Server (Version: %s)", serviceName, version)
	if err := server.ServeStdio(s); err != nil {
		log.Fatalf("STDIO Server error: %v", err)
	}
}
