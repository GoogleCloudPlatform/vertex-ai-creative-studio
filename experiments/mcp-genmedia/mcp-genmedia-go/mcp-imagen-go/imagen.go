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

// Package main implements an MCP server for Google's Imagen models.

package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/rs/cors"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/genai"
)

var (
	appConfig   *common.Config
	genAIClient *genai.Client // Global GenAI client
	transport   string
)

const (
	serviceName = "mcp-imagen-go"
	version     = "1.10.2" // Updates default model
)

func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
	flag.Parse()
}

// main is the entry point for the mcp-imagen-go service.
func main() {
	appConfig = common.LoadConfig()

	tp, err := common.InitTracerProvider(serviceName, version)
	if err != nil {
		log.Fatalf("failed to initialize tracer provider: %v", err)
	}
	if tp != nil {
		defer func() {
			if err := tp.Shutdown(context.Background()); err != nil {
				log.Printf("Error shutting down tracer provider: %v", err)
			}
		}()
	}

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

	s := server.NewMCPServer("Imagen", version, server.WithResourceCapabilities(true, true))
	registerImagenEditingTools(s, genAIClient, appConfig)

	s.AddResource(mcp.NewResource(
		"imagen://models",
		"Supported Imagen Models",
		mcp.WithResourceDescription("A list of supported Imagen models and their aliases."),
		mcp.WithMIMEType("application/json"),
	), func(ctx context.Context, request mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
		jsonData, err := json.MarshalIndent(common.SupportedImagenModels, "", "  ")
		if err != nil {
			return nil, fmt.Errorf("failed to marshal supported models: %w", err)
		}
		return []mcp.ResourceContents{
			mcp.TextResourceContents{
				URI:      "imagen://models",
				MIMEType: "application/json",
				Text:     string(jsonData),
			},
		},
		nil
	})

	tool := mcp.NewTool("imagen_t2i",
		mcp.WithDescription("Generates an image based on a text prompt using Google's Imagen models. The image can be returned as base64 data, saved to a local directory, or stored in a Google Cloud Storage bucket."),
		mcp.WithString("prompt", mcp.Required(), mcp.Description("Prompt for text to image generation")),
		mcp.WithString("model",
			mcp.DefaultString("imagen-4.0-fast-generate-001"),
			mcp.Description(common.BuildImagenModelDescription()),
		),
		mcp.WithNumber("num_images",
			mcp.DefaultNumber(1),
			mcp.Min(1),
			mcp.Max(4),
			mcp.Description("Number of images to generate (1-4). Note: the maximum is model-dependent."),
		),
		mcp.WithString("aspect_ratio",
			mcp.DefaultString("1:1"),
			mcp.Description("Aspect ratio of the generated images (e.g., \"1:1\", \"16:9\", \"9:16\")."),
		),
		mcp.WithString("image_size",
			mcp.DefaultString("1K"),
			mcp.Description("Optional. The size of the largest dimension of the generated image. Supported sizes are 1K and 2K (not supported for Imagen 3 models)."),
		),
		mcp.WithString("gcs_bucket_uri", mcp.Description("Optional. GCS URI prefix to store the generated images (e.g., your-bucket/outputs/ or gs://your-bucket/outputs/).")),
		mcp.WithString("output_directory", mcp.Description("Optional. Local directory to save the generated image(s) to.")),
	)

	handlerWithClient := func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return imagenGenerationHandler(genAIClient, ctx, request)
	}
	s.AddTool(tool, handlerWithClient)

	s.AddPrompt(mcp.NewPrompt("generate-image",
		mcp.WithPromptDescription("Generates an image from a text prompt."),
		mcp.WithArgument("prompt", mcp.ArgumentDescription("The text prompt to generate an image from."), mcp.RequiredArgument()),
		mcp.WithArgument("model", mcp.ArgumentDescription("The model to use for generation.")),
		mcp.WithArgument("num_images", mcp.ArgumentDescription("The number of images to generate.")),
		mcp.WithArgument("aspect_ratio", mcp.ArgumentDescription("The aspect ratio of the generated images.")),
	), func(ctx context.Context, request mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		prompt, ok := request.Params.Arguments["prompt"]
		if !ok || strings.TrimSpace(prompt) == "" {
			return mcp.NewGetPromptResult(
				"Missing Prompt",
				[]mcp.PromptMessage{
					mcp.NewPromptMessage(mcp.RoleAssistant, mcp.NewTextContent("What would you like to create an image of?")),
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
		result, err := imagenGenerationHandler(genAIClient, ctx, toolRequest)
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
			"Image Generation Result",
			[]mcp.PromptMessage{
				mcp.NewPromptMessage(mcp.RoleAssistant, mcp.NewTextContent(strings.TrimSpace(responseText))),
			},
		), nil
	})

	log.Printf("Starting Imagen MCP Server (Version: %s, Transport: %s)", version, transport)

	if transport == "sse" {
		// Assuming 8081 is the desired SSE port for Imagen to avoid conflict if HTTP uses 8080
		sseServer := server.NewSSEServer(s, server.WithBaseURL("http://localhost:8081"))
		log.Printf("Imagen MCP Server listening on SSE at :8081 with t2i tools")
		if err := sseServer.Start(":8081"); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
	} else if transport == "http" {
		mcpHTTPHandler := server.NewStreamableHTTPServer(s) // Base path /mcp

		// Configure CORS
		c := cors.New(cors.Options{
			AllowedOrigins:   []string{"*"}, // Consider making this configurable via env var for production
			AllowedMethods:   []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodDelete, http.MethodOptions, http.MethodHead},
			AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-MCP-Progress-Token"},
			ExposedHeaders:   []string{"Link"},
			AllowCredentials: true,
			MaxAge:           300, // In seconds
		})

		handlerWithCORS := c.Handler(mcpHTTPHandler)

		httpPort := os.Getenv("PORT")
		if httpPort == "" {
			httpPort = "8080"
		}

		listenAddr := fmt.Sprintf(":%s", httpPort)
		log.Printf("Imagen MCP Server listening on HTTP at %s/mcp with t2i tools and CORS enabled", listenAddr)
		if err := http.ListenAndServe(listenAddr, handlerWithCORS); err != nil {
			log.Fatalf("HTTP Server error: %v", err)
		}
	} else { // Default to stdio
		if transport != "stdio" && transport != "" {
			log.Printf("Unsupported transport type '%s' specified, defaulting to stdio.", transport)
		}
		log.Printf("Imagen MCP Server listening on STDIO with t2i tools")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	}
	log.Println("Imagen Server has stopped.")
}

type ImagenOutput struct {
	GCSURIs   []string `json:"gcsUris"`
	HTTPSURLs []string `json:"httpsURLs"`
	Message   string   `json:"message"`
}

func contains(s []string, e string) bool {
	for _, a := range s {
		if a == e {
			return true
		}
	}
	return false
}

func imagenGenerationHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "imagen_t2i")
	defer span.End()

	prompt, ok := request.GetArguments()["prompt"].(string)
	if !ok {
		return &mcp.CallToolResult{Content: []mcp.Content{mcp.TextContent{Type: "text", Text: "Error: prompt must be a string and is required"}}}, nil
	}

	modelInput, ok := request.GetArguments()["model"].(string)
	if !ok || modelInput == "" {
		log.Printf("Model not provided or empty, using default: imagen-4.0-fast-generate-001")
		modelInput = "imagen-4.0-fast-generate-001"
	}

	canonicalName, found := common.ResolveImagenModel(modelInput)
	if !found {
		return &mcp.CallToolResult{Content: []mcp.Content{mcp.TextContent{Type: "text", Text: fmt.Sprintf("Error: Model '%s' is not a valid or supported model name.", modelInput)}}}, nil
	}
	model := canonicalName
	modelDetails := common.SupportedImagenModels[model]

	var numberOfImages int32 = 1
	if numImagesArg, ok := request.GetArguments()["num_images"]; ok {
		if numImagesFloat, okFloat := numImagesArg.(float64); okFloat {
			numberOfImages = int32(numImagesFloat)
		} else {
			log.Printf("Warning: num_images was not a float64, received %T. Using default.", numImagesArg)
		}
	}

	if numberOfImages < 1 {
		numberOfImages = 1
	}
			if numberOfImages > modelDetails.MaxImages {
				log.Printf("Warning: Requested %d images, but model %s only supports up to %d. Adjusting to max.", numberOfImages, model, modelDetails.MaxImages)
				numberOfImages = modelDetails.MaxImages
			}
	
			aspectRatio, ok := request.GetArguments()["aspect_ratio"].(string)
			if !ok || aspectRatio == "" {
				log.Printf("Aspect ratio not provided or empty, using default: 1:1")
				aspectRatio = "1:1"
			}
	
					if !contains(modelDetails.SupportedAspectRatios, aspectRatio) {
						log.Printf("Warning: Requested aspect ratio '%s' is not supported by model %s. Supported ratios are: %v. Falling back to '1:1'.", aspectRatio, model, modelDetails.SupportedAspectRatios)
						aspectRatio = "1:1" // Fallback to a safe default
					}
			
					imageSize, _ := request.GetArguments()["image_size"].(string)
					var finalImageSize string
					if imageSize != "" {
						if len(modelDetails.SupportedImageSizes) == 0 {
							log.Printf("Warning: image_size parameter ('%s') provided, but model %s does not support it. The parameter will be ignored.", imageSize, model)
						} else if !contains(modelDetails.SupportedImageSizes, imageSize) {
							log.Printf("Warning: Requested image size '%s' is not supported by model %s. Supported sizes are: %v. The parameter will be ignored.", imageSize, model, modelDetails.SupportedImageSizes)
						} else {
							finalImageSize = imageSize
						}
					}	// ... rest of handler ...
	gcsOutputURI := ""
	gcsBucketUriParam, _ := request.GetArguments()["gcs_bucket_uri"].(string)
	gcsBucketUriParam = strings.TrimSpace(gcsBucketUriParam)

	if gcsBucketUriParam != "" {
		gcsOutputURI = gcsBucketUriParam
		if !strings.HasPrefix(gcsOutputURI, "gs://") {
			gcsOutputURI = "gs://" + gcsOutputURI
			log.Printf("gcs_bucket_uri did not start with 'gs://', prepended. New URI: %s", gcsOutputURI)
		}
	} else if appConfig.GenmediaBucket != "" {
		gcsOutputURI = fmt.Sprintf("gs://%s/imagen_outputs/", appConfig.GenmediaBucket)
		log.Printf("Handler imagen_t2i: 'gcs_bucket_uri' parameter not provided, using default constructed from GENMEDIA_BUCKET: %s", gcsOutputURI)
	} else {
		log.Printf("Handler imagen_t2i: 'gcs_bucket_uri' parameter and GENMEDIA_BUCKET env var are both empty. No GCS output will be saved.")
	}

	if gcsOutputURI != "" && !strings.HasSuffix(gcsOutputURI, "/") {
		gcsOutputURI += "/"
		log.Printf("Appended '/' to gcsOutputURI for directory structure. New URI: %s", gcsOutputURI)
	}

	outputDir := ""
	if dir, ok := request.GetArguments()["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}
	attemptLocalSave := outputDir != ""

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("model", model),
		attribute.Int("num_images", int(numberOfImages)),
		attribute.String("aspect_ratio", aspectRatio),
		attribute.String("image_size", finalImageSize),
		attribute.String("gcs_bucket_uri", gcsBucketUriParam),
		attribute.String("output_directory", outputDir),
	)

	select {
	case <-ctx.Done():
		errMsg := fmt.Sprintf("Request processing canceled early: %v", ctx.Err())
		log.Printf("Incoming context for prompt \"%s\" was already canceled: %v", prompt, ctx.Err())
		return &mcp.CallToolResult{Content: []mcp.Content{mcp.TextContent{Type: "text", Text: errMsg}}}, nil
	default:
		log.Printf("Handling imagen request: Prompt=\"%s\", Model=%s, NumImages=%d, AspectRatio=%s, ImageSize=%s, GCSOutputURI='%s', OutputDirectory='%s'",
			prompt, model, numberOfImages, aspectRatio, finalImageSize, gcsOutputURI, outputDir)
	}

	config := &genai.GenerateImagesConfig{
		NumberOfImages: numberOfImages,
		AspectRatio:    aspectRatio,
		ImageSize:      finalImageSize,
		OutputGCSURI:   gcsOutputURI,
	}

	apiCallCtx, apiCallCancel := context.WithTimeout(ctx, 3*time.Minute)
	defer apiCallCancel()

	log.Printf("Calling GenerateImages with Model: %s, Prompt: \"%s\". API call timeout: 3m", model, prompt)
	startTime := time.Now()

	response, err := client.Models.GenerateImages(
		apiCallCtx,
		model,
		prompt,
		config,
	)

	apiCallDuration := time.Since(startTime)
	log.Printf("GenerateImages call took: %v", apiCallDuration)
	span.SetAttributes(attribute.Float64("duration_ms", float64(apiCallDuration.Milliseconds())))

	var contentItems []mcp.Content

	if err != nil {
		errorMessage := fmt.Sprintf("error generating images: %v", err.Error())
		if errors.Is(err, context.DeadlineExceeded) && apiCallCtx.Err() == context.DeadlineExceeded {
			log.Printf("GenerateImages failed due to API call timeout (3 minutes): %v", err)
			errorMessage = "image generation timed out"
		} else if errors.Is(err, context.Canceled) {
			log.Printf("GenerateImages failed due to context cancellation: %v", err)
			errorMessage = "image generation was canceled"
		} else {
			log.Printf("Error generating images (API call failed): %v", err)
		}
		span.RecordError(err)
		contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: errorMessage})
		return &mcp.CallToolResult{Content: contentItems}, nil
	}

	if response == nil || len(response.GeneratedImages) == 0 {
		noImageText := fmt.Sprintf("Sorry, I couldn't generate any images for the prompt \"%s\".", prompt)
		log.Print(noImageText)
		contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: noImageText})
		return &mcp.CallToolResult{Content: contentItems}, nil
	}

	log.Printf("Successfully received %d image metadata/references from API.", len(response.GeneratedImages))

	var savedLocalFilenames []string
	var failedLocalSaveReasons []string
	var gcsSavedURIs []string
	var totalSizeBytesGenerated int64 = 0
	var imagesWithDataOrURI int = 0
	returnImageDataInResponse := gcsOutputURI == "" && !attemptLocalSave
	log.Printf("Will return image data in response: %t", returnImageDataInResponse)

	for n, genImg := range response.GeneratedImages {
		var imageData []byte
		var imageMimeType string = "image/png"
		var imageSourceIsGCS bool = false
		var currentImageGCSURI string

		if genImg.Image != nil && genImg.Image.GCSURI != "" {
			currentImageGCSURI = genImg.Image.GCSURI
			imagesWithDataOrURI++
			imageSourceIsGCS = true
			gcsSavedURIs = append(gcsSavedURIs, currentImageGCSURI)
			log.Printf("Image %d available at GCS URI (from API response): %s", n, currentImageGCSURI)
			if genImg.Image.MIMEType != "" {
				imageMimeType = genImg.Image.MIMEType
			}
		} else if genImg.Image != nil && genImg.Image.ImageBytes != nil && len(genImg.Image.ImageBytes) > 0 {
			imagesWithDataOrURI++
			imageData = genImg.Image.ImageBytes
			totalSizeBytesGenerated += int64(len(imageData))
			if genImg.Image.MIMEType != "" {
				imageMimeType = genImg.Image.MIMEType
			}
			log.Printf("Image %d received as bytes from API (Size: %s, MIME: %s)", n, common.FormatBytes(int64(len(imageData))), imageMimeType)
		} else {
			log.Printf("Generated image %d (model: %s) from API had no GCS URI and no direct image data.", n, model)
			continue
		}

		if attemptLocalSave {
			localFilename := fmt.Sprintf("imagen-%s-%s-%d", model, time.Now().Format("20060102-150405"), n)
			switch imageMimeType {
			case "image/jpeg":
				localFilename += ".jpg"
			case "image/webp":
				localFilename += ".webp"
			default:
				localFilename += ".png"
			}
			actualSavePath := filepath.Join(outputDir, localFilename)
			actualSavePath = filepath.Clean(actualSavePath)

			if imageSourceIsGCS {
				log.Printf("Attempting to download image %d from GCS URI %s to %s", n, currentImageGCSURI, actualSavePath)
				downloadCtx, downloadCancel := context.WithTimeout(ctx, 2*time.Minute)
				err := common.DownloadFromGCS(downloadCtx, currentImageGCSURI, actualSavePath)
				downloadCancel()
				if err != nil {
					log.Print(err)
					failedLocalSaveReasons = append(failedLocalSaveReasons, err.Error())
				} else {
					log.Printf("Successfully downloaded and saved image %d to %s", n, actualSavePath)
					savedLocalFilenames = append(savedLocalFilenames, actualSavePath)
					fileInfo, statErr := os.Stat(actualSavePath)
					if statErr == nil {
						totalSizeBytesGenerated += fileInfo.Size()
					} else {
						log.Printf("Could not get file info for downloaded file %s: %v", actualSavePath, statErr)
					}
				}
			} else if len(imageData) > 0 {
				if err := os.MkdirAll(outputDir, 0755); err != nil {
					log.Print(err)
					failedLocalSaveReasons = append(failedLocalSaveReasons, err.Error())
				} else {
					if err := os.WriteFile(actualSavePath, imageData, 0644); err != nil {
						log.Print(err)
						failedLocalSaveReasons = append(failedLocalSaveReasons, err.Error())
					} else {
						log.Printf("Saved image %s (Size: %s)", actualSavePath, common.FormatBytes(int64(len(imageData))))
						savedLocalFilenames = append(savedLocalFilenames, actualSavePath)
					}
				}
			}
		}

		if returnImageDataInResponse && len(imageData) > 0 {
			base64Data := base64.StdEncoding.EncodeToString(imageData)
			imageItem := mcp.ImageContent{
				Type:     "image",
				Data:     base64Data,
				MIMEType: imageMimeType,
			}
			contentItems = append(contentItems, imageItem)
		}
	}

	var resultText string
	var saveMessageParts []string

	if gcsOutputURI != "" {
		if len(gcsSavedURIs) > 0 {
			httpURIs := make([]string, len(gcsSavedURIs))
			for i, gcsUri := range gcsSavedURIs {
				httpURIs[i] = strings.Replace(gcsUri, "gs://", "https://storage.mtls.cloud.google.com/", 1)
			}
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Images saved to GCS: %s. HTTPS URLs: %s.", strings.Join(gcsSavedURIs, ", "), strings.Join(httpURIs, ", ")))
		} else if imagesWithDataOrURI > 0 && len(gcsSavedURIs) == 0 {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("GCS output was requested to '%s', but API did not return GCS URIs for the generated images.", config.OutputGCSURI))
		} else {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("GCS output was requested to '%s', but no images with GCS URIs were returned by the API.", config.OutputGCSURI))
		}
	}

	if attemptLocalSave {
		if gcsOutputURI != "" {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Attempted to download images from GCS to local directory '%s'.", outputDir))
		} else {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Attempted to save images from API response bytes to local directory '%s'.", outputDir))
		}
		if len(savedLocalFilenames) > 0 {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Successfully saved locally: %s.", strings.Join(savedLocalFilenames, ", ")))
		}
		if len(failedLocalSaveReasons) > 0 {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Local save/download issues: %s.", strings.Join(failedLocalSaveReasons, "; ")))
		}
	}

	if !returnImageDataInResponse {
		saveMessageParts = append(saveMessageParts, "Image data is not included in this MCP response because a GCS URI or local output directory was specified.")
	} else if returnImageDataInResponse && imagesWithDataOrURI > 0 {
		saveMessageParts = append(saveMessageParts, "Image(s) are included in this MCP response as base64 data.")
	}

	sizeReport := ""
	if totalSizeBytesGenerated > 0 {
		sizeReport = fmt.Sprintf("(total processed/downloaded byte size: %s) ", common.FormatBytes(totalSizeBytesGenerated))
	} else if len(gcsSavedURIs) > 0 && !attemptLocalSave {
		sizeReport = "(image sizes are on GCS) "
	}

	if imagesWithDataOrURI > 0 {
		resultText = fmt.Sprintf("Generated %d image(s) %susing model %s for prompt \"%s\". This took about %s. %s",
			imagesWithDataOrURI,
			sizeReport,
			model,
			prompt,
			apiCallDuration.Round(time.Second),
			strings.Join(saveMessageParts, " "),
		)
	} else {
		resultText = fmt.Sprintf("Processed request for model %s with prompt \"%s\" (took %s), but no images with data or GCS URIs were returned by the API.",
			model,
			prompt,
			apiCallDuration.Round(time.Second),
		)
	}

	textItem := mcp.TextContent{
		Type: "text",
		Text: strings.TrimSpace(resultText),
	}

	finalContentItems := []mcp.Content{textItem}
	if returnImageDataInResponse {
		finalContentItems = append(finalContentItems, contentItems...)
	}

	return &mcp.CallToolResult{Content: finalContentItems}, nil
}
