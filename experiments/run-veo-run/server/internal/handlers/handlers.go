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
	"net/http"

	"firebase.google.com/go/auth"
	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/run-veo-run/server/internal/config"
	"github.com/gorilla/websocket"
	"google.golang.org/genai"
)

type Handler struct {
	Config     *config.Config
	AuthClient *auth.Client
	GenAI      *genai.Client
}

func New(cfg *config.Config, authClient *auth.Client, genaiClient *genai.Client) *Handler {
	return &Handler{
		Config:     cfg,
		AuthClient: authClient,
		GenAI:      genaiClient,
	}
}

var Upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true }, // Allow all origins for dev
}

func (h *Handler) HandleConfig(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"geminiModel": h.Config.GeminiModel,
		"veoModel":    h.Config.VeoModel,
		"veoBucket":   h.Config.VeoBucket,
	})
}
