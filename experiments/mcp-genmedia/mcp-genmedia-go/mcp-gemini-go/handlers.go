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
	"encoding/base64"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/genai"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
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

	aspectRatio := "1:1"
	if ar, ok := request.GetArguments()["aspect_ratio"].(string); ok && strings.TrimSpace(ar) != "" {
		aspectRatio = strings.TrimSpace(ar)
	}

	modelArg, _ := request.GetArguments()["model"].(string)
	model := "gemini-3.1-flash-image"
	if modelArg != "" {
		if resolvedInfo, found := common.ResolveGeminiImageModel(modelArg, appConfig.AllowUnsafeModels); found {
			model = resolvedInfo.CanonicalName
		} else {
			model = modelArg
		}
	}

	outputDir := ""
	if dir, ok := request.GetArguments()["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}

	gcsOutputURI := ""
	gcsBucketName := ""
	gcsObjectPrefix := ""
	if gcsURI, ok := request.GetArguments()["gcs_bucket_uri"].(string); ok && strings.TrimSpace(gcsURI) != "" {
		gcsOutputURI = common.EnsureGCSPathPrefix(strings.TrimSpace(gcsURI))
		var err error
		gcsBucketName, gcsObjectPrefix, err = common.ParseGCSPrefix(gcsOutputURI)
		if err != nil {
			return mcp.NewToolResultError(fmt.Sprintf("invalid gcs_bucket_uri: %v", err)), nil
		}
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
		attribute.String("gcs_bucket_uri", gcsOutputURI),
	)

	// --- API Call ---
	log.Printf("Calling GenerateContent with Model: %s, Prompt: \"%s\"", model, prompt)
	startTime := time.Now()

	config := &genai.GenerateContentConfig{
		ResponseModalities: []string{"IMAGE", "TEXT"},
		ImageConfig: &genai.ImageConfig{
			AspectRatio: aspectRatio,
		},
	}
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
	var gcsSavedURIs []string
	var responseImages []mcp.Content
	generatedImages := 0
	returnImageDataInResponse := outputDir == "" && gcsOutputURI == ""

	// Check for optional Sherlog header
	if resp.SDKHTTPResponse != nil && resp.SDKHTTPResponse.Headers != nil {
		if link := resp.SDKHTTPResponse.Headers.Get("x-goog-sherlog-link"); link != "" {
			fmt.Fprintf(&responseText, "Optional header capture: %s\n\n", link)
		}
	}
	gentime := time.Now().Format("20060102150405")

	for _, candidate := range resp.Candidates {
		for n, part := range candidate.Content.Parts {
			if part.Text != "" {
				responseText.WriteString(part.Text)
			}
			if part.InlineData != nil {
				generatedImages++
				mimeType := common.NormalizeImageMIMEType(part.InlineData.MIMEType)
				fileName := fmt.Sprintf("gemini_%s_%d%s", gentime, n, common.ImageExtensionForMIMEType(mimeType))
				log.Printf("part %d mime-type: %s", n, mimeType)

				if outputDir != "" {
					if err := os.MkdirAll(outputDir, 0755); err != nil {
						return mcp.NewToolResultError(fmt.Sprintf("failed to create output directory: %v", err)), nil
					}
					filePath := filepath.Join(outputDir, fileName)
					if err := os.WriteFile(filePath, part.InlineData.Data, 0644); err != nil {
						return mcp.NewToolResultError(fmt.Sprintf("failed to write image file: %v", err)), nil
					}
					savedFiles = append(savedFiles, filePath)
				}

				if gcsOutputURI != "" {
					objectName := common.JoinGCSObjectName(gcsObjectPrefix, fileName)
					if err := common.UploadToGCS(ctx, gcsBucketName, objectName, mimeType, part.InlineData.Data); err != nil {
						return mcp.NewToolResultError(fmt.Sprintf("failed to upload image to GCS: %v", err)), nil
					}
					gcsSavedURIs = append(gcsSavedURIs, common.BuildGCSURI(gcsBucketName, objectName))
				}

				if returnImageDataInResponse {
					responseImages = append(responseImages, mcp.ImageContent{
						Type:     "image",
						Data:     base64.StdEncoding.EncodeToString(part.InlineData.Data),
						MIMEType: mimeType,
					})
				}
			}
		}
	}

	// --- Format Final Result ---
	finalMessage := strings.TrimSpace(responseText.String())
	if finalMessage == "" && generatedImages > 0 {
		finalMessage = fmt.Sprintf("Generated %d image(s).", generatedImages)
	}
	if len(savedFiles) > 0 {
		finalMessage += fmt.Sprintf("\n\nGenerated and saved %d image(s): %s", len(savedFiles), strings.Join(savedFiles, ", "))
	}
	if len(gcsSavedURIs) > 0 {
		finalMessage += fmt.Sprintf("\n\nGenerated and uploaded %d image(s) to GCS: %s", len(gcsSavedURIs), strings.Join(gcsSavedURIs, ", "))
	}
	if returnImageDataInResponse && len(responseImages) > 0 {
		finalMessage += "\n\nImage(s) are included in this MCP response as base64 data."
	}

	contentItems := []mcp.Content{mcp.TextContent{Type: "text", Text: strings.TrimSpace(finalMessage)}}
	if returnImageDataInResponse {
		contentItems = append(contentItems, responseImages...)
	}

	return &mcp.CallToolResult{Content: contentItems}, nil
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
	case ".pdf":
		return "application/pdf"
	case ".mp4":
		return "video/mp4"
	case ".mov":
		return "video/quicktime"
	case ".webm":
		return "video/webm"
	case ".avi":
		return "video/x-msvideo"
	case ".mkv":
		return "video/x-matroska"
	default:
		// Defaulting to a common image type if extension is unknown, as the API might handle it.
		// A more robust solution might involve reading file headers.
		return "image/png"
	}
}
