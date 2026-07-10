// Copyright 2026 Google LLC
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
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/ghchinoy/cloud-interactions-go"
	"github.com/mark3labs/mcp-go/mcp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
)

func omniVideoGenerationHandler(client *interactions.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "omni_video_generation")
	defer span.End()

	args := request.GetArguments()

	prompt, ok := args["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("prompt must be a non-empty string and is required"), nil
	}

	model, _ := args["model"].(string)
	if strings.TrimSpace(model) == "" {
		model = "gemini-omni-flash-preview"
	}

	mode, _ := args["mode"].(string)
	if strings.TrimSpace(mode) == "" {
		mode = "t2v"
	}

	aspectRatio, _ := args["aspect_ratio"].(string)
	if strings.TrimSpace(aspectRatio) == "" {
		aspectRatio = "16:9"
	}

	duration := 10
	if durFloat, ok := args["duration_seconds"].(float64); ok && durFloat > 0 {
		duration = int(durFloat)
	}

	prevID, _ := args["previous_interaction_id"].(string)
	outputDir, _ := args["output_directory"].(string)
	gcsBucket, _ := args["gcs_bucket_uri"].(string)
	if gcsBucket == "" && appConfig.GenmediaBucket != "" {
		gcsBucket = fmt.Sprintf("gs://%s/omni_outputs", appConfig.GenmediaBucket)
	}

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("model", model),
		attribute.String("mode", mode),
	)

	// Modify prompt with aspect ratio and duration if different from defaults
	modifiedPrompt := prompt
	var additions []string
	if aspectRatio != "16:9" {
		additions = append(additions, fmt.Sprintf("aspect ratio %s", aspectRatio))
	}
	if duration != 10 {
		additions = append(additions, fmt.Sprintf("duration %ds", duration))
	}
	if len(additions) > 0 {
		sep := ", "
		if strings.HasSuffix(prompt, ",") {
			sep = " "
		}
		modifiedPrompt = strings.TrimSpace(prompt) + sep + strings.Join(additions, ", ")
	}

	req := &interactions.InteractionRequest{
		Model: model,
	}

	if prevID != "" {
		req.PreviousInteractionID = prevID
		req.Input = []interactions.Content{
			{
				Type: "user_input",
				Content: []interactions.Part{
					{
						Type: "text",
						Text: modifiedPrompt,
					},
				},
			},
		}
	} else {
		var parts []interactions.Part
		parts = append(parts, interactions.Part{
			Type: "text",
			Text: modifiedPrompt,
		})

		if imgArgs, ok := args["images"].([]interface{}); ok {
			for _, imgArg := range imgArgs {
				if imgStr, ok := imgArg.(string); ok && strings.TrimSpace(imgStr) != "" {
					if strings.HasPrefix(imgStr, "gs://") {
						parts = append(parts, interactions.Part{
							Type:     "image",
							MimeType: inferMimeType(imgStr),
							URI:      imgStr,
						})
					} else {
						data, mime, err := readOrDownloadFile(ctx, imgStr)
						if err != nil {
							return mcp.NewToolResultError(fmt.Sprintf("failed to read image %s: %v", imgStr, err)), nil
						}
						parts = append(parts, interactions.Part{
							Type:     "image",
							MimeType: mime,
							Data:     base64.StdEncoding.EncodeToString(data),
						})
					}
				}
			}
		}

		if vidArgs, ok := args["videos"].([]interface{}); ok {
			for _, vidArg := range vidArgs {
				if vidStr, ok := vidArg.(string); ok && strings.TrimSpace(vidStr) != "" {
					if strings.HasPrefix(vidStr, "gs://") {
						parts = append(parts, interactions.Part{
							Type:     "video",
							MimeType: inferMimeType(vidStr),
							URI:      vidStr,
						})
					} else {
						data, mime, err := readOrDownloadFile(ctx, vidStr)
						if err != nil {
							return mcp.NewToolResultError(fmt.Sprintf("failed to read video %s: %v", vidStr, err)), nil
						}
						parts = append(parts, interactions.Part{
							Type:     "video",
							MimeType: mime,
							Data:     base64.StdEncoding.EncodeToString(data),
						})
					}
				}
			}
		}

		req.Input = parts
	}

	log.Printf("Calling Interactions API create with model=%s, prompt=%q", model, modifiedPrompt)
	startTime := time.Now()
	resp, err := client.Create(ctx, req)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Interactions API call failed: %v", err)), nil
	}
	log.Printf("Interactions API call completed in %v (ID: %s, Status: %s)", time.Since(startTime), resp.ID, resp.Status)

	var videoPart *interactions.Part
	for _, out := range resp.Outputs {
		for _, part := range out.Content {
			p := part
			if p.Type == "video" || p.Data != "" || (strings.HasPrefix(p.URI, "gs://") && strings.Contains(p.MimeType, "video")) {
				videoPart = &p
				break
			}
		}
		if videoPart != nil {
			break
		}
	}

	if videoPart == nil {
		for _, step := range resp.Steps {
			for _, part := range step.Content {
				p := part
				if p.Type == "video" || p.Data != "" || (strings.HasPrefix(p.URI, "gs://") && strings.Contains(p.MimeType, "video")) {
					videoPart = &p
					break
				}
			}
			if videoPart != nil {
				break
			}
		}
	}

	if videoPart == nil {
		return mcp.NewToolResultError("no video payload found in model output"), nil
	}

	var videoData []byte
	var gcsURI string
	if videoPart.Data != "" {
		videoData, err = base64.StdEncoding.DecodeString(videoPart.Data)
		if err != nil {
			return mcp.NewToolResultError(fmt.Sprintf("failed to decode base64 video data: %v", err)), nil
		}
	} else if videoPart.URI != "" {
		gcsURI = videoPart.URI
		videoData, _, err = readOrDownloadFile(ctx, videoPart.URI)
		if err != nil {
			log.Printf("Warning: failed to download video from URI %s: %v", videoPart.URI, err)
		}
	}

	var savedPath string
	if len(videoData) > 0 && gcsBucket != "" && gcsURI == "" {
		gcsURI, err = saveVideoToGCS(ctx, gcsBucket, videoData)
		if err != nil {
			log.Printf("Warning: failed to save video to GCS: %v", err)
		}
	}

	if len(videoData) > 0 && outputDir != "" {
		savedPath, err = saveVideoLocally(outputDir, videoData)
		if err != nil {
			return mcp.NewToolResultError(fmt.Sprintf("failed to save video locally: %v", err)), nil
		}
	}

	var resSb strings.Builder
	resSb.WriteString(fmt.Sprintf("Successfully generated video with interaction ID: %s\n", resp.ID))
	if gcsURI != "" {
		resSb.WriteString(fmt.Sprintf("GCS URI: %s\n", gcsURI))
	}
	if savedPath != "" {
		resSb.WriteString(fmt.Sprintf("Local file: %s\n", savedPath))
	}

	return mcp.NewToolResultText(resSb.String()), nil
}
