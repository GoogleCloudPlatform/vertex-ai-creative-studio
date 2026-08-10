package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"log"

	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// generateAudioWithInteractions generates audio for newer Lyria models like
// lyria-3-pro-preview and lyria-3-clip-preview via the shared mcp-common
// Interactions seam (common.NewInteractionsClient + Create).
//
// The seam owns the transport concerns this function used to hand-roll: ADC via
// google.FindDefaultCredentials, the auto-refreshing oauth2 client, the
// x-goog-user-project header, and the global-only interactions URL. It
// additionally pins the "Api-Revision" header on every request — the single
// intended, benign wire delta versus the previous hand-rolled client (omni uses
// the same header successfully). This is a behavior-preserving consolidation:
// audio bytes, output filenames, result text, env-var handling, and sherlog
// capture are unchanged.
func generateAudioWithInteractions(ctx context.Context, modelID string, prompt string) ([]byte, string, error) {
	log.Printf("Using Interactions API for model: %s", modelID)

	client, err := common.NewInteractionsClient(ctx, appConfig)
	if err != nil {
		return nil, "", fmt.Errorf("failed to create interactions client: %w", err)
	}

	req := &common.InteractionRequest{
		Model: modelID,
		Input: []common.InputItem{{Type: "text", Text: prompt}},
		Store: false,
	}

	resp, err := client.Create(ctx, req)
	if err != nil {
		return nil, "", err
	}

	// Sherlog link is only surfaced when optional header capture is enabled,
	// preserving the pre-seam behavior (the seam always populates
	// resp.SherlogLink from the x-goog-sherlog-link response header).
	var sherlogLink string
	if appConfig.EnableOptionalHeaderCapture {
		sherlogLink = resp.SherlogLink
	}

	// Lyria returns flat audio ({type:"audio", mime_type, data}); the live shape
	// arrives in outputs[], but tolerate steps[] as well.
	audioBytes, found, err := extractFlatAudio(resp.Outputs)
	if !found && err == nil {
		audioBytes, found, err = extractFlatAudio(resp.Steps)
	}
	if err != nil {
		return nil, "", err
	}
	if !found {
		return nil, "", fmt.Errorf("no audio output found in response")
	}
	return audioBytes, sherlogLink, nil
}

// extractFlatAudio scans a flat outputs[]/steps[] slice for the first audio
// entry and returns its base64-decoded bytes. found is false when no audio
// entry is present; a present-but-undecodable entry surfaces the decode error
// verbatim, matching the pre-seam behavior.
func extractFlatAudio(steps []common.Step) ([]byte, bool, error) {
	for _, s := range steps {
		if s.Type == "audio" && s.Data != "" {
			decoded, err := base64.StdEncoding.DecodeString(s.Data)
			if err != nil {
				return nil, true, fmt.Errorf("failed to decode base64 audio data: %w", err)
			}
			return decoded, true, nil
		}
	}
	return nil, false, nil
}
