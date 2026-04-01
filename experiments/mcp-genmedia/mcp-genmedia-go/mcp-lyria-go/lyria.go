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

// Package main implements an MCP server for Google's Lyria models.

package main

import (
	"context"
	"encoding/base64"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	aiplatform "cloud.google.com/go/aiplatform/apiv1"
	"cloud.google.com/go/aiplatform/apiv1/aiplatformpb"
	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/rs/cors"
	"github.com/teris-io/shortid"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/api/option"
	"google.golang.org/protobuf/types/known/structpb"
)

var (
	// MCP Server settings
	transport string
	port      int

	// Google Cloud settings
	appConfig *common.Config

	predictionClient *aiplatform.PredictionClient // Global Prediction Client
)

const (
	serviceName         = "mcp-lyria-go"
	version     = "3.4.1" // Synchronize release version
	defaultPublisher    = "google"
	defaultLyriaModelID = "lyria-3-clip-preview"
	defaultSampleCount  = 1
	audioMIMEType       = "audio/wav" // Define MIME type for audio
)

// init handles command-line flags and initial logging setup.
func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
	flag.IntVar(&port, "p", 0, "Port for SSE/HTTP server (defaults to PORT env var or 8080/8081)")
	flag.IntVar(&port, "port", 0, "Port for SSE/HTTP server (defaults to PORT env var or 8080/8081)")
}

// main is the entry point for the mcp-lyria-go service.
// It initializes the configuration, OpenTelemetry, and the AI Platform Prediction client.
// It then creates an MCP server, registers the 'lyria_generate_music' tool, and starts
// listening for requests on the configured transport.
func main() {
	flag.Parse()

	// Initialize OpenTelemetry
	var cleanup func()
	appConfig, cleanup = common.Init(serviceName, version)
	defer cleanup()
	var err error

	log.Println("Initializing global AI Platform Prediction client...")
	regionalEndpoint := fmt.Sprintf("%s-aiplatform.googleapis.com:443", appConfig.Location)
	predictionClient, err = aiplatform.NewPredictionClient(context.Background(), option.WithEndpoint(regionalEndpoint))
	if err != nil {
		log.Printf("Warning: Failed to create global AI Platform Prediction client: %v. Deferring to runtime.", err)
	}
	defer func() {
		if predictionClient != nil {
			log.Println("Closing global AI Platform Prediction client.")
			if err := predictionClient.Close(); err != nil {
				log.Printf("Error closing global AI Platform Prediction client: %v", err)
			}
		}
	}()
	log.Println("Global AI Platform Prediction client initialized successfully.")

	s := server.NewMCPServer(
		"Lyria", // Standardized name
		version,
	)

	lyriaToolParams := []mcp.ToolOption{
		mcp.WithDescription("Generates music from a text prompt using Lyria. Optionally saves to GCS and/or a local directory. Audio data is returned directly ONLY if neither GCS nor local path is specified."),
		mcp.WithString("prompt",
			mcp.Required(),
			mcp.Description("Text prompt for music generation."),
		),
		mcp.WithString("negative_prompt",
			mcp.Description("Optional. A negative prompt to instruct the model to avoid certain characteristics."),
		),
		mcp.WithNumber("seed",
			mcp.Description("Optional. Random seed (uint32) for music generation for reproducibility."),
		),
		mcp.WithNumber("sample_count",
			mcp.DefaultNumber(float64(defaultSampleCount)),
			mcp.Min(1),
			mcp.Description("Optional. Number of music samples (uint32) to generate. Currently, only the first sample is processed and returned."),
		),
		mcp.WithString("output_gcs_bucket",
			mcp.Description("Optional. Google Cloud Storage bucket name. If provided, audio is saved to GCS and direct audio data is NOT returned."),
		),
		mcp.WithString("file_name",
			mcp.Description("Optional. Desired file name (e.g., 'my_song.wav'). Used for GCS object and local file. If omitted, a unique name is generated."),
		),
		mcp.WithString("local_path",
			mcp.Description("Optional. Local directory path. If provided, audio is saved locally and direct audio data is NOT returned (unless GCS is also not specified)."),
		),
		mcp.WithString("model_id",
			mcp.DefaultString(defaultLyriaModelID),
			mcp.Description(common.BuildLyriaModelDescription()),
		),
	}

	lyriaTool := mcp.NewTool("lyria_generate_music", lyriaToolParams...)
	s.AddTool(lyriaTool, lyriaGenerateMusicHandler)

	s.AddPrompt(mcp.NewPrompt("generate-music",
		mcp.WithPromptDescription("Generates music from a text prompt."),
		mcp.WithArgument("prompt", mcp.ArgumentDescription("The text prompt to generate music from."), mcp.RequiredArgument()),
		mcp.WithArgument("negative_prompt", mcp.ArgumentDescription("A negative prompt to instruct the model to avoid certain characteristics.")),
	), func(ctx context.Context, request mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		prompt, ok := request.Params.Arguments["prompt"]
		if !ok || strings.TrimSpace(prompt) == "" {
			return mcp.NewGetPromptResult(
				"Missing Prompt",
				[]mcp.PromptMessage{
					mcp.NewPromptMessage(mcp.RoleAssistant, mcp.NewTextContent("What kind of music should I create for you?")),
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
		result, err := lyriaGenerateMusicHandler(ctx, toolRequest)
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
			"Music Generation Result",
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
		log.Printf("Starting Lyria MCP Server (Version: %s, Transport: sse, Port: %d)", version, ssePort)
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
		log.Printf("Starting Lyria MCP Server (Version: %s, Transport: http, Port: %d)", version, httpPort)
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
		log.Printf("Starting Lyria MCP Server (Version: %s, Transport: stdio)", version)
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	default:
		log.Fatalf("Unsupported transport type: %s. Please use 'stdio', 'sse', or 'http'.", transport)
	}

	log.Println("Lyria Server has stopped.")
}

// lyriaGenerateMusicHandler is the handler for the 'lyria_generate_music' tool.
// It parses the request parameters, calls the Lyria model to generate music,
// and then handles the response. It can save the generated audio to GCS, a local directory,
// or return it as base64-encoded data in the response.
func lyriaGenerateMusicHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "lyria_generate_music")
	defer span.End()

	startTime := time.Now()
	params := request.GetArguments()

	prompt, ok := params["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("Parameter 'prompt' must be a non-empty string and is required."), nil
	}

	gcsBucketParam := ""
	userProvidedBucket, _ := params["output_gcs_bucket"].(string)
	userProvidedBucket = strings.TrimSpace(userProvidedBucket)

	if userProvidedBucket != "" {
		gcsBucketParam = userProvidedBucket
	} else if appConfig.GenmediaBucket != "" {
		gcsBucketParam = appConfig.GenmediaBucket
		log.Printf("Handler lyria_generate_music: 'output_gcs_bucket' parameter not provided, using default from GENMEDIA_BUCKET: %s", gcsBucketParam)
	}

	if gcsBucketParam != "" { // Only trim prefix if bucket is actually set
		gcsBucketParam = strings.TrimPrefix(gcsBucketParam, "gs://")
	}

	fileNameParam := ""
	if val, ok := params["file_name"].(string); ok && strings.TrimSpace(val) != "" {
		fileNameParam = strings.TrimSpace(val)
	}

	localDirectoryPathParameter := ""
	if val, ok := params["local_path"].(string); ok && strings.TrimSpace(val) != "" {
		localDirectoryPathParameter = strings.TrimSpace(val)
	}

	modelInput := defaultLyriaModelID
	if val, ok := params["model_id"].(string); ok && strings.TrimSpace(val) != "" {
		modelInput = strings.TrimSpace(val)
	}

	modelInfo, found := common.ResolveLyriaModel(modelInput, appConfig.AllowUnsafeModels)
	if !found {
		return mcp.NewToolResultError(fmt.Sprintf("Error: Model '%s' is not a valid or supported model name.", modelInput)), nil
	}
	modelID := modelInfo.CanonicalName

	negativePrompt := ""
	if val, ok := params["negative_prompt"].(string); ok {
		negativePrompt = val
	}

	var seed *uint32
	if seedValFloat, ok := params["seed"].(float64); ok {
		s := uint32(seedValFloat)
		seed = &s
	}

	sampleCount := uint32(defaultSampleCount)
	if scValFloat, ok := params["sample_count"].(float64); ok {
		sc := uint32(scValFloat)
		if sc > 0 {
			sampleCount = sc
		} else {
			log.Printf("Warning: sample_count was <= 0 (%.0f), using default %d.", scValFloat, defaultSampleCount)
			sampleCount = uint32(defaultSampleCount)
		}
	}

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("negative_prompt", negativePrompt),
		attribute.String("model_id", modelID),
		attribute.Int("sample_count", int(sampleCount)),
		attribute.String("output_gcs_bucket", gcsBucketParam),
		attribute.String("file_name", fileNameParam),
		attribute.String("local_path", localDirectoryPathParameter),
	)
	if seed != nil {
		span.SetAttributes(attribute.Int("seed", int(*seed)))
	}

	log.Printf("Handling Lyria request: Prompt='%s', NegativePrompt='%s', ModelID='%s', Seed=%v, SampleCount=%d, GCSBucket='%s', FileName='%s', LocalDir='%s'",
		prompt, negativePrompt, modelID, seed, sampleCount, gcsBucketParam, fileNameParam, localDirectoryPathParameter)

	baseFilename := fileNameParam
	if baseFilename == "" {
		uid, errGen := shortid.Generate()
		if errGen != nil {
			log.Printf("Error generating shortid for filename: %v. Using default fallback.", errGen)
			baseFilename = "lyria_output_default.wav"
		} else {
			baseFilename = fmt.Sprintf("lyria_output_%s.wav", uid)
		}
		log.Printf("Generated Base Filename: %s", baseFilename)
	}
	baseFilename = strings.TrimPrefix(baseFilename, "/")

	gcsUploadedObjectName, base64AudioData, sherlogLink, err := invokeLyriaAndUpload(predictionClient, ctx, prompt, negativePrompt, seed, sampleCount, modelInfo, gcsBucketParam, baseFilename)

	duration := time.Since(startTime)
	span.SetAttributes(attribute.Float64("duration_ms", float64(duration.Milliseconds())))

	if err != nil {
		span.RecordError(err)
		log.Printf("Error in invokeLyriaAndUpload after %v: %v", duration, err)
		errMsg := fmt.Sprintf("Music generation failed after %v: %v", duration, err)
		if gcsBucketParam != "" {
			errMsg = fmt.Sprintf("Music generation or GCS upload/processing failed after %v: %v", duration, err)
		}
		return mcp.NewToolResultError(errMsg), nil
	}

	if base64AudioData == "" {
		log.Printf("invokeLyriaAndUpload returned no error but base64AudioData is empty after %v.", duration)
		return mcp.NewToolResultError(fmt.Sprintf("Music generation resulted in empty audio data after %v.", duration)), nil
	}

	var localSaveMessage string
	if localDirectoryPathParameter != "" {
		audioBytes, decodeErr := base64.StdEncoding.DecodeString(base64AudioData)
		if decodeErr != nil {
			localSaveMessage = fmt.Sprintf("Failed to decode audio for local save: %v.", decodeErr)
			log.Printf("Error decoding audio for local save (dir: %s): %v", localDirectoryPathParameter, decodeErr)
		} else {
			if errMkdir := os.MkdirAll(localDirectoryPathParameter, 0755); errMkdir != nil {
				localSaveMessage = fmt.Sprintf("Failed to create local directory %s: %v.", localDirectoryPathParameter, errMkdir)
				log.Printf("Error creating local directory %s: %v", localDirectoryPathParameter, errMkdir)
			} else {
				fullLocalPath := filepath.Join(localDirectoryPathParameter, baseFilename)
				errWrite := os.WriteFile(fullLocalPath, audioBytes, 0644)
				if errWrite != nil {
					localSaveMessage = fmt.Sprintf("Failed to save audio locally to %s: %v.", fullLocalPath, errWrite)
					log.Printf("Error saving audio locally to %s: %v", fullLocalPath, errWrite)
				} else {
					localSaveMessage = fmt.Sprintf("Successfully saved audio locally to %s.", fullLocalPath)
					log.Printf("Successfully saved audio locally to %s.", fullLocalPath)
				}
			}
		}
	}

	var resultContents []mcp.Content
	var messageText string
	var finalMessageParts []string

	// Start building the message text
	finalMessageParts = append(finalMessageParts, fmt.Sprintf("Music generation completed in %v.", duration))

	if gcsBucketParam != "" {
		if gcsUploadedObjectName != "" {
			fullGCSPath := fmt.Sprintf("gs://%s/%s", gcsBucketParam, gcsUploadedObjectName)
			finalMessageParts = append(finalMessageParts, fmt.Sprintf("Uploaded to GCS: %s.", fullGCSPath))
			log.Printf("GCS specified. Success. Path: %s.", fullGCSPath)
		} else {
			finalMessageParts = append(finalMessageParts, fmt.Sprintf("GCS upload was specified (bucket: %s) but object name was not confirmed for upload.", gcsBucketParam))
			log.Printf("GCS specified but no object name confirmed from upload. Bucket: %s.", gcsBucketParam)
		}
	}

	if localSaveMessage != "" {
		finalMessageParts = append(finalMessageParts, localSaveMessage)
	}

	if sherlogLink != "" {
		finalMessageParts = append(finalMessageParts, fmt.Sprintf("\nOptional header capture: %s", sherlogLink))
	}

	messageText = strings.Join(finalMessageParts, " ")
	textContent := mcp.TextContent{Type: "text", Text: messageText}
	resultContents = append(resultContents, textContent)

	// Only include AudioContent if NEITHER GCS nor local path was specified
	if gcsBucketParam == "" && localDirectoryPathParameter == "" {
		log.Printf("Neither GCS nor local path specified. Returning audio data directly. Length: %d", len(base64AudioData))
		audioContent := mcp.AudioContent{Type: "audio", Data: base64AudioData, MIMEType: audioMIMEType}
		resultContents = append(resultContents, audioContent)
	} else {
		log.Printf("GCS or local path specified. Audio data NOT returned directly.")
	}

	return &mcp.CallToolResult{
		Content: resultContents,
		IsError: false,
	}, nil
}

// invokeLyriaAndUpload calls the Lyria model and optionally uploads the result to GCS.
// It constructs the prediction request, sends it to the AI Platform Prediction service,
// and processes the response. If a GCS bucket is specified, it uploads the generated
// audio to the bucket.
func invokeLyriaAndUpload(client *aiplatform.PredictionClient, ctx context.Context, prompt, negativePrompt string, seed *uint32, sampleCount uint32, modelInfo common.LyriaModelInfo, gcsBucket, gcsObjectNameForUpload string) (gcsWrittenObjectName string, audioDataB64 string, sherlogLink string, err error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "invokeLyriaAndUpload")
	defer span.End()

	var audioBytes []byte
	var extractedB64Audio string

	modelID := modelInfo.CanonicalName

	// 1. GENERATE AUDIO DATA
	if modelInfo.EndpointType == "interactions" {
		// --- V3 INTERACTIONS API ROUTE ---
		log.Printf("Routing request to Interactions API for model: %s", modelID)
		audioBytes, sherlogLink, err = generateAudioWithInteractions(ctx, modelID, prompt)
		if err != nil {
			return "", "", "", fmt.Errorf("interactions API failed: %w", err)
		}
		// Interactions API gives us raw bytes, but the rest of the pipeline expects base64 string
		extractedB64Audio = base64.StdEncoding.EncodeToString(audioBytes)

	} else {
		// --- V2 PREDICTION API ROUTE ---
		lyriaEndpointPath := fmt.Sprintf("projects/%s/locations/%s/publishers/google/models/%s",
			appConfig.ProjectID, appConfig.Location, modelID)
		log.Printf("Using Lyria Prediction Endpoint Path: %s", lyriaEndpointPath)

		instanceData := map[string]interface{}{
			"prompt":       prompt,
			"sample_count": sampleCount,
		}
		if negativePrompt != "" {
			instanceData["negative_prompt"] = negativePrompt
		}
		if seed != nil {
			instanceData["seed"] = *seed
		}

		instanceStructVal, errStruct := structpb.NewValue(instanceData)
		if errStruct != nil {
			return "", "", "", fmt.Errorf("failed to create instance struct value: %w", errStruct)
		}
		instances := []*structpb.Value{instanceStructVal}

		predictRequest := &aiplatformpb.PredictRequest{
			Endpoint:  lyriaEndpointPath,
			Instances: instances,
		}

		log.Printf("Sending Predict request to Lyria model %s. Instance data: %+v", modelID, instanceData)

		resp, errPredict := client.Predict(ctx, predictRequest)
		if errPredict != nil {
			return "", "", "", fmt.Errorf("lyria prediction request failed: %w", errPredict)
		}

		if len(resp.GetPredictions()) == 0 {
			return "", "", "", errors.New("lyria prediction returned no predictions")
		}

		predictionStruct := resp.GetPredictions()[0].GetStructValue()
		if predictionStruct == nil {
			return "", "", "", errors.New("prediction is not a struct")
		}

		if generatedMusicValue, ok := predictionStruct.GetFields()["generated_music"]; ok {
			generatedMusicList := generatedMusicValue.GetListValue()
			if generatedMusicList != nil && len(generatedMusicList.GetValues()) > 0 {
				firstMusicSampleStruct := generatedMusicList.GetValues()[0].GetStructValue()
				if firstMusicSampleStruct != nil {
					if audioVal, audioOK := firstMusicSampleStruct.GetFields()["audio"]; audioOK {
						extractedB64Audio = audioVal.GetStringValue()
					} else if audioVal, b64OK := firstMusicSampleStruct.GetFields()["bytesBase64Encoded"]; b64OK {
						extractedB64Audio = audioVal.GetStringValue()
					}
				}
			}
		}
		if extractedB64Audio == "" {
			if base64AudioValue, directAudioOK := predictionStruct.GetFields()["bytesBase64Encoded"]; directAudioOK {
				extractedB64Audio = base64AudioValue.GetStringValue()
			}
		}

		if extractedB64Audio == "" {
			return "", "", "", errors.New("failed to extract audio data (audio or bytesBase64Encoded) from Lyria prediction")
		}
		
		audioBytes, err = base64.StdEncoding.DecodeString(extractedB64Audio)
		if err != nil {
			return "", "", "", fmt.Errorf("failed to decode base64 audio data: %w", err)
		}
	}

	log.Printf("Received audio data (decoded length: %d bytes) from Lyria.", len(audioBytes))

	// 2. OPTIONAL GCS UPLOAD
	if gcsBucket != "" {
		if gcsObjectNameForUpload == "" {
			return "", extractedB64Audio, sherlogLink, errors.New("GCS bucket provided but object name for upload is empty")
		}
		
		uploadErr := common.UploadToGCS(ctx, gcsBucket, gcsObjectNameForUpload, audioMIMEType, audioBytes)
		if uploadErr != nil {
			return "", extractedB64Audio, sherlogLink, fmt.Errorf("failed to upload audio to GCS (bucket: %s, object: %s): %w", gcsBucket, gcsObjectNameForUpload, uploadErr)
		}
		log.Printf("Successfully uploaded audio sample to gs://%s/%s", gcsBucket, gcsObjectNameForUpload)
		return gcsObjectNameForUpload, extractedB64Audio, sherlogLink, nil
	}

	log.Println("GCS bucket not provided, skipping upload.")
	return "", extractedB64Audio, sherlogLink, nil
}
