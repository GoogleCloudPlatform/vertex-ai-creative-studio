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

	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/genai"
)

// veoFirstLastToVideoHandler is the handler for the 'veo_first_last_to_video' tool.
func veoFirstLastToVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "veo_first_last_to_video")
	defer span.End()

	firstImageURI, ok := request.GetArguments()["first_image_uri"].(string)
	if !ok || strings.TrimSpace(firstImageURI) == "" || !strings.HasPrefix(firstImageURI, "gs://") {
		return mcp.NewToolResultError("first_image_uri must be a valid GCS URI starting with 'gs://'"), nil
	}

	lastImageURI, ok := request.GetArguments()["last_image_uri"].(string)
	if !ok || strings.TrimSpace(lastImageURI) == "" || !strings.HasPrefix(lastImageURI, "gs://") {
		return mcp.NewToolResultError("last_image_uri must be a valid GCS URI starting with 'gs://'"), nil
	}

	prompt := ""
	if promptArg, ok := request.GetArguments()["prompt"].(string); ok {
		prompt = strings.TrimSpace(promptArg)
	}

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, personGeneration, err := parseCommonVideoParams(request.GetArguments(), appConfig, false)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	modelDetails := common.SupportedVeoModels[modelName]
	if !modelDetails.SupportsFirstLast {
		return mcp.NewToolResultError(fmt.Sprintf("Model %s does not support first-last video generation.", modelName)), nil
	}

	firstMimeType := ""
	if mt, ok := request.GetArguments()["first_mime_type"].(string); ok && strings.TrimSpace(mt) != "" {
		firstMimeType = strings.ToLower(strings.TrimSpace(mt))
		if firstMimeType != "image/jpeg" && firstMimeType != "image/png" {
			return mcp.NewToolResultError(fmt.Sprintf("Unsupported first_mime_type '%s'. Please use 'image/jpeg' or 'image/png'.", firstMimeType)), nil
		}
	} else {
		firstMimeType = inferMimeTypeFromURI(firstImageURI)
		if firstMimeType == "" {
			return mcp.NewToolResultError(fmt.Sprintf("MIME type for first image '%s' could not be inferred. Please specify 'first_mime_type' as 'image/jpeg' or 'image/png'.", firstImageURI)), nil
		}
	}

	lastMimeType := ""
	if mt, ok := request.GetArguments()["last_mime_type"].(string); ok && strings.TrimSpace(mt) != "" {
		lastMimeType = strings.ToLower(strings.TrimSpace(mt))
		if lastMimeType != "image/jpeg" && lastMimeType != "image/png" {
			return mcp.NewToolResultError(fmt.Sprintf("Unsupported last_mime_type '%s'. Please use 'image/jpeg' or 'image/png'.", lastMimeType)), nil
		}
	} else {
		lastMimeType = inferMimeTypeFromURI(lastImageURI)
		if lastMimeType == "" {
			return mcp.NewToolResultError(fmt.Sprintf("MIME type for last image '%s' could not be inferred. Please specify 'last_mime_type' as 'image/jpeg' or 'image/png'.", lastImageURI)), nil
		}
	}

	span.SetAttributes(
		attribute.String("first_image_uri", firstImageURI),
		attribute.String("last_image_uri", lastImageURI),
		attribute.String("prompt", prompt),
		attribute.String("model", modelName),
		attribute.String("person_generation", personGeneration),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming first_last_to_video context was already canceled: %v", ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo first_last_to_video request: FirstImageURI=\"%s\", LastImageURI=\"%s\", Prompt=\"%s\", Model=%s, PersonGen=%s", firstImageURI, lastImageURI, prompt, modelName, personGeneration)
	}

	inputImage := &genai.Image{
		GCSURI:   firstImageURI,
		MIMEType: firstMimeType,
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:   numberOfVideos,
		AspectRatio:      finalAspectRatio,
		OutputGCSURI:     gcsBucket,
		DurationSeconds:  &durationSecs,
		PersonGeneration: personGeneration,
		LastFrame: &genai.Image{
			GCSURI:   lastImageURI,
			MIMEType: lastMimeType,
		},
	}

	if generateAudio {
		config.GenerateAudio = &generateAudio
	}

	source := &genai.GenerateVideosSource{
		Prompt: prompt,
		Image:  inputImage,
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, source, config, "first_last_to_video")
}

// veoReferenceToVideoHandler is the handler for the 'veo_reference_to_video' tool.
func veoReferenceToVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "veo_reference_to_video")
	defer span.End()

	prompt, ok := request.GetArguments()["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("prompt must be a non-empty string and is required for reference-to-video"), nil
	}

	referenceImageURIsRaw, ok := request.GetArguments()["reference_image_uris"].([]interface{})
	if !ok || len(referenceImageURIsRaw) == 0 {
		return mcp.NewToolResultError("reference_image_uris must be a non-empty array of strings (GCS URIs)"), nil
	}

	if len(referenceImageURIsRaw) > 3 {
		return mcp.NewToolResultError("A maximum of 3 reference images are supported"), nil
	}

	var referenceMimeTypes []string
	if mimeTypesRaw, ok := request.GetArguments()["reference_mime_types"].([]interface{}); ok {
		if len(mimeTypesRaw) != len(referenceImageURIsRaw) {
			return mcp.NewToolResultError(fmt.Sprintf("If reference_mime_types is provided, its length (%d) must match reference_image_uris length (%d)", len(mimeTypesRaw), len(referenceImageURIsRaw))), nil
		}
		for _, mtRaw := range mimeTypesRaw {
			if mt, ok := mtRaw.(string); ok {
				referenceMimeTypes = append(referenceMimeTypes, strings.ToLower(strings.TrimSpace(mt)))
			} else {
				return mcp.NewToolResultError("All elements in reference_mime_types must be strings"), nil
			}
		}
	}

	var referenceImages []*genai.VideoGenerationReferenceImage
	for i, rawURI := range referenceImageURIsRaw {
		uriStr, ok := rawURI.(string)
		if !ok || !strings.HasPrefix(uriStr, "gs://") {
			return mcp.NewToolResultError(fmt.Sprintf("Invalid reference image URI: %v. Must be a GCS URI starting with 'gs://'", rawURI)), nil
		}

		mimeType := ""
		if len(referenceMimeTypes) > i {
			mimeType = referenceMimeTypes[i]
		}

		if mimeType == "" {
			mimeType = inferMimeTypeFromURI(uriStr)
			if mimeType == "" {
				return mcp.NewToolResultError(fmt.Sprintf("MIME type for reference image '%s' could not be inferred. Please provide 'reference_mime_types' array.", uriStr)), nil
			}
		}

		if mimeType != "image/jpeg" && mimeType != "image/png" {
			return mcp.NewToolResultError(fmt.Sprintf("Unsupported MIME type '%s' for reference image '%s'. Please use 'image/jpeg' or 'image/png'.", mimeType, uriStr)), nil
		}

		referenceImages = append(referenceImages, &genai.VideoGenerationReferenceImage{
			Image: &genai.Image{
				GCSURI:   uriStr,
				MIMEType: mimeType,
			},
			ReferenceType: genai.VideoGenerationReferenceTypeAsset,
		})
	}

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, personGeneration, err := parseCommonVideoParams(request.GetArguments(), appConfig, false)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	modelDetails := common.SupportedVeoModels[modelName]
	if !modelDetails.SupportsReferenceImage {
		return mcp.NewToolResultError(fmt.Sprintf("Model %s does not support reference image to video generation.", modelName)), nil
	}

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("model", modelName),
		attribute.Int("num_reference_images", len(referenceImages)),
		attribute.String("person_generation", personGeneration),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming reference_to_video context was already canceled: %v", ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo reference_to_video request: Prompt=\"%s\", Model=%s, NumRefImages=%d, PersonGen=%s", prompt, modelName, len(referenceImages), personGeneration)
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:   numberOfVideos,
		AspectRatio:      finalAspectRatio,
		OutputGCSURI:     gcsBucket,
		DurationSeconds:  &durationSecs,
		ReferenceImages:  referenceImages,
		PersonGeneration: personGeneration,
	}

	if generateAudio {
		config.GenerateAudio = &generateAudio
	}

	source := &genai.GenerateVideosSource{
		Prompt: prompt,
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, source, config, "reference_to_video")
}

// veoExtendVideoHandler is the handler for the 'veo_extend_video' tool.
func veoExtendVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "veo_extend_video")
	defer span.End()

	videoURI, ok := request.GetArguments()["video_uri"].(string)
	if !ok || strings.TrimSpace(videoURI) == "" {
		return mcp.NewToolResultError("video_uri must be a non-empty string (GCS URI) and is required for extending videos"), nil
	}
	if !strings.HasPrefix(videoURI, "gs://") {
		return mcp.NewToolResultError(fmt.Sprintf("invalid video_uri '%s'. Must be a GCS URI starting with 'gs://'", videoURI)), nil
	}

	mimeType := "video/mp4" // Veo currently only supports MP4 for extension
	if mt, ok := request.GetArguments()["mime_type"].(string); ok && strings.TrimSpace(mt) != "" {
		mimeType = strings.ToLower(strings.TrimSpace(mt))
	}

	prompt := ""
	if promptArg, ok := request.GetArguments()["prompt"].(string); ok {
		prompt = strings.TrimSpace(promptArg)
	}

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, personGeneration, err := parseCommonVideoParams(request.GetArguments(), appConfig, true)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	modelDetails := common.SupportedVeoModels[modelName]
	if !modelDetails.SupportsExtend {
		return mcp.NewToolResultError(fmt.Sprintf("Model %s does not support video extension.", modelName)), nil
	}

	span.SetAttributes(
		attribute.String("video_uri", videoURI),
		attribute.String("mime_type", mimeType),
		attribute.String("prompt", prompt),
		attribute.String("gcs_bucket", gcsBucket),
		attribute.String("output_dir", outputDir),
		attribute.String("model", modelName),
		attribute.String("aspect_ratio", finalAspectRatio),
		attribute.Int("num_videos", int(numberOfVideos)),
		attribute.Int("duration_secs", int(durationSecs)),
		attribute.Bool("generate_audio", generateAudio),
		attribute.String("person_generation", personGeneration),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming extend context for video_uri \"%s\" was already canceled: %v", videoURI, ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo extend_video request: VideoURI=\"%s\", Prompt=\"%s\", Model=%s", videoURI, prompt, modelName)
	}

	inputVideo := &genai.Video{
		URI:   videoURI,
		MIMEType: mimeType,
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:   numberOfVideos,
		AspectRatio:      finalAspectRatio,
		OutputGCSURI:     gcsBucket,
		DurationSeconds:  &durationSecs,
		PersonGeneration: personGeneration,
	}

	if generateAudio {
		config.GenerateAudio = &generateAudio
	}

	source := &genai.GenerateVideosSource{
		Prompt: prompt,
		Video:  inputVideo,
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, source, config, "extend_video")
}
