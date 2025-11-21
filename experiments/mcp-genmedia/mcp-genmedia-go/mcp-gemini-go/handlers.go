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

// Package main implements an MCP server for Google's Gemini models.

package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/genai"
)

func geminiGenerateContentHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "gemini_generate_content")
	defer span.End()

	// --- Parameter Parsing ---
	prompt, ok := request.GetArguments()["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("prompt must be a non-empty string and is required"), nil
	}

	modelInput, _ := request.GetArguments()["model"].(string)
	if modelInput == "" {
		modelInput = "nano-banana-pro"
	}

	model, ok := common.ResolveGeminiModel(modelInput)
	if !ok {
		return mcp.NewToolResultError(fmt.Sprintf("Invalid model: %s. Supported models: %s", modelInput, common.BuildGeminiModelDescription())), nil
	}

	outputDir := ""
	if dir, ok := request.GetArguments()["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}

	// --- Construct Gemini Request ---
	var parts []*genai.Part
	parts = append(parts, genai.NewPartFromText(prompt))

	if imageArgs, ok := request.GetArguments()["images"].([]interface{}); ok {
		for _, imgArg := range imageArgs {
			if imgPath, ok := imgArg.(string); ok {
				if strings.HasPrefix(imgPath, "gs://") {
					parts = append(parts, genai.NewPartFromURI(imgPath, ""))
				} else {
					imgData, err := os.ReadFile(imgPath)
					if err != nil {
						return mcp.NewToolResultError(fmt.Sprintf("failed to read image file %s: %v", imgPath, err)), nil
					}
					parts = append(parts, genai.NewPartFromBytes(imgData, inferMimeType(imgPath)))
				}
			}
		}
	}

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("model", model),
		attribute.String("output_directory", outputDir),
	)

	// --- API Call ---
	log.Printf("Calling GenerateContent with Model: %s, Prompt: \"%s\"", model, prompt)
	startTime := time.Now()

	config := &genai.GenerateContentConfig{}
	config.ResponseModalities = []string{"IMAGE", "TEXT"}
	contents := &genai.Content{Parts: parts, Role: "USER"}

	resp, err := client.Models.GenerateContent(ctx, model, []*genai.Content{contents}, config)

	apiCallDuration := time.Since(startTime)
	log.Printf("GenerateContent call took: %v", apiCallDuration)
	span.SetAttributes(attribute.Float64("duration_ms", float64(apiCallDuration.Milliseconds())))

	if err != nil {
		span.RecordError(err)
		return mcp.NewToolResultError(fmt.Sprintf("error calling Gemini API: %v", err)), nil
	}

	// --- Process Response ---
	var responseText strings.Builder
	var savedFiles []string
	gentime := time.Now().Format("20060102150405")

	for _, candidate := range resp.Candidates {
		for n, part := range candidate.Content.Parts {
			if part.Text != "" {
				responseText.WriteString(part.Text)
			}
			if part.InlineData != nil {
				log.Printf("part %d mime-type: %s", n, part.InlineData.MIMEType)

				if outputDir != "" {
					if err := os.MkdirAll(outputDir, 0755); err != nil {
						return mcp.NewToolResultError(fmt.Sprintf("failed to create output directory: %v", err)), nil
					}
					fileName := fmt.Sprintf("gemini_%s_%d.png", gentime, n)
					filePath := filepath.Join(outputDir, fileName)
					if err := os.WriteFile(filePath, part.InlineData.Data, 0644); err != nil {
						return mcp.NewToolResultError(fmt.Sprintf("failed to write image file: %v", err)), nil
					}
					savedFiles = append(savedFiles, filePath)
				} else {
					// If no output dir, should we return base64? For now, we just log.
					log.Println("Received image data but no output_directory was specified. Image not saved.")
				}
			}
		}
	}

	// --- Format Final Result ---
	finalMessage := responseText.String()
	if len(savedFiles) > 0 {
		finalMessage += fmt.Sprintf("\n\nGenerated and saved %d image(s): %s", len(savedFiles), strings.Join(savedFiles, ", "))
	}

	return &mcp.CallToolResult{Content: []mcp.Content{mcp.TextContent{Type: "text", Text: strings.TrimSpace(finalMessage)}}}, nil
}

func inferMimeType(path string) string {
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".png":
		return "image/png"
	case ".gif":
		return "image/gif"
	case ".webp":
		return "image/webp"
	default:
		// Defaulting to a common image type if extension is unknown, as the API might handle it.
		// A more robust solution might involve reading file headers.
		return "image/png"
	}
}
