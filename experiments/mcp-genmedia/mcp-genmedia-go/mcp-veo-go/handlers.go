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
	"fmt"
	"log"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"google.golang.org/genai"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
)

// veoTextToVideoHandler is the handler for the 'veo_t2v' tool.
func veoTextToVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "veo_t2v")
	defer span.End()

	prompt, ok := request.GetArguments()["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("prompt must be a non-empty string and is required for text-to-video"), nil
	}

	gcsBucket, outputDir, model, finalAspectRatio, numberOfVideos, durationSecs, err := parseCommonVideoParams(request.GetArguments(), appConfig)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("gcs_bucket", gcsBucket),
		attribute.String("output_dir", outputDir),
		attribute.String("model", model),
		attribute.String("aspect_ratio", finalAspectRatio),
		attribute.Int("num_videos", int(numberOfVideos)),
		attribute.Int("duration_secs", int(durationSecs)),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming t2v context for prompt \"%s\" was already canceled: %v", prompt, ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo t2v request: Prompt=\"%s\", GCSBucket=%s, OutputDir='%s', Model=%s, NumVideos=%d, AspectRatio=%s, Duration=%ds", prompt, gcsBucket, outputDir, model, numberOfVideos, finalAspectRatio, durationSecs)
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:  numberOfVideos,
		AspectRatio:     finalAspectRatio,
		OutputGCSURI:    gcsBucket,
		DurationSeconds: &durationSecs,
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, model, prompt, nil, config, "t2v")
}

// veoImageToVideoHandler is the handler for the 'veo_i2v' tool.
func veoImageToVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "veo_i2v")
	defer span.End()

	imageURI, ok := request.GetArguments()["image_uri"].(string)
	if !ok || strings.TrimSpace(imageURI) == "" {
		return mcp.NewToolResultError("image_uri must be a non-empty string (GCS URI) and is required for image-to-video"), nil
	}
	if !strings.HasPrefix(imageURI, "gs://") {
		return mcp.NewToolResultError(fmt.Sprintf("invalid image_uri '%s'. Must be a GCS URI starting with 'gs://'", imageURI)), nil
	}

	var mimeType string
	if mt, ok := request.GetArguments()["mime_type"].(string); ok && strings.TrimSpace(mt) != "" {
		mimeType = strings.ToLower(strings.TrimSpace(mt))
		if mimeType != "image/jpeg" && mimeType != "image/png" {
			log.Printf("Unsupported MIME type provided: %s. Only 'image/jpeg' and 'image/png' are supported.", mimeType)
			return mcp.NewToolResultError(fmt.Sprintf("Unsupported MIME type '%s'. Please use 'image/jpeg' or 'image/png'.", mimeType)), nil
		}
		log.Printf("Using provided and validated MIME type: %s", mimeType)
	} else {
		mimeType = inferMimeTypeFromURI(imageURI)
		if mimeType == "" {
			log.Printf("Could not infer a supported MIME type (image/jpeg or image/png) from image_uri: %s. Please provide a 'mime_type' parameter.", imageURI)
			return mcp.NewToolResultError(fmt.Sprintf("MIME type for image '%s' could not be inferred or is not supported. Please specify 'mime_type' as 'image/jpeg' or 'image/png'.", imageURI)), nil
		}
		log.Printf("Inferred MIME type: %s for image_uri: %s", mimeType, imageURI)
	}

	prompt := ""
	if promptArg, ok := request.GetArguments()["prompt"].(string); ok {
		prompt = strings.TrimSpace(promptArg)
	}

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, err := parseCommonVideoParams(request.GetArguments(), appConfig)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	span.SetAttributes(
		attribute.String("image_uri", imageURI),
		attribute.String("mime_type", mimeType),
		attribute.String("prompt", prompt),
		attribute.String("gcs_bucket", gcsBucket),
		attribute.String("output_dir", outputDir),
		attribute.String("model", modelName),
		attribute.String("aspect_ratio", finalAspectRatio),
		attribute.Int("num_videos", int(numberOfVideos)),
		attribute.Int("duration_secs", int(durationSecs)),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming i2v context for image_uri \"%s\" was already canceled: %v", imageURI, ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo i2v request: ImageURI=\"%%s\", MimeType=\"%%s\", Prompt=\"%%s\", GCSBucket=%s, OutputDir='%s', Model=%s, NumVideos=%d, AspectRatio=%s, Duration=%ds", imageURI, mimeType, prompt, gcsBucket, outputDir, modelName, numberOfVideos, finalAspectRatio, durationSecs)
	}

	inputImage := &genai.Image{
		GCSURI:   imageURI,
		MIMEType: mimeType,
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:  numberOfVideos,
		AspectRatio:     finalAspectRatio,
		OutputGCSURI:    gcsBucket,
		DurationSeconds: &durationSecs,
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, prompt, inputImage, config, "i2v")
}