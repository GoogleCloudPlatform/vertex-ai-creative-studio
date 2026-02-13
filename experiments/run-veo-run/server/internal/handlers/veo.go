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

package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"cloud.google.com/go/storage"
	"google.golang.org/genai"
)

type VeoRequest struct {
	Prompt            string   `json:"prompt"`
	VideoURI          string   `json:"videoUri,omitempty"`          // For extension (gs://...)
	MimeType          string   `json:"mimeType,omitempty"`          // e.g., video/mp4
	Model             string   `json:"model,omitempty"`             // Optional model override
	AspectRatio       string   `json:"aspectRatio,omitempty"`       // "16:9" or "9:16"
	ImageURI          string   `json:"imageUri,omitempty"`          // Start frame (gs://...)
	ImageMimeType     string   `json:"imageMimeType,omitempty"`     // e.g., image/png
	LastFrameURI      string   `json:"lastFrameUri,omitempty"`      // End frame (gs://...)
	LastFrameMimeType string   `json:"lastFrameMimeType,omitempty"` //
	RefImageURIs      []string `json:"refImageUris,omitempty"`      // Ingredient assets
	RefImageTypes     []string `json:"refImageTypes,omitempty"`     // e.g. "ASSET"
}

type VeoResponse struct {
	VideoURI  string `json:"videoUri"`  // Signed URL for playback
	SourceURI string `json:"sourceUri"` // Original gs:// URI (for extension)
}

// HandleGenerateVideo handles text-to-video requests
func (h *Handler) HandleGenerateVideo(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req VeoRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	model := req.Model
	if model == "" {
		model = h.Config.VeoModel
	}

	slog.Info("Generating video", "prompt", req.Prompt, "model", model, "aspect_ratio", req.AspectRatio, "image_uri", req.ImageURI, "last_frame", req.LastFrameURI, "ref_images", len(req.RefImageURIs))

	source := &genai.GenerateVideosSource{
		Prompt: req.Prompt,
	}

	if req.ImageURI != "" {
		mimeType := req.ImageMimeType
		if mimeType == "" {
			mimeType = "image/png"
		}
		source.Image = &genai.Image{
			GCSURI:   req.ImageURI,
			MIMEType: mimeType,
		}
	}

	gcsDest := fmt.Sprintf("gs://%s/outputs/", h.Config.VeoBucket)
	cfg := &genai.GenerateVideosConfig{
		OutputGCSURI: gcsDest,
	}

	// Aspect Ratio Handling
	if req.AspectRatio != "" {
		cfg.AspectRatio = req.AspectRatio
	}

	if req.LastFrameURI != "" {
				mimeType := req.LastFrameMimeType
				if mimeType == "" {
					mimeType = "image/png"
				}
				cfg.LastFrame = &genai.Image{
					GCSURI:   req.LastFrameURI,
					MIMEType: mimeType,
				}
			}
		
			if len(req.RefImageURIs) > 0 {
				var refs []*genai.VideoGenerationReferenceImage
				for i, uri := range req.RefImageURIs {
					refTypeStr := "ASSET"
					if i < len(req.RefImageTypes) {
						refTypeStr = req.RefImageTypes[i]
					}
					
					// Map string to Enum
					var refType genai.VideoGenerationReferenceType
					if refTypeStr == "STYLE" {
						refType = genai.VideoGenerationReferenceTypeStyle
					} else {
						refType = genai.VideoGenerationReferenceTypeAsset
					}
		
					refs = append(refs, &genai.VideoGenerationReferenceImage{
						Image: &genai.Image{
							GCSURI:   uri,
							MIMEType: "image/png", // Simplification
						},
						ReferenceType: refType,
					})
				}
				cfg.ReferenceImages = refs
			}
		
			op, err := h.GenAI.Models.GenerateVideosFromSource(r.Context(), model, source, cfg)
			if err != nil {		slog.Error("Failed to start video generation", "error", err)
		http.Error(w, fmt.Sprintf("Generation failed: %v", err), http.StatusInternalServerError)
		return
	}

	slog.Info("Video generation started", "op", op.Name)

	resp, err := h.waitForOperation(r.Context(), op)
	if err != nil {
		slog.Error("Video generation failed during wait", "error", err)
		http.Error(w, fmt.Sprintf("Generation failed: %v", err), http.StatusInternalServerError)
		return
	}

	if len(resp.GeneratedVideos) == 0 {
		http.Error(w, "No video generated", http.StatusInternalServerError)
		return
	}

	videoGS := resp.GeneratedVideos[0].Video.URI
	slog.Info("Video generation complete", "uri", videoGS)

	signedURL, err := h.signURL(r.Context(), videoGS)
	if err != nil {
		slog.Warn("Failed to sign URL (playback might fail locally without SA impersonation)", "error", err)
		// Fallback: Use the original GS URI, though it won't play in standard browsers
		signedURL = videoGS
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(VeoResponse{
		VideoURI:  signedURL,
		SourceURI: videoGS,
	})
}

// HandleExtendVideo handles video-to-video extension
func (h *Handler) HandleExtendVideo(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req VeoRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.VideoURI == "" {
		http.Error(w, "videoUri is required for extension", http.StatusBadRequest)
		return
	}

	model := req.Model
	if model == "" {
		model = h.Config.VeoModel
	}

	slog.Info("Extending video", "prompt", req.Prompt, "source", req.VideoURI, "model", model)

	source := &genai.GenerateVideosSource{
		Prompt: req.Prompt,
		Video: &genai.Video{
			URI:      req.VideoURI,
			MIMEType: req.MimeType,
		},
	}

	if source.Video.MIMEType == "" {
		source.Video.MIMEType = "video/mp4" // Default
	}

	gcsDest := fmt.Sprintf("gs://%s/extensions/", h.Config.VeoBucket)
	cfg := &genai.GenerateVideosConfig{
		OutputGCSURI: gcsDest,
	}

	op, err := h.GenAI.Models.GenerateVideosFromSource(r.Context(), model, source, cfg)
	if err != nil {
		slog.Error("Failed to start video extension", "error", err)
		http.Error(w, fmt.Sprintf("Extension failed: %v", err), http.StatusInternalServerError)
		return
	}

	resp, err := h.waitForOperation(r.Context(), op)
	if err != nil {
		slog.Error("Video extension failed during wait", "error", err)
		http.Error(w, fmt.Sprintf("Extension failed: %v", err), http.StatusInternalServerError)
		return
	}

	if len(resp.GeneratedVideos) == 0 {
		http.Error(w, "No video extended", http.StatusInternalServerError)
		return
	}

	videoGS := resp.GeneratedVideos[0].Video.URI
	slog.Info("Video extension complete", "uri", videoGS)

	signedURL, err := h.signURL(r.Context(), videoGS)
	if err != nil {
		slog.Warn("Failed to sign URL (playback might fail locally without SA impersonation)", "error", err)
		// Fallback: Use the original GS URI, though it won't play in standard browsers
		signedURL = videoGS
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(VeoResponse{
		VideoURI:  signedURL,
		SourceURI: videoGS,
	})
}

func (h *Handler) waitForOperation(ctx context.Context, op *genai.GenerateVideosOperation) (*genai.GenerateVideosResponse, error) {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	// Timeout after 5 minutes
	ctx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()

	for {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-ticker.C:
			// Poll the operation
			latestOp, err := h.GenAI.Operations.GetVideosOperation(ctx, op, nil)
			if err != nil {
				return nil, fmt.Errorf("failed to poll operation: %w", err)
			}
			if latestOp.Done {
				if latestOp.Error != nil {
					return nil, fmt.Errorf("operation failed: %v", latestOp.Error)
				}
				return latestOp.Response, nil
			}
		}
	}
}

func (h *Handler) signURL(ctx context.Context, gcsURI string) (string, error) {
	// gcsURI format: gs://bucket/object
	if !strings.HasPrefix(gcsURI, "gs://") {
		return "", fmt.Errorf("invalid GCS URI: %s", gcsURI)
	}

	parts := strings.SplitN(strings.TrimPrefix(gcsURI, "gs://"), "/", 2)
	if len(parts) != 2 {
		return "", fmt.Errorf("invalid GCS URI format")
	}
	bucketName := parts[0]
	objectName := parts[1]

	client, err := storage.NewClient(ctx)
	if err != nil {
		return "", fmt.Errorf("storage client creation failed: %w", err)
	}
	defer client.Close()

	// 15 minute expiration
	opts := &storage.SignedURLOptions{
		Scheme:  storage.SigningSchemeV4,
		Method:  "GET",
		Expires: time.Now().Add(15 * time.Minute),
	}

	u, err := client.Bucket(bucketName).SignedURL(objectName, opts)
	if err != nil {
		return "", fmt.Errorf("sign failed: %w", err)
	}
	return u, nil
}
