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
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io" // Required for GCS download
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"cloud.google.com/go/storage" // Added for GCS download
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"google.golang.org/genai"
)

var (
	project, location string
	genAIClient       *genai.Client // Global GenAI client
	transport         string
)

const version = "1.3.4" // Version increment for optional local download

// inferMimeTypeFromURI attempts to guess the MIME type from the file extension.
// Only "image/png" and "image/jpeg" are supported by the API.
func inferMimeTypeFromURI(uri string) string {
	ext := strings.ToLower(filepath.Ext(uri))
	switch ext {
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	default:
		return ""
	}
}

// parseGCSPath splits a GCS URI (gs://bucket/object/path) into bucket and object path.
func parseGCSPath(gcsURI string) (bucketName string, objectName string, err error) {
	if !strings.HasPrefix(gcsURI, "gs://") {
		return "", "", fmt.Errorf("invalid GCS URI: must start with gs://")
	}
	trimmedURI := strings.TrimPrefix(gcsURI, "gs://")
	parts := strings.SplitN(trimmedURI, "/", 2)
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf("invalid GCS URI format: %s. Expected gs://bucket/object", gcsURI)
	}
	return parts[0], parts[1], nil
}

// downloadFromGCS downloads an object from GCS to a local file.
// The parentCtx is the context from the handler, used for creating the storage client.
// A new derived context with timeout is used for the actual download operation.
func downloadFromGCS(parentCtx context.Context, gcsURI string, localDestPath string) error {
	bucketName, objectName, err := parseGCSPath(gcsURI)
	if err != nil {
		return fmt.Errorf("parseGCSPath for %s: %w", gcsURI, err)
	}

	// Use parentCtx for creating the storage client.
	// If parentCtx is already canceled, NewClient might fail or operations might fail quickly.
	storageClient, err := storage.NewClient(parentCtx)
	if err != nil {
		return fmt.Errorf("storage.NewClient: %w", err)
	}
	defer storageClient.Close()

	// Create a new context with its own timeout for the GCS download operation.
	// This makes the download itself resilient if parentCtx has a very short deadline.
	gcsDownloadCtx, cancel := context.WithTimeout(context.Background(), 2*time.Minute) // 2-minute timeout for each download
	defer cancel()

	rc, err := storageClient.Bucket(bucketName).Object(objectName).NewReader(gcsDownloadCtx)
	if err != nil {
		return fmt.Errorf("Object(%q in bucket %q).NewReader: %w", objectName, bucketName, err)
	}
	defer rc.Close()

	// Ensure destination directory exists before creating the file
	destDir := filepath.Dir(localDestPath)
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return fmt.Errorf("os.MkdirAll for directory %s: %w", destDir, err)
	}

	f, err := os.Create(localDestPath)
	if err != nil {
		return fmt.Errorf("os.Create for %s: %w", localDestPath, err)
	}
	defer f.Close()

	if _, err := io.Copy(f, rc); err != nil {
		return fmt.Errorf("io.Copy to %s: %w", localDestPath, err)
	}

	log.Printf("Successfully downloaded GCS object %s to %s", gcsURI, localDestPath)
	return nil
}

func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio or sse)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio or sse)")
	flag.Parse()
}

func main() {
	project = os.Getenv("PROJECT_ID")
	if project == "" {
		log.Fatal("PROJECT_ID environment variable not set. Please set the env variable, e.g. export PROJECT_ID=$(gcloud config get project)")
	}
	location = os.Getenv("LOCATION")
	if location == "" {
		location = "us-central1"
		log.Printf("LOCATION environment variable not set, defaulting to %s", location)
	}

	log.Printf("Initializing global GenAI client...")
	var err error
	clientCtx, clientCancel := context.WithTimeout(context.Background(), 1*time.Minute)
	defer clientCancel()

	genAIClient, err = genai.NewClient(clientCtx, &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  project,
		Location: location,
	})
	if err != nil {
		log.Fatalf("Error creating global GenAI client: %v", err)
	}
	log.Printf("Global GenAI client initialized successfully.")

	s := server.NewMCPServer(
		"Google Cloud Veo",
		version,
	)

	commonVideoParams := []mcp.ToolOption{
		mcp.WithString("bucket",
			mcp.Required(),
			mcp.Description("Google Cloud Storage bucket where the API will save the generated video(s) (e.g., gs://your-bucket/output-folder)."),
		),
		mcp.WithString("output_directory", // New optional parameter
			mcp.Description("Optional. If provided, specifies a local directory to download the generated video(s) to. Filenames will be generated automatically."),
		),
		mcp.WithString("model",
			mcp.DefaultString("veo-2.0-generate-001"),
			mcp.Description("Model to use for video generation (e.g., veo-2.0-generate-001)."),
		),
		mcp.WithNumber("num_videos",
			mcp.DefaultNumber(1),
			mcp.Min(1),
			mcp.Max(4),
			mcp.Description("Number of videos to generate (1-4)."),
		),
		mcp.WithString("aspect_ratio",
			mcp.DefaultString("16:9"),
			mcp.Description("Aspect ratio of the generated videos (e.g., 16:9, 9:16, widescreen, portrait)."),
		),
		mcp.WithNumber("duration",
			mcp.DefaultNumber(5),
			mcp.Min(5),
			mcp.Max(8),
			mcp.Description("Duration of the generated video in seconds (integer values 5-8)."),
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

	if transport == "sse" {
		sseServer := server.NewSSEServer(s, server.WithBaseURL("http://localhost:8080"))
		log.Printf("SSE server listening on :8080 with t2v and i2v tools")
		if err := sseServer.Start(":8080"); err != nil {
			log.Fatalf("Server error: %v", err)
		}
		log.Println("Server has stopped.")
	} else {
		log.Printf("STDIO server listening with t2v and i2v tools")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("Server error: %v", err)
		}
	}
}

func parseCommonVideoParams(params map[string]interface{}) (gcsBucket, outputDir, model, finalAspectRatio string, numberOfVideos int32, durationSeconds *int32, err error) {
	model = "veo-2.0-generate-001"
	numberOfVideos = 1
	finalAspectRatio = "16:9"
	defaultDurationVal := int32(5)
	durationSeconds = &defaultDurationVal

	bucketVal, ok := params["bucket"].(string)
	if !ok || strings.TrimSpace(bucketVal) == "" {
		return "", "", "", "", 0, nil, errors.New("Google Cloud Storage bucket (parameter 'bucket') must be a non-empty string and is required")
	}
	gcsBucket = bucketVal // Assign to the correct return variable
	if !strings.HasPrefix(gcsBucket, "gs://") {
		gcsBucket = "gs://" + gcsBucket
		log.Printf("Bucket name did not start with 'gs://', prepended. New bucket name: %s", gcsBucket)
	}

	if dir, ok := params["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}

	if modelArg, ok := params["model"].(string); ok && modelArg != "" {
		model = modelArg
	} else {
		log.Printf("Model not provided or empty, using default: %s", model)
	}

	if numVideosArg, ok := params["num_videos"]; ok {
		if numVideosFloat, okFloat := numVideosArg.(float64); okFloat {
			numberOfVideos = int32(numVideosFloat)
		} else {
			log.Printf("Warning: num_videos was not a float64, received %T. Using default (%d).", numVideosArg, numberOfVideos)
		}
	}
	if numberOfVideos < 1 {
		log.Printf("num_videos was less than 1 (%d), clamping to 1.", numberOfVideos)
		numberOfVideos = 1
	}
	if numberOfVideos > 4 {
		log.Printf("num_videos was greater than 4 (%d), clamping to 4.", numberOfVideos)
		numberOfVideos = 4
	}

	aspectRatioInput := finalAspectRatio
	if aspectRatioArg, ok := params["aspect_ratio"].(string); ok && aspectRatioArg != "" {
		aspectRatioInput = aspectRatioArg
	} else {
		log.Printf("Aspect ratio not provided or empty, using default: %s", finalAspectRatio)
	}

	switch strings.ToLower(aspectRatioInput) {
	case "widescreen", "16:9":
		finalAspectRatio = "16:9"
	case "portrait", "9:16":
		finalAspectRatio = "9:16"
	default:
		log.Printf("Invalid aspect_ratio value '%s' received. Defaulting to '16:9'. Valid options are '16:9', '9:16', 'widescreen', or 'portrait'.", aspectRatioInput)
	}

	if durationArg, ok := params["duration"]; ok {
		if durationFloat, okFloat := durationArg.(float64); okFloat {
			parsedDuration := int32(durationFloat)
			if parsedDuration >= 5 && parsedDuration <= 8 {
				durationSeconds = &parsedDuration
			} else {
				log.Printf("Warning: duration '%.0f' is outside the accepted range (5-8 seconds). Using default (%d seconds).", durationFloat, *durationSeconds)
			}
		} else {
			log.Printf("Warning: duration was not a float64, received %T. Using default (%d seconds).", durationArg, *durationSeconds)
		}
	} else {
		log.Printf("Duration not provided, using default (%d seconds).", *durationSeconds)
	}
	return gcsBucket, outputDir, model, finalAspectRatio, numberOfVideos, durationSeconds, nil
}

func veoTextToVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	prompt, ok := request.GetArguments()["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("prompt must be a non-empty string and is required for text-to-video"), nil
	}

	gcsBucket, outputDir, model, finalAspectRatio, numberOfVideos, durationSecs, err := parseCommonVideoParams(request.GetArguments())
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

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
		log.Printf("Handling Veo t2v request: Prompt=\"%s\", GCSBucket=%s, OutputDir='%s', Model=%s, NumVideos=%d, AspectRatio=%s, Duration=%ds", prompt, gcsBucket, outputDir, model, numberOfVideos, finalAspectRatio, *durationSecs)
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:  numberOfVideos,
		AspectRatio:     finalAspectRatio,
		OutputGCSURI:    gcsBucket,
		DurationSeconds: durationSecs,
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, model, prompt, nil, config, "t2v")
}

func veoImageToVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
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

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, err := parseCommonVideoParams(request.GetArguments())
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

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
		log.Printf("Handling Veo i2v request: ImageURI=\"%s\", MimeType=\"%s\", Prompt=\"%s\", GCSBucket=%s, OutputDir='%s', Model=%s, NumVideos=%d, AspectRatio=%s, Duration=%ds", imageURI, mimeType, prompt, gcsBucket, outputDir, modelName, numberOfVideos, finalAspectRatio, *durationSecs)
	}

	inputImage := &genai.Image{
		GCSURI:   imageURI,
		MIMEType: mimeType,
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:  numberOfVideos,
		AspectRatio:     finalAspectRatio,
		OutputGCSURI:    gcsBucket,
		DurationSeconds: durationSecs,
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, prompt, inputImage, config, "i2v")
}

func callGenerateVideosAPI(
	client *genai.Client,
	parentCtx context.Context,
	mcpServer *server.MCPServer,
	progressToken mcp.ProgressToken,
	outputDir string, // New parameter
	modelName string,
	prompt string,
	image *genai.Image,
	config *genai.GenerateVideosConfig,
	callType string,
) (*mcp.CallToolResult, error) {

	attemptLocalDownload := outputDir != ""

	operationCtx, operationCancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer operationCancel()

	logMsg := fmt.Sprintf("Initiating GenerateVideos (%s) with Model: %s", callType, modelName)
	// ... (logging for image, prompt, duration, GCS output)
	if image != nil && image.GCSURI != "" {
		logMsg += fmt.Sprintf(", ImageGCSURI: %s, ImageMIMEType: %s", image.GCSURI, image.MIMEType)
	}
	if prompt != "" {
		logMsg += fmt.Sprintf(", Prompt: \"%s\"", prompt)
	}
	if config.DurationSeconds != nil {
		logMsg += fmt.Sprintf(", Duration: %ds", *config.DurationSeconds)
	}
	logMsg += fmt.Sprintf(", OutputGCS: %s. Operation timeout: %v", config.OutputGCSURI, 5*time.Minute)
	if attemptLocalDownload {
		logMsg += fmt.Sprintf(". Will attempt to download to local directory: '%s'", outputDir)
	}
	log.Print(logMsg)

	startTime := time.Now()

	operation, err := client.Models.GenerateVideos(operationCtx, modelName, prompt, image, config)
	if err != nil {
		// ... (error handling for initiation)
		if errors.Is(err, context.DeadlineExceeded) && operationCtx.Err() == context.DeadlineExceeded {
			log.Printf("GenerateVideos (%s) failed: initial call timed out: %v", callType, err)
			return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) initiation timed out", callType)), nil
		}
		log.Printf("Error initiating GenerateVideos (%s): %v", callType, err)
		return mcp.NewToolResultError(fmt.Sprintf("error starting video generation (%s): %v", callType, err)), nil
	}
	log.Printf("GenerateVideos operation (%s) initiated successfully. Operation Name: %s", callType, operation.Name)

	if progressToken != nil && mcpServer != nil {
		mcpServer.SendNotificationToClient(
			parentCtx,
			"notifications/progress",
			map[string]interface{}{
				"progressToken": progressToken,
				"message":       fmt.Sprintf("Video generation (%s) initiated. Polling for completion...", callType),
			},
		)
	}

	pollingStartTime := time.Now()
	pollingInterval := 15 * time.Second
	pollingAttempt := 0

	for !operation.Done {
		select {
		case <-operationCtx.Done():
			log.Printf("Polling loop for GenerateVideos (%s) canceled/timed out: %v", callType, operationCtx.Err())
			return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) timed out while waiting for completion", callType)), nil
		case <-time.After(pollingInterval):
			pollingAttempt++
			log.Printf("Polling GenerateVideos operation (%s): %s (Attempt: %d, Elapsed: %v)", callType, operation.Name, pollingAttempt, time.Since(pollingStartTime).Round(time.Second))

			var getOpOpts genai.GetOperationConfig
			updatedOp, err := client.Operations.GetVideosOperation(operationCtx, operation, &getOpOpts)
			if err != nil {
				// ... (polling error handling)
				log.Printf("Error polling GenerateVideos operation (%s) %s: %v", callType, operation.Name, err)
				if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
					return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) polling was canceled or timed out", callType)), nil
				}
				if progressToken != nil && mcpServer != nil {
					mcpServer.SendNotificationToClient(
						parentCtx,
						"notifications/progress",
						map[string]interface{}{
							"progressToken": progressToken,
							"message":       fmt.Sprintf("Polling attempt %d for %s video encountered an issue. Retrying...", pollingAttempt, callType),
							"status":        "polling_issue",
						},
					)
				}
				continue
			}
			operation = updatedOp

			if progressToken != nil && mcpServer != nil {
				// ... (progress notification logic)
				progressMessage := fmt.Sprintf("Video generation (%s) in progress. Polling attempt %d.", callType, pollingAttempt)
				progressPercent := -1

				if operation.Metadata != nil {
					if state, ok := operation.Metadata["state"].(string); ok {
						progressMessage = fmt.Sprintf("Video generation (%s) state: %s. Polling attempt %d.", callType, state, pollingAttempt)
					}
					if p, ok := operation.Metadata["progress_percent"].(float64); ok {
						progressPercent = int(p)
						progressMessage = fmt.Sprintf("Video generation (%s) is %d%% complete. Polling attempt %d.", callType, progressPercent, pollingAttempt)
					}
				}

				payload := map[string]interface{}{
					"progressToken": progressToken,
					"message":       progressMessage,
					"status":        "processing",
				}
				if progressPercent != -1 {
					payload["progress"] = progressPercent
					payload["total"] = 100
				}
				mcpServer.SendNotificationToClient(parentCtx, "notifications/progress", payload)
			}
		}
	}

	operationDuration := time.Since(startTime)
	log.Printf("GenerateVideos operation (%s) %s completed. Total duration: %v", callType, operation.Name, operationDuration.Round(time.Second))

	if progressToken != nil && mcpServer != nil {
		// ... (final progress notification logic)
		finalStatus := "completed_successfully"
		finalMessage := fmt.Sprintf("Video generation (%s) completed successfully in %v.", callType, operationDuration.Round(time.Second))
		if operation.Error != nil {
			finalStatus = "completed_with_error"
			finalMessage = fmt.Sprintf("Video generation (%s) failed after %v.", callType, operationDuration.Round(time.Second))
		}
		mcpServer.SendNotificationToClient(
			parentCtx,
			"notifications/progress",
			map[string]interface{}{
				"progressToken": progressToken,
				"message":       finalMessage,
				"status":        finalStatus,
			},
		)
	}

	if operation.Error != nil {
		// ... (operation error handling)
		var errMessage string
		var errCode int

		if msg, ok := operation.Error["message"].(string); ok {
			errMessage = msg
		}
		if code, ok := operation.Error["code"].(float64); ok {
			errCode = int(code)
		}

		if errMessage == "" {
			errorBytes, jsonErr := json.Marshal(operation.Error)
			if jsonErr != nil {
				errMessage = fmt.Sprintf("operation failed with unmarshalable error: %v", jsonErr)
			} else {
				errMessage = string(errorBytes)
			}
		}
		log.Printf("GenerateVideos operation (%s) %s failed with error: %s (Code: %d, FullError: %v)", callType, operation.Name, errMessage, errCode, operation.Error)
		return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) failed: %s", callType, errMessage)), nil
	}

	if operation.Response == nil || len(operation.Response.GeneratedVideos) == 0 {
		log.Printf("No videos generated (%s) by operation %s, despite completion.", callType, operation.Name)
		return mcp.NewToolResultText(fmt.Sprintf("Sorry, I couldn't generate any videos (%s) for your request (operation completed but no videos found).", callType)), nil
	}

	log.Printf("Successfully generated %d videos (%s) by operation %s.", len(operation.Response.GeneratedVideos), callType, operation.Name)

	var gcsVideoURIs []string
	var downloadedLocalFiles []string
	var downloadErrors []string // Store reasons for download/save failures

	for i, generatedVideo := range operation.Response.GeneratedVideos {
		videoGCSURI := ""
		// Veo API typically populates generatedVideo.Video.URI with the GCS path
		if generatedVideo.Video != nil && generatedVideo.Video.URI != "" {
			videoGCSURI = generatedVideo.Video.URI
		} else if generatedVideo.Video.URI != "" { // Fallback for other potential structures
			videoGCSURI = generatedVideo.Video.URI
		}

		if videoGCSURI == "" {
			log.Printf("Generated video %d (%s) (model: %s, operation: %s) had no retrievable GCS URI.", i, callType, modelName, operation.Name)
			continue
		}
		gcsVideoURIs = append(gcsVideoURIs, videoGCSURI)
		log.Printf("Video %d (%s) generated by operation %s is available at GCS URI: %s", i, callType, operation.Name, videoGCSURI)

		if attemptLocalDownload {
			// Generate a local filename
			// Extract original filename from GCS URI to use as a base or create a new one
			baseFilename := filepath.Base(videoGCSURI)
			if baseFilename == "." || baseFilename == "/" { // Handle edge cases from filepath.Base
				baseFilename = fmt.Sprintf("veo_video_%d.mp4", i) // Fallback filename
			}
			localFilepath := filepath.Join(outputDir, baseFilename)
			localFilepath = filepath.Clean(localFilepath)

			log.Printf("Attempting to download video %d from GCS URI %s to %s", i, videoGCSURI, localFilepath)
			downloadErr := downloadFromGCS(parentCtx, videoGCSURI, localFilepath) // Use parentCtx for GCS client creation
			if downloadErr != nil {
				errMsg := fmt.Sprintf("Error downloading video %d from %s to %s: %v", i, videoGCSURI, localFilepath, downloadErr)
				log.Print(errMsg)
				downloadErrors = append(downloadErrors, errMsg)
			} else {
				log.Printf("Successfully downloaded and saved video %d to %s", i, localFilepath)
				downloadedLocalFiles = append(downloadedLocalFiles, localFilepath)
			}
		}
	}

	var resultText string
	var saveMessageParts []string

	if len(gcsVideoURIs) > 0 {
		saveMessageParts = append(saveMessageParts, fmt.Sprintf("Videos saved to GCS: %s.", strings.Join(gcsVideoURIs, ", ")))
	}

	if attemptLocalDownload {
		saveMessageParts = append(saveMessageParts, fmt.Sprintf("Attempted to download videos to local directory '%s'.", outputDir))
		if len(downloadedLocalFiles) > 0 {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Successfully downloaded and saved locally: %s.", strings.Join(downloadedLocalFiles, ", ")))
		}
		if len(downloadErrors) > 0 {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Local download/save issues: %s.", strings.Join(downloadErrors, "; ")))
		}
	}

	if len(gcsVideoURIs) > 0 {
		resultText = fmt.Sprintf("Generated %d video(s) using model %s. This took about %s. %s",
			len(gcsVideoURIs),
			modelName,
			operationDuration.Round(time.Second),
			strings.Join(saveMessageParts, " "),
		)
	} else {
		resultText = fmt.Sprintf("Processed request (%s) for model %s (took %s), but no video URIs were found in the completed operation %s.",
			callType,
			modelName,
			operationDuration.Round(time.Second),
			operation.Name,
		)
	}
	return mcp.NewToolResultText(strings.TrimSpace(resultText)), nil
}
