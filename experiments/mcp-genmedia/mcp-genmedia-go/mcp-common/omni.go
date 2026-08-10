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

// Package common provides shared utilities for the MCP Genmedia servers.

package common

import (
	"context"
	"encoding/base64"
	"fmt"
	"strings"
)

// omniVideoMimePrefix is the MIME prefix identifying a video output part.
const omniVideoMimePrefix = "video/"

// OmniParams are the inputs to a Gemini Omni video generation call. This phase
// exposes only the text prompt and model; image/video inputs and sampling controls
// are added in a later phase (design §5.1).
type OmniParams struct {
	// Prompt is the text prompt (required).
	Prompt string
	// Model is the resolved canonical model ID. If empty, the default Omni model
	// is used (see ResolveOmniModel).
	Model string
}

// OmniResult is the mapped output of a Gemini Omni video generation call.
type OmniResult struct {
	// Videos holds the decoded MP4 bytes for each returned video part (up to 3).
	Videos [][]byte
	// VideoMimeTypes holds the MIME type for each entry in Videos (index-aligned).
	VideoMimeTypes []string
	// Text is the concatenated model text output (excluding thought summaries).
	Text string
	// ThoughtSteps is the number of "thought" steps the model returned.
	ThoughtSteps int
	// SherlogLink is the optional captured x-goog-sherlog-link, if enabled.
	SherlogLink string
	// Status is the interaction status reported by the API (e.g. "completed").
	Status string
}

// GenerateOmniVideo is the single shared entry point both mcp-omni-go and (later)
// mcp-gemini-go call, so the request/response contract can never drift. It builds
// the Omni envelope (lowercase response_modalities), calls the Interactions client,
// and maps steps[] -> decoded MP4 bytes + text (design §7.2).
func GenerateOmniVideo(ctx context.Context, cfg *Config, p OmniParams) (*OmniResult, error) {
	if strings.TrimSpace(p.Prompt) == "" {
		return nil, fmt.Errorf("omni: prompt must be a non-empty string")
	}

	model := p.Model
	if strings.TrimSpace(model) == "" {
		model = DefaultOmniModel
	}

	client, err := NewInteractionsClient(ctx, cfg)
	if err != nil {
		return nil, err
	}

	req := buildOmniRequest(model, p)

	resp, err := client.Create(ctx, req)
	if err != nil {
		return nil, err
	}

	return mapOmniResponse(resp)
}

// buildOmniRequest constructs the Omni interaction envelope. response_modalities
// is lowercase ["text","video"] per the live wire (findings §3).
func buildOmniRequest(model string, p OmniParams) *InteractionRequest {
	return &InteractionRequest{
		Model:              model,
		ResponseModalities: []string{"text", "video"},
		Input: []InputItem{
			{
				Type: "user_input",
				Content: []Part{
					{Type: "text", Text: p.Prompt},
				},
			},
		},
		Store: false,
	}
}

// mapOmniResponse walks the interaction's steps[] (falling back to outputs[]),
// decoding video parts to bytes and concatenating text. It counts thought steps
// and is tolerant of both nested (Omni) and flat (Lyria-style) media shapes.
func mapOmniResponse(resp *InteractionResponse) (*OmniResult, error) {
	if resp == nil {
		return nil, fmt.Errorf("omni: nil interaction response")
	}

	result := &OmniResult{
		SherlogLink: resp.SherlogLink,
		Status:      resp.Status,
	}

	steps := resp.Steps
	if len(steps) == 0 {
		// Some interaction shapes place results in outputs[] rather than steps[].
		steps = resp.Outputs
	}

	var textBuilder strings.Builder
	for _, step := range steps {
		if step.Type == "thought" {
			result.ThoughtSteps++
			continue
		}

		// Nested content parts (Omni's model_output shape).
		for _, part := range step.Content {
			switch {
			case part.Type == "text" || part.Text != "":
				textBuilder.WriteString(part.Text)
			case strings.HasPrefix(part.MimeType, omniVideoMimePrefix) || part.Type == "video":
				decoded, err := base64.StdEncoding.DecodeString(part.Data)
				if err != nil {
					return nil, fmt.Errorf("omni: failed to decode base64 video data: %w", err)
				}
				result.Videos = append(result.Videos, decoded)
				result.VideoMimeTypes = append(result.VideoMimeTypes, partMimeOrDefault(part.MimeType))
			}
		}

		// Flat media at the step level (Lyria-style outputs[] parts).
		if len(step.Content) == 0 {
			switch {
			case step.Type == "text" || step.Text != "":
				textBuilder.WriteString(step.Text)
			case strings.HasPrefix(step.MimeType, omniVideoMimePrefix) || step.Type == "video":
				decoded, err := base64.StdEncoding.DecodeString(step.Data)
				if err != nil {
					return nil, fmt.Errorf("omni: failed to decode base64 video data: %w", err)
				}
				result.Videos = append(result.Videos, decoded)
				result.VideoMimeTypes = append(result.VideoMimeTypes, partMimeOrDefault(step.MimeType))
			}
		}
	}

	result.Text = textBuilder.String()

	if len(result.Videos) == 0 {
		return result, fmt.Errorf("omni: no video output found in interaction response (status=%q)", resp.Status)
	}
	return result, nil
}

// partMimeOrDefault returns the given MIME type or a video/mp4 default.
func partMimeOrDefault(mime string) string {
	if mime == "" {
		return "video/mp4"
	}
	return mime
}
