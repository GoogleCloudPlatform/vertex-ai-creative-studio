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
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"cloud.google.com/go/storage"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/teris-io/shortid"
	// Mimetype detection can be added if needed for advanced logic
	// "github.com/gabriel-vasile/mimetype"
)

var (
	// MCP Server settings
	transport string
	version   = "1.0.2" // Incremented version

	// Google Cloud settings - typically set via environment variables
	gcpProjectID string // PROJECT_ID for GCS operations
	gcpLocation  string // LOCATION (not directly used by FFMpeg server but good for consistency)
)

const (
	defaultTempDirPrefix = "mcp_avtool_"
)

// init handles command-line flags and initial logging setup.
func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio or sse)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio or sse)")
}

// getEnv gets an environment variable or returns a default value.
func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	log.Printf("Environment variable %s not set, using fallback: %s", key, fallback)
	return fallback
}

// loadConfiguration loads settings from environment variables.
func loadConfiguration() {
	gcpProjectID = os.Getenv("PROJECT_ID")
	if gcpProjectID == "" {
		log.Println("WARNING: PROJECT_ID environment variable not set. GCS operations will not be available.")
	} else {
		log.Printf("Using GCP Project ID: %s for GCS operations.", gcpProjectID)
	}
	gcpLocation = getEnv("LOCATION", "us-central1")
	log.Printf("Using GCP Location: %s (primarily for GCS client initialization context if needed).", gcpLocation)
}

// main is the entry point of the application.
func main() {
	flag.Parse()
	loadConfiguration()

	s := server.NewMCPServer(
		"FFMpeg AV Processing Tool",
		version,
	)

	addConvertAudioTool(s)
	addCombineAudioVideoTool(s)
	addOverlayImageOnVideoTool(s)
	addConcatenateMediaTool(s)
	addAdjustVolumeTool(s)
	addLayerAudioTool(s)

	log.Printf("Starting FFMpeg AV Tool MCP Server (Version: %s, Transport: %s)", version, transport)
	if transport == "sse" {
		sseServer := server.NewSSEServer(s, server.WithBaseURL("http://localhost:8081"))
		log.Printf("SSE server listening on :8081")
		if err := sseServer.Start(":8081"); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
	} else {
		log.Printf("STDIO server listening")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	}
	log.Println("Server has stopped.")
}

// runFFmpegCommand executes an FFMpeg command and returns its combined output.
func runFFmpegCommand(ctx context.Context, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, "ffmpeg", args...)
	log.Printf("Running FFMpeg command: ffmpeg %s", strings.Join(args, " "))

	output, err := cmd.CombinedOutput()
	if err != nil {
		log.Printf("FFMpeg command failed. Error: %v\nFFMpeg Output:\n%s", err, string(output))
		return string(output), fmt.Errorf("ffmpeg command failed: %w. Output: %s", err, string(output))
	}
	log.Printf("FFMpeg command successful. Output (last few lines):\n%s", getTail(string(output), 5))
	return string(output), nil
}

func getTail(s string, n int) string {
	lines := strings.Split(s, "\n")
	if len(lines) <= n {
		return s
	}
	return strings.Join(lines[len(lines)-n:], "\n")
}

func prepareInputFile(ctx context.Context, fileURI, purpose string) (localPath string, cleanupFunc func(), err error) {
	cleanupFunc = func() {}

	if strings.HasPrefix(fileURI, "gs://") {
		if gcpProjectID == "" {
			return "", cleanupFunc, errors.New("PROJECT_ID not set, cannot download from GCS")
		}
		tempDir, err := os.MkdirTemp("", defaultTempDirPrefix+"input_")
		if err != nil {
			return "", cleanupFunc, fmt.Errorf("failed to create temp dir for GCS download: %w", err)
		}

		base := filepath.Base(fileURI)
		if base == "." || base == "/" {
			uid, _ := shortid.Generate()
			base = fmt.Sprintf("gcs_download_%s_%s", purpose, uid)
		}
		localPath = filepath.Join(tempDir, base)

		log.Printf("Downloading GCS file %s to temporary path %s for %s", fileURI, localPath, purpose)

		gcsErr := downloadFromGCS(ctx, fileURI, localPath)
		if gcsErr != nil {
			os.RemoveAll(tempDir)
			return "", cleanupFunc, fmt.Errorf("failed to download %s from GCS: %w", fileURI, gcsErr)
		}

		cleanupFunc = func() {
			log.Printf("Cleaning up temporary directory for GCS download: %s", tempDir)
			os.RemoveAll(tempDir)
		}
		return localPath, cleanupFunc, nil
	}

	if _, err := os.Stat(fileURI); os.IsNotExist(err) {
		return "", cleanupFunc, fmt.Errorf("local input file %s does not exist for %s", fileURI, purpose)
	}
	log.Printf("Using local input file %s for %s", fileURI, purpose)
	return fileURI, cleanupFunc, nil
}

func downloadFromGCS(ctx context.Context, gcsURI, localDestPath string) error {
	bucketName, objectName, err := parseGCSPath(gcsURI)
	if err != nil {
		return err
	}

	client, err := storage.NewClient(ctx)
	if err != nil {
		return fmt.Errorf("storage.NewClient: %w", err)
	}
	defer client.Close()

	rc, err := client.Bucket(bucketName).Object(objectName).NewReader(ctx)
	if err != nil {
		return fmt.Errorf("Object(%q).NewReader: %w", objectName, err)
	}
	defer rc.Close()

	f, err := os.Create(localDestPath)
	if err != nil {
		return fmt.Errorf("os.Create: %w", err)
	}
	defer f.Close()

	if _, err := io.Copy(f, rc); err != nil {
		return fmt.Errorf("io.Copy: %w", err)
	}
	log.Printf("Successfully downloaded %s to %s", gcsURI, localDestPath)
	return nil
}

func parseGCSPath(gcsURI string) (bucketName, objectName string, err error) {
	if !strings.HasPrefix(gcsURI, "gs://") {
		return "", "", fmt.Errorf("invalid GCS URI: must start with 'gs://', got %s", gcsURI)
	}
	trimmedURI := strings.TrimPrefix(gcsURI, "gs://")
	parts := strings.SplitN(trimmedURI, "/", 2)
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf("invalid GCS URI format: %s. Expected gs://bucket/object", gcsURI)
	}
	return parts[0], parts[1], nil
}

func handleOutputPreparation(desiredOutputFilename, defaultExt string) (tempLocalOutputFile string, finalOutputFilename string, cleanupFunc func(), err error) {
	cleanupFunc = func() {}

	tempDir, err := os.MkdirTemp("", defaultTempDirPrefix+"output_")
	if err != nil {
		return "", "", cleanupFunc, fmt.Errorf("failed to create temp dir for FFMpeg output: %w", err)
	}

	finalOutputFilename = desiredOutputFilename
	if finalOutputFilename == "" {
		uid, _ := shortid.Generate()
		finalOutputFilename = fmt.Sprintf("ffmpeg_output_%s.%s", uid, defaultExt)
	} else {
		currentExt := filepath.Ext(finalOutputFilename)
		if currentExt == "" {
			finalOutputFilename = finalOutputFilename + "." + defaultExt
		} else if strings.ToLower(currentExt) != "."+strings.ToLower(defaultExt) {
			log.Printf("Warning: output_file_name '%s' has extension '%s', but expected '%s'. Using original extension.", desiredOutputFilename, currentExt, defaultExt)
		}
	}

	tempLocalOutputFile = filepath.Join(tempDir, finalOutputFilename)

	cleanupFunc = func() {
		log.Printf("Cleaning up temporary output directory: %s", tempDir)
		os.RemoveAll(tempDir)
	}

	log.Printf("FFMpeg will write temporary output to: %s", tempLocalOutputFile)
	log.Printf("Final output filename will be: %s", finalOutputFilename)
	return tempLocalOutputFile, finalOutputFilename, cleanupFunc, nil
}

func processOutputAfterFFmpeg(ctx context.Context, ffmpegOutputActualPath, finalOutputFilename, outputLocalDir, outputGCSBucket string) (finalLocalPath string, finalGCSPath string, err error) {
	currentLocalPath := ffmpegOutputActualPath

	if outputLocalDir != "" {
		if errMkdir := os.MkdirAll(outputLocalDir, 0755); errMkdir != nil {
			return "", "", fmt.Errorf("failed to create specified output local directory %s: %w", outputLocalDir, errMkdir)
		}
		destLocalPath := filepath.Join(outputLocalDir, finalOutputFilename)
		log.Printf("Moving FFMpeg output from %s to %s", currentLocalPath, destLocalPath)
		if errRename := os.Rename(currentLocalPath, destLocalPath); errRename != nil {
			return "", "", fmt.Errorf("failed to move FFMpeg output to %s: %w", destLocalPath, errRename)
		}
		currentLocalPath = destLocalPath
		finalLocalPath = currentLocalPath
		log.Printf("Output saved to local directory: %s", finalLocalPath)
	} else {
		finalLocalPath = ffmpegOutputActualPath
		log.Printf("Output generated at temporary location: %s (will be cleaned up if not moved or uploaded)", finalLocalPath)
	}

	if outputGCSBucket != "" {
		if gcpProjectID == "" {
			return finalLocalPath, "", errors.New("PROJECT_ID not set, cannot upload to GCS")
		}
		if _, errStat := os.Stat(currentLocalPath); os.IsNotExist(errStat) {
			return finalLocalPath, "", fmt.Errorf("ffmpeg output file %s not found for GCS upload", currentLocalPath)
		}

		log.Printf("Uploading %s to GCS bucket %s as object %s", currentLocalPath, outputGCSBucket, finalOutputFilename)

		fileData, readErr := os.ReadFile(currentLocalPath)
		if readErr != nil {
			return finalLocalPath, "", fmt.Errorf("failed to read file %s for GCS upload: %w", currentLocalPath, readErr)
		}

		contentType := ""

		errUpload := uploadToGCS(ctx, outputGCSBucket, finalOutputFilename, contentType, fileData)
		if errUpload != nil {
			return finalLocalPath, "", fmt.Errorf("failed to upload to GCS (gs://%s/%s): %w", outputGCSBucket, finalOutputFilename, errUpload)
		}
		finalGCSPath = fmt.Sprintf("gs://%s/%s", outputGCSBucket, finalOutputFilename)
		log.Printf("Output uploaded to GCS: %s", finalGCSPath)
	}
	return finalLocalPath, finalGCSPath, nil
}

func uploadToGCS(ctx context.Context, bucketName, objectName, contentType string, data []byte) error {
	client, err := storage.NewClient(ctx)
	if err != nil {
		return fmt.Errorf("storage.NewClient: %w", err)
	}
	defer client.Close()

	obj := client.Bucket(bucketName).Object(objectName)
	wc := obj.NewWriter(ctx)
	if contentType != "" {
		wc.ContentType = contentType
	}

	if _, err := wc.Write(data); err != nil {
		wc.Close()
		return fmt.Errorf("Writer.Write: %w", err)
	}
	if err := wc.Close(); err != nil {
		return fmt.Errorf("Writer.Close: %w", err)
	}
	return nil
}

// Helper to safely get arguments from request
func getArguments(request mcp.CallToolRequest) (map[string]interface{}, error) {
	// request.Params is a struct and cannot be nil itself.
	// We check request.Params.Arguments, which is of type 'any' (interface{}) and can be nil.
	if request.Params.Arguments == nil {
		log.Println("Warning: request.Params.Arguments is nil, treating as empty arguments.")
		return make(map[string]interface{}), nil // Return empty map if Arguments is nil
	}

	argsMap, ok := request.Params.Arguments.(map[string]interface{})
	if !ok {
		log.Printf("Error: request.Params.Arguments is of type %T, not map[string]interface{}", request.Params.Arguments)
		return nil, fmt.Errorf("internal error: request arguments are not in the expected map format (type: %T)", request.Params.Arguments)
	}
	return argsMap, nil
}

func addConvertAudioTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_convert_audio_wav_to_mp3",
		mcp.WithDescription("Converts a WAV audio file to MP3 format using FFMpeg."),
		mcp.WithString("input_audio_uri", mcp.Required(), mcp.Description("URI of the input WAV audio file (local path or gs://).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output MP3 file (e.g., 'converted.mp3'). If omitted, a unique name is generated.")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output MP3 file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output MP3 file to.")),
	)
	s.AddTool(tool, ffmpegConvertAudioHandler)
}

func ffmpegConvertAudioHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	inputAudioURI, _ := argsMap["input_audio_uri"].(string)
	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")

	if inputAudioURI == "" {
		return mcp.NewToolResultError("Parameter 'input_audio_uri' is required."), nil
	}

	localInputAudio, inputCleanup, err := prepareInputFile(ctx, inputAudioURI, "input_audio")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input audio: %v", err)), nil
	}
	defer inputCleanup()

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, "mp3")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-i", localInputAudio, "-acodec", "libmp3lame", tempOutputFile)
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg conversion failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket)
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Audio conversion to MP3 completed in %v.", duration))
	if finalLocalPath != "" {
		if outputLocalDir != "" {
			messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
		} else {
			messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not uploaded).", finalLocalPath))
		}
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}

	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

func addCombineAudioVideoTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_combine_audio_and_video",
		mcp.WithDescription("Combines separate audio and video files into a single video file."),
		mcp.WithString("input_video_uri", mcp.Required(), mcp.Description("URI of the input video file (local path or gs://).")),
		mcp.WithString("input_audio_uri", mcp.Required(), mcp.Description("URI of the input audio file (local path or gs://).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output video file (e.g., 'combined.mp4').")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output video file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output video file to.")),
	)
	s.AddTool(tool, ffmpegCombineAudioVideoHandler)
}

func ffmpegCombineAudioVideoHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	inputVideoURI, _ := argsMap["input_video_uri"].(string)
	inputAudioURI, _ := argsMap["input_audio_uri"].(string)
	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")

	if inputVideoURI == "" || inputAudioURI == "" {
		return mcp.NewToolResultError("Parameters 'input_video_uri' and 'input_audio_uri' are required."), nil
	}

	localInputVideo, videoCleanup, err := prepareInputFile(ctx, inputVideoURI, "input_video")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input video: %v", err)), nil
	}
	defer videoCleanup()

	localInputAudio, audioCleanup, err := prepareInputFile(ctx, inputAudioURI, "input_audio")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input audio: %v", err)), nil
	}
	defer audioCleanup()

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, "mp4")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-i", localInputVideo, "-i", localInputAudio, "-map", "0", "-map", "1:a", "-c:v", "copy", "-shortest", tempOutputFile)
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg combine audio/video failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket)
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Audio and video combination completed in %v.", duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}

	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

func addOverlayImageOnVideoTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_overlay_image_on_video",
		mcp.WithDescription("Overlays an image onto a video at specified coordinates."),
		mcp.WithString("input_video_uri", mcp.Required(), mcp.Description("URI of the input video file (local path or gs://).")),
		mcp.WithString("input_image_uri", mcp.Required(), mcp.Description("URI of the input image file (local path or gs://).")),
		mcp.WithNumber("x_coordinate", mcp.DefaultNumber(0), mcp.Description("X coordinate for the overlay (top-left).")),
		mcp.WithNumber("y_coordinate", mcp.DefaultNumber(0), mcp.Description("Y coordinate for the overlay (top-left).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output video file (e.g., 'overlayed_video.mp4').")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output video file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output video file to.")),
	)
	s.AddTool(tool, ffmpegOverlayImageHandler)
}

func ffmpegOverlayImageHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	inputVideoURI, _ := argsMap["input_video_uri"].(string)
	inputImageURI, _ := argsMap["input_image_uri"].(string)
	xCoordFloat, _ := argsMap["x_coordinate"].(float64)
	yCoordFloat, _ := argsMap["y_coordinate"].(float64)
	xCoord := int(xCoordFloat)
	yCoord := int(yCoordFloat)

	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")

	if inputVideoURI == "" || inputImageURI == "" {
		return mcp.NewToolResultError("Parameters 'input_video_uri' and 'input_image_uri' are required."), nil
	}

	localInputVideo, videoCleanup, err := prepareInputFile(ctx, inputVideoURI, "input_video")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input video: %v", err)), nil
	}
	defer videoCleanup()

	localInputImage, imageCleanup, err := prepareInputFile(ctx, inputImageURI, "input_image")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input image: %v", err)), nil
	}
	defer imageCleanup()

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, "mp4")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	overlayFilter := fmt.Sprintf("[0:v][1:v]overlay=%d:%d", xCoord, yCoord)
	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-i", localInputVideo, "-i", localInputImage, "-filter_complex", overlayFilter, tempOutputFile)
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg overlay image failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket)
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Image overlay on video completed in %v.", duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}

	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

func addConcatenateMediaTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_concatenate_media_files",
		mcp.WithDescription("Concatenates multiple media files (videos or audios of the same type) into a single file."),
		mcp.WithArray("input_media_uris", mcp.Required(), mcp.Description("Array of URIs for the input media files (local paths or gs://). All files should be of a compatible type (e.g., all mp4 or all mp3).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output file (e.g., 'concatenated.mp4'). Extension should match input type.")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output file to.")),
	)
	s.AddTool(tool, ffmpegConcatenateMediaHandler)
}

func ffmpegConcatenateMediaHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	inputMediaURIsRaw, _ := argsMap["input_media_uris"].([]interface{})
	var inputMediaURIs []string
	for _, item := range inputMediaURIsRaw {
		if strItem, ok := item.(string); ok {
			inputMediaURIs = append(inputMediaURIs, strItem)
		}
	}

	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")

	if len(inputMediaURIs) == 0 {
		return mcp.NewToolResultError("Parameter 'input_media_uris' must be a non-empty array of strings."), nil
	}
	if len(inputMediaURIs) < 2 {
		return mcp.NewToolResultError("At least two media files are required for concatenation."), nil
	}

	var localInputFiles []string
	var inputCleanups []func()
	concatTempDir, err := os.MkdirTemp("", defaultTempDirPrefix+"concat_work_")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to create temp working directory for concatenation: %v", err)), nil
	}
	defer func() {
		log.Printf("Cleaning up concatenation working directory: %s", concatTempDir)
		os.RemoveAll(concatTempDir)
	}()

	for i, uri := range inputMediaURIs {
		localPath, cleanup, errPrep := prepareInputFile(ctx, uri, fmt.Sprintf("concat_input_%d", i))
		if errPrep != nil { // Changed err to errPrep to avoid conflict
			return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input media file %s: %v", uri, errPrep)), nil
		}
		inputCleanups = append(inputCleanups, cleanup)
		localInputFiles = append(localInputFiles, localPath)
	}
	defer func() {
		for _, c := range inputCleanups {
			c()
		}
	}()

	fileListPath := filepath.Join(concatTempDir, "mediafilelist.txt")
	fileListFile, err := os.Create(fileListPath)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to create media file list for FFMpeg: %v", err)), nil
	}
	for _, localFile := range localInputFiles {
		sanitizedPath := strings.ReplaceAll(localFile, "'", "'\\''")
		_, err = fileListFile.WriteString(fmt.Sprintf("file '%s'\n", sanitizedPath))
		if err != nil {
			fileListFile.Close()
			return mcp.NewToolResultError(fmt.Sprintf("Failed to write to media file list: %v", err)), nil
		}
	}
	fileListFile.Close()

	defaultOutputExt := "mp4"
	if len(localInputFiles) > 0 {
		ext := filepath.Ext(localInputFiles[0])
		if ext != "" && (strings.ToLower(ext) == ".mp4" || strings.ToLower(ext) == ".mov" || strings.ToLower(ext) == ".mkv" || strings.ToLower(ext) == ".webm") {
			defaultOutputExt = strings.ToLower(strings.TrimPrefix(ext, "."))
		} else if ext != "" && (strings.ToLower(ext) == ".mp3" || strings.ToLower(ext) == ".wav" || strings.ToLower(ext) == ".aac" || strings.ToLower(ext) == ".m4a") {
			defaultOutputExt = strings.ToLower(strings.TrimPrefix(ext, "."))
		}
	}
	if outputFileName != "" {
		userExt := filepath.Ext(outputFileName)
		if userExt != "" {
			defaultOutputExt = strings.ToLower(strings.TrimPrefix(userExt, "."))
		}
	}

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, defaultOutputExt)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-f", "concat", "-safe", "0", "-i", fileListPath, "-c", "copy", tempOutputFile)
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg concatenation failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket)
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Media concatenation completed in %v.", duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}

	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

func addAdjustVolumeTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_adjust_volume",
		mcp.WithDescription("Adjusts the volume of an audio file by a specified dB amount."),
		mcp.WithString("input_audio_uri", mcp.Required(), mcp.Description("URI of the input audio file (local path or gs://).")),
		mcp.WithNumber("volume_db_change", mcp.Required(), mcp.Description("Volume change in dB (e.g., -10 for -10dB, 5 for +5dB).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output audio file.")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output audio file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output audio file to.")),
	)
	s.AddTool(tool, ffmpegAdjustVolumeHandler)
}

func ffmpegAdjustVolumeHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	inputAudioURI, _ := argsMap["input_audio_uri"].(string)
	volumeDBChangeFloat, paramOK := argsMap["volume_db_change"].(float64) // Renamed ok to paramOK
	if !paramOK {
		return mcp.NewToolResultError("Parameter 'volume_db_change' is required and must be a number."), nil
	}
	volumeDBChange := int(volumeDBChangeFloat)

	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")

	if inputAudioURI == "" {
		return mcp.NewToolResultError("Parameter 'input_audio_uri' is required."), nil
	}

	localInputAudio, inputCleanup, err := prepareInputFile(ctx, inputAudioURI, "input_audio_vol")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input audio: %v", err)), nil
	}
	defer inputCleanup()

	defaultOutputExt := "mp3"
	inputExt := filepath.Ext(localInputAudio)
	if inputExt != "" {
		defaultOutputExt = strings.ToLower(strings.TrimPrefix(inputExt, "."))
	}
	if outputFileName != "" {
		userExt := filepath.Ext(outputFileName)
		if userExt != "" {
			defaultOutputExt = strings.ToLower(strings.TrimPrefix(userExt, "."))
		}
	}

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, defaultOutputExt)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	volumeFilter := fmt.Sprintf("volume=%ddB", volumeDBChange)
	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-i", localInputAudio, "-af", volumeFilter, tempOutputFile)
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg adjust volume failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket)
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Volume adjustment (%ddB) completed in %v.", volumeDBChange, duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}

	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

func addLayerAudioTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_layer_audio_files",
		mcp.WithDescription("Layers multiple audio files together (mixing)."),
		mcp.WithArray("input_audio_uris", mcp.Required(), mcp.Description("Array of URIs for the input audio files to layer (local paths or gs://).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output mixed audio file (e.g., 'layered_audio.mp3').")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output file to.")),
	)
	s.AddTool(tool, ffmpegLayerAudioHandler)
}

func ffmpegLayerAudioHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	inputAudioURIsRaw, _ := argsMap["input_audio_uris"].([]interface{})
	var inputAudioURIs []string
	for _, item := range inputAudioURIsRaw {
		if strItem, ok := item.(string); ok { // Renamed ok to strOK
			inputAudioURIs = append(inputAudioURIs, strItem)
		}
	}

	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")

	if len(inputAudioURIs) == 0 {
		return mcp.NewToolResultError("Parameter 'input_audio_uris' must be a non-empty array of strings."), nil
	}
	if len(inputAudioURIs) < 2 {
		return mcp.NewToolResultError("At least two audio files are typically required for layering."), nil
	}

	var localInputFiles []string
	var inputCleanups []func()
	layerTempDir, err := os.MkdirTemp("", defaultTempDirPrefix+"layer_work_")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to create temp working directory for layering: %v", err)), nil
	}
	defer func() {
		log.Printf("Cleaning up layering working directory: %s", layerTempDir)
		os.RemoveAll(layerTempDir)
	}()

	var ffmpegInputArgs []string
	for i, uri := range inputAudioURIs {
		localPath, cleanup, errPrep := prepareInputFile(ctx, uri, fmt.Sprintf("layer_input_%d", i)) // Renamed err to errPrep
		if errPrep != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input audio file %s: %v", uri, errPrep)), nil
		}
		inputCleanups = append(inputCleanups, cleanup)
		localInputFiles = append(localInputFiles, localPath)
		ffmpegInputArgs = append(ffmpegInputArgs, "-i", localPath)
	}
	defer func() {
		for _, c := range inputCleanups {
			c()
		}
	}()

	defaultOutputExt := "mp3"
	if len(localInputFiles) > 0 {
		ext := filepath.Ext(localInputFiles[0])
		if ext != "" {
			defaultOutputExt = strings.ToLower(strings.TrimPrefix(ext, "."))
		}
	}
	if outputFileName != "" {
		userExt := filepath.Ext(outputFileName)
		if userExt != "" {
			defaultOutputExt = strings.ToLower(strings.TrimPrefix(userExt, "."))
		}
	}

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, defaultOutputExt)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	amixFilter := fmt.Sprintf("amix=inputs=%d:duration=longest", len(localInputFiles))

	var commandArgs []string
	commandArgs = append(commandArgs, "-y")
	commandArgs = append(commandArgs, ffmpegInputArgs...)
	commandArgs = append(commandArgs, "-filter_complex", amixFilter, tempOutputFile)

	_, ffmpegErr := runFFmpegCommand(ctx, commandArgs...)
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg audio layering failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket)
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Audio layering of %d files completed in %v.", len(localInputFiles), duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}

	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}
