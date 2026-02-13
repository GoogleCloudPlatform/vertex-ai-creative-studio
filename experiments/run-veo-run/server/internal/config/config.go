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

package config

import (
	"fmt"
	"os"
	"strconv"
)

type Config struct {
	ProjectID          string
	Port               string
	GeminiModel        string
	VeoModel           string
	VeoBucket          string
	Location           string
	GeminiLocation     string
	RateLimitPerMinute int
}

func Load() *Config {
	projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")
	if projectID == "" {
		projectID = "your-project-here" // Default
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	geminiModel := os.Getenv("GEMINI_MODEL")
	if geminiModel == "" {
		geminiModel = "gemini-3-flash-preview"
	}

	veoModel := os.Getenv("VEO_MODEL")
	if veoModel == "" {
		veoModel = "veo-3.1-fast-generate-preview"
	}

	veoBucket := os.Getenv("VEO_BUCKET")
	if veoBucket == "" {
		veoBucket = fmt.Sprintf("%s-assets", projectID) // Default bucket
	}

	location := os.Getenv("GOOGLE_CLOUD_LOCATION")
	if location == "" {
		location = "us-central1"
	}

	geminiLocation := os.Getenv("GEMINI_MODEL_LOCATION")
	if geminiLocation == "" {
		geminiLocation = location
	}

	rateLimitStr := os.Getenv("RATE_LIMIT_PER_MINUTE")
	rateLimit := 3 // Default safe limit (Global quota is ~10 RPM)
	if rateLimitStr != "" {
		if val, err := strconv.Atoi(rateLimitStr); err == nil {
			rateLimit = val
		}
	}

	return &Config{
		ProjectID:          projectID,
		Port:               port,
		GeminiModel:        geminiModel,
		VeoModel:           veoModel,
		VeoBucket:          veoBucket,
		Location:           location,
		GeminiLocation:     geminiLocation,
		RateLimitPerMinute: rateLimit,
	}
}
