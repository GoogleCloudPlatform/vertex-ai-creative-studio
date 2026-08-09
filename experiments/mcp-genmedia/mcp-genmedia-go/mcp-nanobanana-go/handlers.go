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
	"strconv"
	"strings"
	"time"

	"cloud.google.com/go/storage"
	"github.com/mark3labs/mcp-go/mcp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/genai"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

func nanobananaGenerateContentHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "nanobanana_generate_content")
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

	// gcsBucketURI: explicit "gcs_bucket_uri" argument takes precedence. If not
	// provided, fall back to the server-wide GENMEDIA_BUCKET default (mirrors
	// the fallback behavior documented for the other genmedia MCP tools).
	gcsBucketURI := ""
	if u, ok := request.GetArguments()["gcs_bucket_uri"].(string); ok && strings.TrimSpace(u) != "" {
		gcsBucketURI = strings.TrimSpace(u)
	} else if appConfig != nil && appConfig.GenmediaBucket != "" {
		gcsBucketURI = appConfig.GenmediaBucket + "/nanobanana_outputs/"
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
		attribute.String("gcs_bucket_uri", gcsBucketURI),
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
				log.Printf("part %d mime-type: %s", n, part.InlineData.MIMEType)
				saved := false

				if outputDir != "" {
					if err := os.MkdirAll(outputDir, 0755); err != nil {
						return mcp.NewToolResultError(fmt.Sprintf("failed to create output directory: %v", err)), nil
					}
					fileName := fmt.Sprintf("gemini_%s_%d%s", gentime, n, extForMimeType(part.InlineData.MIMEType))
					filePath := filepath.Join(outputDir, fileName)
					if err := os.WriteFile(filePath, part.InlineData.Data, 0644); err != nil {
						return mcp.NewToolResultError(fmt.Sprintf("failed to write image file: %v", err)), nil
					}
					savedFiles = append(savedFiles, filePath)
					saved = true
				}

				if gcsBucketURI != "" {
					bucketName, objectPrefix := parseGCSBucketAndPrefix(gcsBucketURI)
					objectName := fmt.Sprintf("%sgemini_%s_%d%s", objectPrefix, gentime, n, extForMimeType(part.InlineData.MIMEType))
					if err := common.UploadToGCS(ctx, bucketName, objectName, part.InlineData.MIMEType, part.InlineData.Data); err != nil {
						log.Printf("failed to upload image to gs://%s/%s: %v", bucketName, objectName, err)
						fmt.Fprintf(&responseText, "\n\n[Warning: failed to upload generated image to GCS: %v]", err)
					} else {
						gcsURI := fmt.Sprintf("gs://%s/%s", bucketName, objectName)
						savedFiles = append(savedFiles, gcsURI)
						saved = true

						// Best-effort: also return a V4 signed HTTPS URL so clients
						// (e.g. Claude) can fetch/display the image without the
						// bucket being public. Non-fatal on failure.
						if expiry := signedURLExpiry(); expiry > 0 {
							if signedURL, sErr := generateSignedURL(ctx, bucketName, objectName, expiry); sErr != nil {
								log.Printf("failed to generate signed URL for %s: %v", gcsURI, sErr)
							} else {
								fmt.Fprintf(&responseText, "\n\nSigned URL for %s (valid %s):\n%s", objectName, expiry, signedURL)
							}
						}
					}
				}

				if !saved {
					log.Println("Received image data but no output_directory or gcs_bucket_uri was specified/valid. Image not saved.")
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

// signedURLExpiry returns the validity duration for generated V4 signed URLs.
// Controlled by the NANOBANANA_SIGNED_URL_EXPIRY_HOURS env var. Defaults to
// 24 hours. Values are clamped to 168 hours (7 days, the V4 maximum). Set to
// "0" to disable signed URL generation entirely.
func signedURLExpiry() time.Duration {
	const def = 24 * time.Hour
	v := strings.TrimSpace(os.Getenv("NANOBANANA_SIGNED_URL_EXPIRY_HOURS"))
	if v == "" {
		return def
	}
	h, err := strconv.Atoi(v)
	if err != nil || h < 0 {
		log.Printf("invalid NANOBANANA_SIGNED_URL_EXPIRY_HOURS=%q, using default of 24", v)
		return def
	}
	if h == 0 {
		return 0
	}
	if h > 168 {
		log.Printf("NANOBANANA_SIGNED_URL_EXPIRY_HOURS=%d exceeds the V4 maximum of 168 (7 days); clamping to 168", h)
		h = 168
	}
	return time.Duration(h) * time.Hour
}

// generateSignedURL creates a V4 GET signed URL for a GCS object. The signing
// key is detected automatically from the ambient credentials (e.g. the
// service-account JSON key referenced by GOOGLE_APPLICATION_CREDENTIALS).
func generateSignedURL(ctx context.Context, bucketName, objectName string, expiry time.Duration) (string, error) {
	client, err := storage.NewClient(ctx)
	if err != nil {
		return "", fmt.Errorf("storage.NewClient: %w", err)
	}
	defer func() { _ = client.Close() }()

	return client.Bucket(bucketName).SignedURL(objectName, &storage.SignedURLOptions{
		Scheme:  storage.SigningSchemeV4,
		Method:  "GET",
		Expires: time.Now().Add(expiry),
	})
}

// parseGCSBucketAndPrefix splits a "bucket/optional/prefix/" string (with or
// without a leading gs:// scheme) into a bucket name and an object name
// prefix that is guaranteed to be empty or end with a "/".
func parseGCSBucketAndPrefix(uri string) (bucket, prefix string) {
	uri = strings.TrimPrefix(uri, "gs://")
	uri = strings.TrimPrefix(uri, "/")
	parts := strings.SplitN(uri, "/", 2)
	bucket = parts[0]
	if len(parts) > 1 && parts[1] != "" {
		prefix = parts[1]
		if !strings.HasSuffix(prefix, "/") {
			prefix += "/"
		}
	}
	return bucket, prefix
}

// extForMimeType returns a reasonable file extension for a given image MIME type.
func extForMimeType(mimeType string) string {
	switch mimeType {
	case "image/jpeg":
		return ".jpg"
	case "image/webp":
		return ".webp"
	case "image/gif":
		return ".gif"
	case "image/png":
		return ".png"
	default:
		return ".png"
	}
}
