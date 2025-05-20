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
	"encoding/base64"
	"errors"
	"flag"
	"fmt"
	"io" // Required for GCS download
	"log"
	"os"
	"path/filepath" // For manipulating file paths
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

const version = "1.4.3" // Incremented version for GCS download implementation

// formatBytes converts a size in bytes to a human-readable string (KB, MB, GB).
func formatBytes(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
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
func downloadFromGCS(ctx context.Context, gcsURI string, localDestPath string) error {
	bucketName, objectName, err := parseGCSPath(gcsURI)
	if err != nil {
		return fmt.Errorf("parseGCSPath for %s: %w", gcsURI, err)
	}

	storageClient, err := storage.NewClient(ctx)
	if err != nil {
		return fmt.Errorf("storage.NewClient: %w", err)
	}
	defer storageClient.Close()

	// Create a new context with its own timeout for the GCS operation
	// to avoid being cancelled by the parent context if it's too short.
	gcsCtx, cancel := context.WithTimeout(ctx, time.Second*60) // 60-second timeout for download
	defer cancel()

	rc, err := storageClient.Bucket(bucketName).Object(objectName).NewReader(gcsCtx)
	if err != nil {
		return fmt.Errorf("Object(%q in bucket %q).NewReader: %w", objectName, bucketName, err)
	}
	defer rc.Close()

	// Ensure destination directory exists
	destDir := filepath.Dir(localDestPath)
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return fmt.Errorf("os.MkdirAll for %s: %w", destDir, err)
	}

	f, err := os.Create(localDestPath)
	if err != nil {
		return fmt.Errorf("os.Create for %s: %w", localDestPath, err)
	}
	defer f.Close() // Ensure file is closed

	if _, err := io.Copy(f, rc); err != nil {
		return fmt.Errorf("io.Copy to %s: %w", localDestPath, err)
	}

	// f.Close() is called by defer, but an explicit close here can catch errors earlier.
	// However, the deferred close will still run.
	// if err = f.Close(); err != nil {
	//  return fmt.Errorf("f.Close for %s: %w", localDestPath, err)
	// }
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
	// Get Project ID from environment variable
	project = os.Getenv("PROJECT_ID")
	if project == "" {
		log.Fatal("PROJECT_ID environment variable not set. Please set the env variable, e.g. export PROJECT_ID=$(gcloud config get project)")
	}
	// Get Location from environment variable, default to us-central1
	location = os.Getenv("LOCATION")
	if location == "" {
		location = "us-central1"
		log.Printf("LOCATION environment variable not set, defaulting to %s", location)
	}

	// Initialize Google GenAI Client once
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

	// Create MCP server
	s := server.NewMCPServer(
		"Google Cloud Imagen 3",
		version,
	)

	// Define the tool for Imagen text-to-image generation
	tool := mcp.NewTool("imagen_t2i",
		mcp.WithDescription("Generate an image with Imagen 3. Options to save to GCS, save locally, or return base64 data."),
		mcp.WithString("prompt",
			mcp.Required(),
			mcp.Description("Prompt for text to image generation"),
		),
		mcp.WithString("model",
			mcp.DefaultString("imagen-3.0-generate-002"),
			mcp.Description("Model to use for image generation (e.g., imagen-3.0-generate-002)"),
		),
		mcp.WithNumber("num_images",
			mcp.DefaultNumber(1),
			mcp.Min(1),
			mcp.Max(4),
			mcp.Description("Number of images to generate (1-4)"),
		),
		mcp.WithString("aspect_ratio",
			mcp.DefaultString("1:1"),
			mcp.Description("Aspect ratio of the generated images (e.g., 1:1, 16:9, 9:16)"),
		),
		mcp.WithString("gcs_bucket_uri",
			mcp.Description("Optional. GCS URI prefix to store the generated images (e.g., your-bucket/outputs/ or gs://your-bucket/outputs/). If provided, images are saved to GCS instead of returning bytes directly. Filenames are generated by the API."),
		),
		mcp.WithString("output_directory",
			mcp.Description("Optional. If provided, specifies a local directory to save the generated image(s) to. If gcs_bucket_uri is also set, images will be downloaded from GCS. Filenames will be generated automatically."),
		),
	)

	handlerWithClient := func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return imagenGenerationHandler(genAIClient, ctx, request)
	}
	s.AddTool(tool, handlerWithClient)

	if transport == "sse" {
		sseServer := server.NewSSEServer(s, server.WithBaseURL("http://localhost:8080"))
		log.Printf("SSE server listening on :8080 with t2i tools")
		if err := sseServer.Start(":8080"); err != nil {
			log.Fatalf("Server error: %v", err)
		}
		log.Println("Server has stopped.")
	} else {
		log.Printf("STDIO server listening with t2i tools")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("Server error: %v", err)
		}
	}
}

// imagenGenerationHandler invokes Imagen text to image generation
func imagenGenerationHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	// --- 1. Parse Parameters ---
	prompt, ok := request.GetArguments()["prompt"].(string)
	if !ok {
		return &mcp.CallToolResult{Content: []mcp.Content{mcp.TextContent{Type: "text", Text: "Error: prompt must be a string and is required"}}}, nil
	}

	model, ok := request.GetArguments()["model"].(string)
	if !ok || model == "" {
		log.Printf("Model not provided or empty, using default: imagen-3.0-generate-002")
		model = "imagen-3.0-generate-002"
	}

	var numberOfImages int32 = 1
	numImagesArg, ok := request.GetArguments()["num_images"]
	if ok {
		if numImagesFloat, okFloat := numImagesArg.(float64); okFloat {
			numberOfImages = int32(numImagesFloat)
		} else {
			log.Printf("Warning: num_images was not a float64, received %T. Using default.", numImagesArg)
		}
	}
	if numberOfImages < 1 {
		numberOfImages = 1
	}
	if numberOfImages > 4 {
		numberOfImages = 4
	}

	aspectRatio, ok := request.GetArguments()["aspect_ratio"].(string)
	if !ok || aspectRatio == "" {
		log.Printf("Aspect ratio not provided or empty, using default: 1:1")
		aspectRatio = "1:1"
	}

	gcsOutputURI := ""
	if uri, ok := request.GetArguments()["gcs_bucket_uri"].(string); ok && strings.TrimSpace(uri) != "" {
		gcsOutputURI = strings.TrimSpace(uri)
		if !strings.HasPrefix(gcsOutputURI, "gs://") {
			gcsOutputURI = "gs://" + gcsOutputURI
			log.Printf("gcs_bucket_uri did not start with 'gs://', prepended. New URI: %s", gcsOutputURI)
		}
		if !strings.HasSuffix(gcsOutputURI, "/") {
			gcsOutputURI += "/"
			log.Printf("Appended '/' to gcs_bucket_uri for directory structure. New URI: %s", gcsOutputURI)
		}
	}

	outputDir := ""
	if dir, ok := request.GetArguments()["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}
	attemptLocalSave := outputDir != ""

	select {
	case <-ctx.Done():
		errMsg := fmt.Sprintf("Request processing canceled early: %v", ctx.Err())
		log.Printf("Incoming context for prompt \"%s\" was already canceled: %v", prompt, ctx.Err())
		return &mcp.CallToolResult{Content: []mcp.Content{mcp.TextContent{Type: "text", Text: errMsg}}}, nil
	default:
		log.Printf("Handling imagen request: Prompt=\"%s\", Model=%s, NumImages=%d, AspectRatio=%s, GCSOutputURI='%s', OutputDirectory='%s'",
			prompt, model, numberOfImages, aspectRatio, gcsOutputURI, outputDir)
	}

	config := &genai.GenerateImagesConfig{
		NumberOfImages: numberOfImages,
		AspectRatio:    aspectRatio,
	}
	if gcsOutputURI != "" {
		config.OutputGCSURI = gcsOutputURI
		log.Printf("API will save images directly to GCS: %s", gcsOutputURI)
	} else {
		log.Printf("API will return image bytes directly.")
	}

	apiCallCtx, apiCallCancel := context.WithTimeout(context.Background(), 3*time.Minute)
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

	var contentItems []mcp.Content

	if err != nil {
		errMessage := fmt.Sprintf("error generating images: %v", err.Error())
		if errors.Is(err, context.DeadlineExceeded) && apiCallCtx.Err() == context.DeadlineExceeded {
			log.Printf("GenerateImages failed due to API call timeout (3 minutes): %v", err)
			errMessage = "image generation timed out"
		} else if errors.Is(err, context.Canceled) {
			log.Printf("GenerateImages failed due to context cancellation: %v", err)
			errMessage = "image generation was canceled"
		} else {
			log.Printf("Error generating images (API call failed): %v", err)
		}
		contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: errMessage})
		return &mcp.CallToolResult{Content: contentItems}, nil
	}

	if response == nil || len(response.GeneratedImages) == 0 {
		noImageText := fmt.Sprintf("Sorry, I couldn't generate any images for the prompt \"%s\".", prompt)
		log.Printf(noImageText)
		contentItems = append(contentItems, mcp.TextContent{Type: "text", Text: noImageText})
		return &mcp.CallToolResult{Content: contentItems}, nil
	}

	log.Printf("Successfully received %d image metadata/references from API.", len(response.GeneratedImages))

	var savedLocalFilenames []string
	var failedLocalSaveReasons []string
	var gcsSavedURIs []string
	var totalSizeBytesGenerated int64 = 0 // Only for bytes directly from API
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
			log.Printf("Image %d received as bytes from API (Size: %s, MIME: %s)", n, formatBytes(int64(len(imageData))), imageMimeType)
		} else {
			log.Printf("Generated image %d (model: %s) from API had no GCS URI and no direct image data.", n, model)
			continue
		}

		// Handle local saving
		if attemptLocalSave {
			localFilename := fmt.Sprintf("imagen-%s-%s-%d", model, time.Now().Format("20060102-150405"), n)
			// Add extension based on MIME type, default to .png
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

			if imageSourceIsGCS { // Download from GCS then save
				log.Printf("Attempting to download image %d from GCS URI %s to %s", n, currentImageGCSURI, actualSavePath)
				// Use a new context for the download operation
				downloadCtx, downloadCancel := context.WithTimeout(context.Background(), 2*time.Minute) // 2 min timeout for download
				err := downloadFromGCS(downloadCtx, currentImageGCSURI, actualSavePath)
				downloadCancel() // Release context resources
				if err != nil {
					errMsg := fmt.Sprintf("Error downloading image %d from %s to %s: %v", n, currentImageGCSURI, actualSavePath, err)
					log.Print(errMsg)
					failedLocalSaveReasons = append(failedLocalSaveReasons, errMsg)
				} else {
					log.Printf("Successfully downloaded and saved image %d to %s", n, actualSavePath)
					savedLocalFilenames = append(savedLocalFilenames, actualSavePath)
					// If downloaded, get file info to report size
					fileInfo, statErr := os.Stat(actualSavePath)
					if statErr == nil {
						totalSizeBytesGenerated += fileInfo.Size() // Add downloaded file size
					} else {
						log.Printf("Could not get file info for downloaded file %s: %v", actualSavePath, statErr)
					}
				}
			} else if len(imageData) > 0 { // Save directly from bytes
				if err := os.MkdirAll(outputDir, 0755); err != nil {
					errMsg := fmt.Sprintf("Error creating directory %s for image %d: %v", outputDir, n, err)
					log.Print(errMsg)
					failedLocalSaveReasons = append(failedLocalSaveReasons, errMsg)
				} else {
					if err := os.WriteFile(actualSavePath, imageData, 0644); err != nil {
						errMsg := fmt.Sprintf("Error writing image file %s: %v", actualSavePath, err)
						log.Print(errMsg)
						failedLocalSaveReasons = append(failedLocalSaveReasons, errMsg)
					} else {
						log.Printf("Saved image %s (Size: %s)", actualSavePath, formatBytes(int64(len(imageData))))
						savedLocalFilenames = append(savedLocalFilenames, actualSavePath)
					}
				}
			}
		}

		// Add image data to MCP response ONLY if no GCS output and no local save specified
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

	// --- 5. Prepare Text Summary and Add to MCP Content ---
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
	if totalSizeBytesGenerated > 0 { // This now reflects size of direct bytes OR downloaded files
		sizeReport = fmt.Sprintf("(total processed/downloaded byte size: %s) ", formatBytes(totalSizeBytesGenerated))
	} else if len(gcsSavedURIs) > 0 && !attemptLocalSave { // Only GCS URIs, no download attempt
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
