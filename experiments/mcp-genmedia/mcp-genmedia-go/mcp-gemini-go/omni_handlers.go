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
//
// This file adds the Gemini Omni video-generation capability to the all-in-one
// mcp-gemini-go server. Omni (gemini-omni-flash-preview) is reachable only
// through the Vertex Interactions API, so the handler is a THIN wrapper around
// the shared common.GenerateOmniVideo / common.PersistMediaOutputs helpers — the
// identical calls mcp-omni-go's standalone handler makes. There is deliberately
// no second client on this binary: the Interactions path is fully encapsulated in
// mcp-common, so the gemini-go and omni-go request/response contracts cannot drift.

package main

import (
	"context"
	"fmt"
	"log"
	"math"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// maxOmniImages is the per-prompt image input limit (findings §1).
const maxOmniImages = 10

// maxInlineMediaBytes caps the size of a local media file that will be read into
// memory and base64-inlined into the interaction request. Larger files must be
// referenced by a gs:// URI instead (base64 inflates payloads ~33%, and the
// Interactions request body is bounded). 20 MiB is a deliberately conservative cap.
const maxInlineMediaBytes = 20 * 1024 * 1024

// omniVideoGenerationHandler generates one or more videos via the shared
// common.GenerateOmniVideo entry point and persists the returned MP4 bytes
// locally and/or to GCS (with best-effort V4 signed URLs), reusing the suite's
// shared common.PersistMediaOutputs helper. It mirrors mcp-omni-go's standalone
// handler exactly so the two servers never diverge.
func omniVideoGenerationHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "omni_video_generation")
	defer span.End()

	args := request.GetArguments()

	// --- Parameter Parsing ---
	prompt, ok := args["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("prompt must be a non-empty string and is required"), nil
	}
	prompt = strings.TrimSpace(prompt)

	outputDir := ""
	if dir, ok := args["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}

	// gcsBucketURI: explicit "gcs_bucket_uri" takes precedence, otherwise fall
	// back to the server-wide GENMEDIA_BUCKET default (mirrors the other tools).
	gcsBucketURI := ""
	if u, ok := args["gcs_bucket_uri"].(string); ok && strings.TrimSpace(u) != "" {
		gcsBucketURI = strings.TrimSpace(u)
	} else if appConfig != nil && appConfig.GenmediaBucket != "" {
		gcsBucketURI = appConfig.GenmediaBucket + "/omni_outputs/"
	}

	// Model resolution (honors an optional "model" arg / alias).
	modelArg, _ := args["model"].(string)
	model := common.DefaultOmniModel
	if resolved, found := common.ResolveOmniModel(modelArg, appConfig.AllowUnsafeModels); found {
		model = resolved.CanonicalName
	} else if strings.TrimSpace(modelArg) != "" {
		return mcp.NewToolResultError(fmt.Sprintf("unsupported model %q (set ALLOW_UNSAFE_MODELS=true to bypass)", modelArg)), nil
	}

	// Image / video inputs (local paths -> inline bytes; gs:// -> URI).
	// Enforce the image-count limit BEFORE parseMediaRefs reads any file into memory.
	if imgs, ok := args["images"].([]interface{}); ok && len(imgs) > maxOmniImages {
		return mcp.NewToolResultError(fmt.Sprintf("too many images: %d provided, the model accepts at most %d", len(imgs), maxOmniImages)), nil
	}
	images, err := parseMediaRefs(args["images"], "image")
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	videos, err := parseMediaRefs(args["videos"], "video")
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	// sample_count (default 1, clamped to the model max by the shared helper).
	sampleCount := 1
	if raw, present := args["sample_count"]; present {
		n, convErr := toInt(raw)
		if convErr != nil {
			return mcp.NewToolResultError(fmt.Sprintf("sample_count must be an integer: %v", convErr)), nil
		}
		if n >= 1 {
			sampleCount = n
		}
	}

	// temperature / top_p (optional; validated client-side, then sent in generation_config).
	temperature, err := parseOptionalFloatInRange(args, "temperature", 0.0, 2.0)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	topP, err := parseOptionalFloatInRange(args, "top_p", 0.0, 1.0)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("model", model),
		attribute.String("output_directory", outputDir),
		attribute.String("gcs_bucket_uri", gcsBucketURI),
		attribute.Int("images", len(images)),
		attribute.Int("videos", len(videos)),
		attribute.Int("sample_count", sampleCount),
	)

	// --- Shared Omni call ---
	log.Printf("Calling GenerateOmniVideo Model=%s sample_count=%d images=%d videos=%d", model, sampleCount, len(images), len(videos))
	startTime := time.Now()

	result, err := common.GenerateOmniVideo(ctx, appConfig, common.OmniParams{
		Prompt:      prompt,
		Model:       model,
		Images:      images,
		Videos:      videos,
		SampleCount: sampleCount,
		Temperature: temperature,
		TopP:        topP,
	})

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
	// Surface any thought/summary reasoning as a NOTE (not as a media output).
	if result.ThoughtSteps > 0 {
		fmt.Fprintf(&responseText, "\n\n[Note: model returned %d reasoning (thought) step(s).]", result.ThoughtSteps)
	}

	gentime := time.Now().Format("20060102150405")
	expiry := common.SignedURLExpiryFromEnv("OMNI_SIGNED_URL_EXPIRY_HOURS")
	var savedFiles []string

	for n, videoBytes := range result.Videos {
		mimeType := "video/mp4"
		if n < len(result.VideoMimeTypes) && result.VideoMimeTypes[n] != "" {
			mimeType = result.VideoMimeTypes[n]
		}

		persisted, err := common.PersistMediaOutputs(ctx, common.MediaArtifact{
			Data:     videoBytes,
			MimeType: mimeType,
			FileName: fmt.Sprintf("omni_%s_%d%s", gentime, n, videoExtForMimeType(mimeType)),
		}, outputDir, gcsBucketURI, expiry)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		if persisted.LocalPath != "" {
			savedFiles = append(savedFiles, persisted.LocalPath)
		}
		if persisted.GCSError != nil {
			log.Printf("failed to upload video to gs://%s/%s: %v", persisted.GCSBucket, persisted.GCSObject, persisted.GCSError)
			fmt.Fprintf(&responseText, "\n\n[Warning: failed to upload generated video to GCS: %v]", persisted.GCSError)
		}
		if persisted.GCSURI != "" {
			savedFiles = append(savedFiles, persisted.GCSURI)
		}
		if persisted.SignedURL != "" {
			fmt.Fprintf(&responseText, "\n\nSigned URL for %s (valid %s):\n%s", persisted.GCSObject, expiry, persisted.SignedURL)
		}
		if persisted.LocalPath == "" && persisted.GCSURI == "" {
			log.Println("Received video data but no output_directory or gcs_bucket_uri was specified/valid. Video not saved.")
		}
	}

	finalMessage := responseText.String()
	if len(savedFiles) > 0 {
		finalMessage += fmt.Sprintf("\n\nGenerated and saved %d video(s): %s", len(result.Videos), strings.Join(savedFiles, ", "))
	} else {
		finalMessage += fmt.Sprintf("\n\nGenerated %d video(s) but none were saved (set output_directory or gcs_bucket_uri).", len(result.Videos))
	}

	return &mcp.CallToolResult{Content: []mcp.Content{mcp.TextContent{Type: "text", Text: strings.TrimSpace(finalMessage)}}}, nil
}

// parseMediaRefs converts a tool argument (expected to be an array of strings,
// each a local file path or a gs:// URI) into common.OmniMediaRef values. Local
// paths are read into memory; gs:// URIs are passed through by reference. kind is
// "image" or "video" and is used only for error messages and MIME inference.
func parseMediaRefs(arg any, kind string) ([]common.OmniMediaRef, error) {
	if arg == nil {
		return nil, nil
	}
	list, ok := arg.([]interface{})
	if !ok {
		return nil, fmt.Errorf("%ss must be an array of strings", kind)
	}

	refs := make([]common.OmniMediaRef, 0, len(list))
	for _, item := range list {
		path, ok := item.(string)
		if !ok || strings.TrimSpace(path) == "" {
			return nil, fmt.Errorf("each %s entry must be a non-empty string (local path or gs:// URI)", kind)
		}
		path = strings.TrimSpace(path)
		mimeType := inferMediaMimeType(path)

		if strings.HasPrefix(path, "gs://") {
			refs = append(refs, common.OmniMediaRef{URI: path, MimeType: mimeType})
			continue
		}
		// Guard against inlining an oversized file: stat first, and reject files
		// above the inline cap with a hint to use a gs:// URI instead.
		info, statErr := os.Stat(path)
		if statErr != nil {
			return nil, fmt.Errorf("failed to read %s file %q: %w", kind, path, statErr)
		}
		if info.IsDir() {
			return nil, fmt.Errorf("%s path %q is a directory, not a file (expected a local media file or a gs:// URI)", kind, path)
		}
		if info.Size() > maxInlineMediaBytes {
			return nil, fmt.Errorf("%s file %q is %d bytes, exceeding the %d-byte inline limit; upload it to GCS and pass a gs:// URI instead", kind, path, info.Size(), maxInlineMediaBytes)
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("failed to read %s file %q: %w", kind, path, err)
		}
		refs = append(refs, common.OmniMediaRef{Data: data, MimeType: mimeType})
	}
	return refs, nil
}

// inferMediaMimeType infers an image/video MIME type from a file extension.
func inferMediaMimeType(path string) string {
	switch strings.ToLower(filepath.Ext(path)) {
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".png":
		return "image/png"
	case ".webp":
		return "image/webp"
	case ".gif":
		return "image/gif"
	case ".heic":
		return "image/heic"
	case ".heif":
		return "image/heif"
	case ".mp4":
		return "video/mp4"
	case ".mov":
		return "video/quicktime"
	case ".webm":
		return "video/webm"
	case ".mpeg", ".mpg":
		return "video/mpeg"
	case ".flv":
		return "video/x-flv"
	case ".wmv":
		return "video/wmv"
	case ".3gp", ".3gpp":
		return "video/3gpp"
	default:
		return "application/octet-stream"
	}
}

// videoExtForMimeType returns a file extension for a generated video MIME type,
// defaulting to ".mp4" (the Omni model's output format) for unknown or empty
// types so the saved filename's extension matches the actual bytes.
func videoExtForMimeType(mimeType string) string {
	switch strings.ToLower(strings.TrimSpace(mimeType)) {
	case "video/mp4":
		return ".mp4"
	case "video/webm":
		return ".webm"
	case "video/quicktime":
		return ".mov"
	case "video/mpeg":
		return ".mpeg"
	case "video/3gpp":
		return ".3gp"
	case "video/x-flv":
		return ".flv"
	case "video/wmv", "video/x-ms-wmv":
		return ".wmv"
	default:
		return ".mp4"
	}
}

// toInt coerces a JSON-decoded numeric tool argument to an int. MCP arguments
// arrive as float64 for JSON numbers, but integer literals may surface as int /
// int64 depending on the decoder, so those are accepted too. A non-integral
// float64 or any non-numeric value is rejected with an error.
func toInt(v any) (int, error) {
	switch n := v.(type) {
	case float64:
		if n != math.Trunc(n) {
			return 0, fmt.Errorf("expected an integer, got %v", n)
		}
		return int(n), nil
	case int:
		return n, nil
	case int64:
		return int(n), nil
	default:
		return 0, fmt.Errorf("expected a number, got %T", v)
	}
}

// toFloat64 coerces a JSON-decoded numeric tool argument to a float64. MCP
// arguments usually arrive as float64, but integer literals may surface as int /
// int64 depending on the decoder, so those are accepted too (mirrors toInt).
func toFloat64(v any) (float64, bool) {
	switch n := v.(type) {
	case float64:
		return n, true
	case float32:
		return float64(n), true
	case int:
		return float64(n), true
	case int64:
		return float64(n), true
	default:
		return 0, false
	}
}

// parseOptionalFloatInRange reads an optional float tool argument and validates
// it lies within [min, max]. Returns nil when the argument is absent.
func parseOptionalFloatInRange(args map[string]interface{}, key string, min, max float64) (*float32, error) {
	raw, present := args[key]
	if !present || raw == nil {
		return nil, nil
	}
	f, ok := toFloat64(raw)
	if !ok {
		return nil, fmt.Errorf("%s must be a number", key)
	}
	if f < min || f > max {
		return nil, fmt.Errorf("%s must be in the range [%.1f, %.1f], got %v", key, min, max, f)
	}
	v := float32(f)
	return &v, nil
}
