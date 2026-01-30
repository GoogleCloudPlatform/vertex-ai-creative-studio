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
	"log/slog"
	"net/http"
	"os"
	"time"

	firebase "firebase.google.com/go"
	"firebase.google.com/go/auth"
	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/run-veo-run/server/internal/config"
	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/run-veo-run/server/internal/handlers"
	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/run-veo-run/server/internal/logging"
	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/run-veo-run/server/internal/security"
	"google.golang.org/genai"
)

func main() {
	// 1. Initialize Logging
	logging.Init()

	// 2. Load Configuration
	cfg := config.Load()

	// 3. Initialize Firebase (Optional)
	ctx := context.Background()
	app, err := firebase.NewApp(ctx, nil)
	var authClient *auth.Client
	if err != nil {
		slog.Warn("Firebase init failed (auth might not work)", "error", err)
	} else {
		client, err := app.Auth(ctx)
		if err != nil {
			slog.Warn("Firebase Auth client init failed", "error", err)
		} else {
			authClient = client
		}
	}

	// 4. Initialize GenAI Client
	genaiClient, err := genai.NewClient(ctx, &genai.ClientConfig{
		Project:  cfg.ProjectID,
		Location: cfg.GeminiLocation,
		Backend:  genai.BackendVertexAI,
	})
	if err != nil {
		slog.Error("Failed to create GenAI client", "error", err)
		os.Exit(1)
	}

	// 5. Initialize Handlers
	h := handlers.New(cfg, authClient, genaiClient)

	// Rate Limiter
	rl := security.NewRateLimiter(cfg.RateLimitPerMinute, time.Minute)

	// 6. Setup Routes
	http.HandleFunc("/api/config", h.HandleConfig)
	http.HandleFunc("/api/veo/generate", rl.Middleware(h.HandleGenerateVideo))
	http.HandleFunc("/api/veo/extend", rl.Middleware(h.HandleExtendVideo))
	http.HandleFunc("/api/gemini/analyze", h.HandleAnalyzeVideo)
	http.HandleFunc("/api/upload", h.HandleUpload)
	http.Handle("/", http.FileServer(http.Dir("./dist")))

	// 7. Start Server
	slog.Info("Server starting", "port", cfg.Port)
	if err := http.ListenAndServe(":"+cfg.Port, nil); err != nil {
		slog.Error("Server failed", "error", err)
		os.Exit(1)
	}
}
