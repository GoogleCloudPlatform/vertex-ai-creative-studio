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

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// omniVideoGenerationHandler generates video via the shared common.GenerateOmniVideo
// entry point and persists the returned MP4 bytes locally and/or to GCS (with a
// best-effort V4 signed URL), reusing the suite's proven output conventions.
func omniVideoGenerationHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "omni_video_generation")
	defer span.End()

	// --- Parameter Parsing ---
	prompt, ok := request.GetArguments()["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("prompt must be a non-empty string and is required"), nil
	}
	prompt = strings.TrimSpace(prompt)

	outputDir := ""
	if dir, ok := request.GetArguments()["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}

	// gcsBucketURI: explicit "gcs_bucket_uri" takes precedence, otherwise fall
	// back to the server-wide GENMEDIA_BUCKET default (mirrors the other tools).
	gcsBucketURI := ""
	if u, ok := request.GetArguments()["gcs_bucket_uri"].(string); ok && strings.TrimSpace(u) != "" {
		gcsBucketURI = strings.TrimSpace(u)
	} else if appConfig != nil && appConfig.GenmediaBucket != "" {
		gcsBucketURI = appConfig.GenmediaBucket + "/omni_outputs/"
	}

	model := common.DefaultOmniModel
	if resolved, found := common.ResolveOmniModel("", appConfig.AllowUnsafeModels); found {
		model = resolved.CanonicalName
	}

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("model", model),
		attribute.String("output_directory", outputDir),
		attribute.String("gcs_bucket_uri", gcsBucketURI),
	)

	// --- Shared Omni call ---
	log.Printf("Calling GenerateOmniVideo with Model: %s, Prompt: %q", model, prompt)
	startTime := time.Now()

	result, err := common.GenerateOmniVideo(ctx, appConfig, common.OmniParams{Prompt: prompt, Model: model})

	apiCallDuration := time.Since(startTime)
	log.Printf("GenerateOmniVideo call took: %v", apiCallDuration)
	span.SetAttributes(attribute.Float64("duration_ms", float64(apiCallDuration.Milliseconds())))

	if err != nil {
		span.RecordError(err)
		return mcp.NewToolResultError(fmt.Sprintf("error generating Omni video: %v", err)), nil
	}
	span.SetAttributes(attribute.Int("video_count", len(result.Videos)))

	// --- Process / persist output ---
	var responseText strings.Builder
	if result.SherlogLink != "" {
		fmt.Fprintf(&responseText, "Optional header capture: %s\n\n", result.SherlogLink)
	}
	if strings.TrimSpace(result.Text) != "" {
		responseText.WriteString(result.Text)
	}
	if result.ThoughtSteps > 0 {
		fmt.Fprintf(&responseText, "\n\n(model reasoning: %d step(s))", result.ThoughtSteps)
	}

	gentime := time.Now().Format("20060102150405")
	var savedFiles []string

	for n, videoBytes := range result.Videos {
		mimeType := "video/mp4"
		if n < len(result.VideoMimeTypes) && result.VideoMimeTypes[n] != "" {
			mimeType = result.VideoMimeTypes[n]
		}
		saved := false

		if outputDir != "" {
			if err := os.MkdirAll(outputDir, 0755); err != nil {
				return mcp.NewToolResultError(fmt.Sprintf("failed to create output directory: %v", err)), nil
			}
			fileName := fmt.Sprintf("omni_%s_%d.mp4", gentime, n)
			filePath := filepath.Join(outputDir, fileName)
			if err := os.WriteFile(filePath, videoBytes, 0644); err != nil {
				return mcp.NewToolResultError(fmt.Sprintf("failed to write video file: %v", err)), nil
			}
			savedFiles = append(savedFiles, filePath)
			saved = true
		}

		if gcsBucketURI != "" {
			bucketName, objectPrefix := parseGCSBucketAndPrefix(gcsBucketURI)
			objectName := fmt.Sprintf("%somni_%s_%d.mp4", objectPrefix, gentime, n)
			if err := common.UploadToGCS(ctx, bucketName, objectName, mimeType, videoBytes); err != nil {
				log.Printf("failed to upload video to gs://%s/%s: %v", bucketName, objectName, err)
				fmt.Fprintf(&responseText, "\n\n[Warning: failed to upload generated video to GCS: %v]", err)
			} else {
				gcsURI := fmt.Sprintf("gs://%s/%s", bucketName, objectName)
				savedFiles = append(savedFiles, gcsURI)
				saved = true

				// Best-effort V4 signed HTTPS URL so clients can fetch the video
				// without the bucket being public. Non-fatal on failure.
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
			log.Println("Received video data but no output_directory or gcs_bucket_uri was specified/valid. Video not saved.")
		}
	}

	finalMessage := responseText.String()
	if len(savedFiles) > 0 {
		finalMessage += fmt.Sprintf("\n\nGenerated and saved %d video(s): %s", len(savedFiles), strings.Join(savedFiles, ", "))
	} else {
		finalMessage += fmt.Sprintf("\n\nGenerated %d video(s) but none were saved (set output_directory or gcs_bucket_uri).", len(result.Videos))
	}

	return &mcp.CallToolResult{Content: []mcp.Content{mcp.TextContent{Type: "text", Text: strings.TrimSpace(finalMessage)}}}, nil
}

// signedURLExpiry returns the validity duration for generated V4 signed URLs.
// Controlled by OMNI_SIGNED_URL_EXPIRY_HOURS. Defaults to 24 hours. Values are
// clamped to 168 hours (the V4 maximum). Set to "0" to disable signed URLs.
func signedURLExpiry() time.Duration {
	const def = 24 * time.Hour
	v := strings.TrimSpace(os.Getenv("OMNI_SIGNED_URL_EXPIRY_HOURS"))
	if v == "" {
		return def
	}
	h, err := strconv.Atoi(v)
	if err != nil || h < 0 {
		log.Printf("invalid OMNI_SIGNED_URL_EXPIRY_HOURS=%q, using default of 24", v)
		return def
	}
	if h == 0 {
		return 0
	}
	if h > 168 {
		log.Printf("OMNI_SIGNED_URL_EXPIRY_HOURS=%d exceeds the V4 maximum of 168 (7 days); clamping to 168", h)
		h = 168
	}
	return time.Duration(h) * time.Hour
}

// generateSignedURL creates a V4 GET signed URL for a GCS object. The signing key
// is detected automatically from the ambient credentials.
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
// without a leading gs:// scheme) into a bucket name and an object name prefix
// that is guaranteed to be empty or end with a "/".
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
