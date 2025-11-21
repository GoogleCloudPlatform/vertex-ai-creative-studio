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
	"encoding/json"
	"fmt"
	"log"
	"strings"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/genai"
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

	gcsBucket, outputDir, model, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, err := parseCommonVideoParams(request.GetArguments(), appConfig)
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
		attribute.Bool("generate_audio", generateAudio),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming t2v context for prompt %s was already canceled: %v", prompt, ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo t2v request: Prompt=\"%s\", GCSBucket=%s, OutputDir='%s', Model=%s, NumVideos=%d, AspectRatio=%s, Duration=%ds, GenerateAudio=%t", prompt, gcsBucket, outputDir, model, numberOfVideos, finalAspectRatio, durationSecs, generateAudio)
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:  numberOfVideos,
		AspectRatio:     finalAspectRatio,
		OutputGCSURI:    gcsBucket,
		DurationSeconds: &durationSecs,
	}

	if generateAudio {
		config.GenerateAudio = &generateAudio
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

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, err := parseCommonVideoParams(request.GetArguments(), appConfig)
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
		attribute.Bool("generate_audio", generateAudio),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming i2v context for image_uri %s was already canceled: %v", imageURI, ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo i2v request: ImageURI=\"%s\", MimeType=\"%s\", Prompt=\"%s\", GCSBucket=%s, OutputDir='%s', Model=%s, NumVideos=%d, AspectRatio=%s, Duration=%ds, GenerateAudio=%t", imageURI, mimeType, prompt, gcsBucket, outputDir, modelName, numberOfVideos, finalAspectRatio, durationSecs, generateAudio)
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

	if generateAudio {
		config.GenerateAudio = &generateAudio
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, prompt, inputImage, config, "i2v")
}

// veoInterpolationHandler is the handler for the 'veo_interpolate' tool.
func veoInterpolationHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "veo_interpolate")
	defer span.End()

	// Get first frame
	firstFrameURI, ok := request.GetArguments()["first_frame_uri"].(string)
	if !ok || strings.TrimSpace(firstFrameURI) == "" {
		return mcp.NewToolResultError("first_frame_uri must be a non-empty GCS URI"), nil
	}
	if !strings.HasPrefix(firstFrameURI, "gs://") {
		return mcp.NewToolResultError(fmt.Sprintf("invalid first_frame_uri '%s'. Must be a GCS URI starting with 'gs://'", firstFrameURI)), nil
	}
	firstFrameMimeType := inferMimeTypeFromURI(firstFrameURI)
	if mt, ok := request.GetArguments()["first_frame_mime_type"].(string); ok && strings.TrimSpace(mt) != "" {
		firstFrameMimeType = strings.ToLower(strings.TrimSpace(mt))
	}
	if firstFrameMimeType == "" {
		return mcp.NewToolResultError(fmt.Sprintf("MIME type for first_frame_uri '%s' could not be inferred. Please specify 'first_frame_mime_type'.", firstFrameURI)), nil
	}

	// Get last frame
	lastFrameURI, ok := request.GetArguments()["last_frame_uri"].(string)
	if !ok || strings.TrimSpace(lastFrameURI) == "" {
		return mcp.NewToolResultError("last_frame_uri must be a non-empty GCS URI"), nil
	}
	if !strings.HasPrefix(lastFrameURI, "gs://") {
		return mcp.NewToolResultError(fmt.Sprintf("invalid last_frame_uri '%s'. Must be a GCS URI starting with 'gs://'", lastFrameURI)), nil
	}
	lastFrameMimeType := inferMimeTypeFromURI(lastFrameURI)
	if mt, ok := request.GetArguments()["last_frame_mime_type"].(string); ok && strings.TrimSpace(mt) != "" {
		lastFrameMimeType = strings.ToLower(strings.TrimSpace(mt))
	}
	if lastFrameMimeType == "" {
		return mcp.NewToolResultError(fmt.Sprintf("MIME type for last_frame_uri '%s' could not be inferred. Please specify 'last_frame_mime_type'.", lastFrameURI)), nil
	}

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, err := parseCommonVideoParams(request.GetArguments(), appConfig)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	modelInfo, ok := common.SupportedVeoModels[modelName]
	if !ok {
		return mcp.NewToolResultError(fmt.Sprintf("Model '%s' is not a supported Veo model.", modelName)), nil
	}

	if !modelInfo.SupportsLastFrame {
		return mcp.NewToolResultError(fmt.Sprintf("Interpolation with a last frame is not supported on model '%s'.", modelName)), nil
	}

	// Get reference images and check for support
	var referenceImages []*genai.VideoGenerationReferenceImage
	if refImagesJSON, ok := request.GetArguments()["reference_images"].(string); ok && strings.TrimSpace(refImagesJSON) != "" {
		if !modelInfo.SupportsReferenceImages {
			return mcp.NewToolResultError(fmt.Sprintf("Providing reference images is not supported on model '%s'.", modelName)), nil
		}

		var refImageInputs []struct {
			URI  string `json:"uri"`
			Type string `json:"type"`
		}

		if err := json.Unmarshal([]byte(refImagesJSON), &refImageInputs); err != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Failed to parse 'reference_images' JSON: %v. Please provide a valid JSON array of objects, each with 'uri' and 'type'.", err)), nil
		}

		for _, input := range refImageInputs {
			trimmedURI := strings.TrimSpace(input.URI)
			if !strings.HasPrefix(trimmedURI, "gs://") {
				log.Printf("Skipping invalid reference image URI: %v", trimmedURI)
				continue
			}
			mimeType := inferMimeTypeFromURI(trimmedURI)
			if mimeType == "" {
				log.Printf("Skipping reference image with unknown MIME type: %s", trimmedURI)
				continue
			}

			var refType genai.VideoGenerationReferenceType
			switch strings.ToUpper(strings.TrimSpace(input.Type)) {
			case "ASSET":
				refType = genai.VideoGenerationReferenceTypeAsset
			case "STYLE":
				refType = genai.VideoGenerationReferenceTypeStyle
			default:
				log.Printf("Skipping reference image with invalid type '%s'. Must be 'ASSET' or 'STYLE'.", input.Type)
				continue
			}

			imageForRef := &genai.Image{GCSURI: trimmedURI, MIMEType: mimeType}
			referenceImages = append(referenceImages, &genai.VideoGenerationReferenceImage{Image: imageForRef, ReferenceType: refType})
		}
	}

	prompt := ""
	if promptArg, ok := request.GetArguments()["prompt"].(string); ok {
		prompt = strings.TrimSpace(promptArg)
	}

	span.SetAttributes(
		attribute.String("first_frame_uri", firstFrameURI),
		attribute.String("last_frame_uri", lastFrameURI),
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

	firstFrameImage := &genai.Image{
		GCSURI:   firstFrameURI,
		MIMEType: firstFrameMimeType,
	}

	lastFrameImage := &genai.Image{
		GCSURI:   lastFrameURI,
		MIMEType: lastFrameMimeType,
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:  numberOfVideos,
		AspectRatio:     finalAspectRatio,
		OutputGCSURI:    gcsBucket,
		DurationSeconds: &durationSecs,
		LastFrame:       lastFrameImage,
		ReferenceImages: referenceImages,
	}

	if generateAudio {
		config.GenerateAudio = &generateAudio
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, prompt, firstFrameImage, config, "interpolate")
}
