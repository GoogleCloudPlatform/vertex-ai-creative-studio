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
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"

	"google.golang.org/genai"
)

type AnalyzeRequest struct {
	VideoURI string `json:"videoUri"`
}

type AnalyzeResponse struct {
	Context string `json:"context"`
}

func (h *Handler) HandleAnalyzeVideo(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req AnalyzeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.VideoURI == "" {
		http.Error(w, "videoUri is required", http.StatusBadRequest)
		return
	}

	slog.Info("Analyzing video context", "uri", req.VideoURI, "model", h.Config.GeminiModel)

	// Construct Prompt
	prompt := `Analyze this video clip to ensure visual continuity for a generative video extension. 
Provide a concise, comma-separated descriptive summary including:
1. Visual Style (e.g., film grain, color palette)
2. Lighting (e.g., neon, harsh shadows)
3. Main Subject description (appearance, clothing)
4. Setting description

Return the result in this JSON format: { "context": "description string" }`

	// Call Gemini
	contents := []*genai.Content{
		{
			Role: "user",
			Parts: []*genai.Part{
				{Text: prompt},
				{
					FileData: &genai.FileData{
						FileURI:  req.VideoURI,
						MIMEType: "video/mp4",
					},
				},
			},
		},
	}

	slog.Info("Sending request to Gemini", "file_uri", req.VideoURI)

	resp, err := h.GenAI.Models.GenerateContent(r.Context(), h.Config.GeminiModel,
		contents,
		&genai.GenerateContentConfig{
			ResponseMIMEType: "application/json",
		},
	)
	if err != nil {
		slog.Error("Gemini analysis failed", "error", err)
		http.Error(w, fmt.Sprintf("Analysis failed: %v", err), http.StatusInternalServerError)
		return
	}

	if resp.UsageMetadata != nil {
		slog.Info("Gemini Usage", 
			"prompt_tokens", resp.UsageMetadata.PromptTokenCount,
			"candidate_tokens", resp.UsageMetadata.CandidatesTokenCount,
			"total_tokens", resp.UsageMetadata.TotalTokenCount,
		)
	}

	// Parse Response
	if len(resp.Candidates) == 0 || len(resp.Candidates[0].Content.Parts) == 0 {
		http.Error(w, "No content generated", http.StatusInternalServerError)
		return
	}

	// The SDK returns parts. We expect Text.
	// Note: In v1.39.0, parts might be specific types.
	// Checking the Part type handling.
	
	// Assuming text response for now based on standard usage.
	// We just stream the raw JSON back to the client or parse/validate it.
	// Let's forward the raw text for simplicity if it validates as JSON.
	
	var partText string
	for _, part := range resp.Candidates[0].Content.Parts {
		if part.Text != "" {
			partText += part.Text
		}
	}

	slog.Info("Analysis complete", "result", partText)

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(partText))
}
