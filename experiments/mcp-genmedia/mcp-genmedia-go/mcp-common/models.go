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
	"fmt"
	"sort"
	"strings"
)

// --- Imagen Model Configuration ---

// ImagenModelInfo holds the details for a specific Imagen model.
type ImagenModelInfo struct {
	CanonicalName         string
	MaxImages             int32
	Aliases               []string
	SupportedAspectRatios []string
	SupportedImageSizes   []string
}

// SupportedImagenModels is the single source of truth for all supported Imagen models.
var SupportedImagenModels = map[string]ImagenModelInfo{
	"imagen-3.0-generate-001": {
		CanonicalName:         "imagen-3.0-generate-001",
		MaxImages:             4,
		Aliases:               []string{},
		SupportedAspectRatios: []string{"1:1", "3:4", "4:3", "9:16", "16:9"},
		SupportedImageSizes:   []string{},
	},
	"imagen-3.0-fast-generate-001": {
		CanonicalName:         "imagen-3.0-fast-generate-001",
		MaxImages:             4,
		Aliases:               []string{"Imagen 3 Fast"},
		SupportedAspectRatios: []string{"1:1", "3:4", "4:3", "9:16", "16:9"},
		SupportedImageSizes:   []string{},
	},
	"imagen-3.0-generate-002": {
		CanonicalName:         "imagen-3.0-generate-002",
		MaxImages:             4,
		Aliases:               []string{"Imagen 3"},
		SupportedAspectRatios: []string{"1:1", "3:4", "4:3", "9:16", "16:9"},
		SupportedImageSizes:   []string{},
	},
	"imagen-4.0-generate-001": {
		CanonicalName:         "imagen-4.0-generate-001",
		MaxImages:             4,
		Aliases:               []string{"Imagen 4", "Imagen4"},
		SupportedAspectRatios: []string{"1:1", "3:4", "4:3", "9:16", "16:9"},
		SupportedImageSizes:   []string{"1K", "2K"},
	},
	"imagen-4.0-fast-generate-001": {
		CanonicalName:         "imagen-4.0-fast-generate-001",
		MaxImages:             4,
		Aliases:               []string{"Imagen 4 Fast", "Imagen4 Fast"},
		SupportedAspectRatios: []string{"1:1", "3:4", "4:3", "9:16", "16:9"},
		SupportedImageSizes:   []string{"1K", "2K"},
	},
	"imagen-4.0-ultra-generate-001": {
		CanonicalName:         "imagen-4.0-ultra-generate-001",
		MaxImages:             1,
		Aliases:               []string{"Imagen 4 Ultra", "Imagen4 Ultra"},
		SupportedAspectRatios: []string{"1:1", "3:4", "4:3", "9:16", "16:9"},
		SupportedImageSizes:   []string{"1K", "2K"},
	},
}

var imagenAliasMap = make(map[string]string)

func init() {
	for canonicalName, info := range SupportedImagenModels {
		imagenAliasMap[strings.ToLower(canonicalName)] = canonicalName
		for _, alias := range info.Aliases {
			imagenAliasMap[strings.ToLower(alias)] = canonicalName
		}
	}
}

// ResolveImagenModel finds the canonical model name from a user-provided name or alias.
func ResolveImagenModel(modelInput string) (string, bool) {
	canonicalName, found := imagenAliasMap[strings.ToLower(modelInput)]
	return canonicalName, found
}

// BuildImagenModelDescription generates a formatted string for the tool description.
func BuildImagenModelDescription() string {
	var sb strings.Builder
	sb.WriteString("Model for image generation. Can be a full model ID or a common name. Supported models:\n")
	var sortedNames []string
	for name := range SupportedImagenModels {
		sortedNames = append(sortedNames, name)
	}
	sort.Strings(sortedNames)

	for _, name := range sortedNames {
		info := SupportedImagenModels[name]
		baseInfo := fmt.Sprintf("- *%s* (Max Images: %d, Ratios: %s)", info.CanonicalName, info.MaxImages, strings.Join(info.SupportedAspectRatios, ", "))
		sb.WriteString(baseInfo)
		if len(info.SupportedImageSizes) > 0 {
			sb.WriteString(fmt.Sprintf(" (Sizes: %s)", strings.Join(info.SupportedImageSizes, ", ")))
		}
		if len(info.Aliases) > 0 {
			sb.WriteString(fmt.Sprintf(" Aliases: *%s*", strings.Join(info.Aliases, "*, *")))
		}
		sb.WriteString("\n")
	}
	return sb.String()
}

// --- Veo Model Configuration ---

// VeoModelInfo holds the details for a specific Veo model.
type VeoModelInfo struct {
	CanonicalName           string
	Aliases                 []string
	DefaultDuration         int32
	SupportedDurations      []int32
	MaxVideos               int32
	SupportedAspectRatios   []string
	SupportsGenerateAudio   bool
	SupportsLastFrame       bool
	SupportsReferenceImages bool
}

// SupportedVeoModels is the single source of truth for all supported Veo models.
var SupportedVeoModels = map[string]VeoModelInfo{
	"veo-2.0-generate-001": {
		CanonicalName:         "veo-2.0-generate-001",
		Aliases:               []string{"Veo 2"},
		DefaultDuration:       8,
		SupportedDurations:    []int32{5, 6, 7, 8},
		MaxVideos:             4,
		SupportedAspectRatios: []string{"16:9", "9:16"},
		SupportsGenerateAudio: false,
	},
	"veo-2.0-generate-exp": {
		CanonicalName:         "veo-2.0-generate-exp",
		Aliases:               []string{"Veo 2.0 Exp"},
		DefaultDuration:       8,
		SupportedDurations:    []int32{5, 6, 7, 8},
		MaxVideos:             4,
		SupportedAspectRatios: []string{"16:9", "9:16"},
		SupportsGenerateAudio: false,
	},
	"veo-2.0-generate-preview": {
		CanonicalName:         "veo-2.0-generate-preview",
		Aliases:               []string{"Veo 2.0 Preview"},
		DefaultDuration:       8,
		SupportedDurations:    []int32{5, 6, 7, 8},
		MaxVideos:             4,
		SupportedAspectRatios: []string{"16:9", "9:16"},
		SupportsGenerateAudio: false,
	},

	// "veo-3.0-generate-preview": {
	// 	CanonicalName:         "veo-3.0-generate-preview",
	// 	Aliases:               []string{"Veo 3 preview"},
	// 	MinDuration:           8,
	// 	MaxDuration:           8,
	// 	DefaultDuration:       8,
	// 	MaxVideos:             2,
	// 	SupportedAspectRatios: []string{"16:9"},
	// },
	"veo-3.0-fast-generate-001": {
		CanonicalName:         "veo-3.0-fast-generate-001",
		Aliases:               []string{"Veo 3 Fast"},
		DefaultDuration:       8,
		SupportedDurations:    []int32{4, 6, 8},
		MaxVideos:             2,
		SupportedAspectRatios: []string{"16:9"},
		SupportsGenerateAudio: true,
	},

	// "veo-3.0-fast-generate-preview": {
	// 	CanonicalName:         "veo-3.0-fast-generate-preview",
	// 	Aliases:               []string{"Veo 3 Fast preview"},
	// 	MinDuration:           8,
	// 	MaxDuration:           8,
	// 	DefaultDuration:       8,
	// 	MaxVideos:             2,
	// 	SupportedAspectRatios: []string{"16:9"},
	// },
	"veo-3.1-generate-preview": {
		CanonicalName:           "veo-3.1-generate-preview",
		Aliases:                 []string{"Veo 3.1 preview"},
		SupportedDurations:      []int32{8},
		DefaultDuration:         8,
		MaxVideos:               2,
		SupportedAspectRatios:   []string{"16:9", "9:16"},
		SupportsLastFrame:       true,
		SupportsReferenceImages: true,
	},
	"veo-3.1-fast-generate-preview": {
		CanonicalName:           "veo-3.1-fast-generate-preview",
		Aliases:                 []string{"Veo 3.1 Fast preview"},
		SupportedDurations:      []int32{8},
		DefaultDuration:         8,
		MaxVideos:               2,
		SupportedAspectRatios:   []string{"16:9", "9:16"},
		SupportsLastFrame:       true,
		SupportsReferenceImages: false,
	},
}

var veoAliasMap = make(map[string]string)

func init() {
	for canonicalName, info := range SupportedVeoModels {
		veoAliasMap[strings.ToLower(canonicalName)] = canonicalName
		for _, alias := range info.Aliases {
			veoAliasMap[strings.ToLower(alias)] = canonicalName
		}
	}
}

// ResolveVeoModel finds the canonical model name from a user-provided name or alias.
func ResolveVeoModel(modelInput string) (string, bool) {
	canonicalName, found := veoAliasMap[strings.ToLower(modelInput)]
	return canonicalName, found
}

// BuildVeoModelDescription generates a formatted string for the tool description.
func BuildVeoModelDescription() string {
	var sb strings.Builder
	sb.WriteString("Model for video generation. Can be a full model ID or a common name. Supported models:\n")
	var sortedNames []string
	for name := range SupportedVeoModels {
		sortedNames = append(sortedNames, name)
	}
	sort.Strings(sortedNames)

	for _, name := range sortedNames {
		info := SupportedVeoModels[name]
		durationsStr := make([]string, len(info.SupportedDurations))
		for i, d := range info.SupportedDurations {
			durationsStr[i] = fmt.Sprintf("%d", d)
		}
		sb.WriteString(fmt.Sprintf("- *%s* (Durations: [%s]s, Max Videos: %d, Ratios: %s)",
			info.CanonicalName, strings.Join(durationsStr, ", "), info.MaxVideos, strings.Join(info.SupportedAspectRatios, ", ")))
		if len(info.Aliases) > 0 {
			sb.WriteString(fmt.Sprintf(" Aliases: *%s*", strings.Join(info.Aliases, "*, *")))
		}
		sb.WriteString("\n")
	}
	return sb.String()
}

// --- Gemini Model Configuration ---

// GeminiModelInfo holds the details for a specific Gemini model.
type GeminiModelInfo struct {
	CanonicalName string
	Aliases       []string
	Description   string
}

// SupportedGeminiModels is the single source of truth for all supported Gemini models.
var SupportedGeminiModels = map[string]GeminiModelInfo{
	"gemini-2.5-flash-image": {
		CanonicalName: "gemini-2.5-flash-image",
		Aliases:       []string{"nano-banana", "nano banana"},
		Description:   "Gemini 2.5 Flash Image generation model.",
	},
	"gemini-3-pro-preview": {
		CanonicalName: "gemini-3-pro-preview",
		Aliases:       []string{"Gemini 3 Pro"},
		Description:   "Gemini 3 Pro Preview model.",
	},
	"gemini-3-pro-image-preview": {
		CanonicalName: "gemini-3-pro-image-preview",
		Aliases:       []string{"Gemini 3 Pro Image", "nano banana pro", "nano-banana-pro"},
		Description:   "Gemini 3 Pro Image Preview model.",
	},
}

var geminiAliasMap = make(map[string]string)

func init() {
	for canonicalName, info := range SupportedGeminiModels {
		geminiAliasMap[strings.ToLower(canonicalName)] = canonicalName
		for _, alias := range info.Aliases {
			geminiAliasMap[strings.ToLower(alias)] = canonicalName
		}
	}
}

// ResolveGeminiModel finds the canonical model name from a user-provided name or alias.
func ResolveGeminiModel(modelInput string) (string, bool) {
	canonicalName, found := geminiAliasMap[strings.ToLower(modelInput)]
	return canonicalName, found
}

// BuildGeminiModelDescription generates a formatted string for the tool description.
func BuildGeminiModelDescription() string {
	var sb strings.Builder
	sb.WriteString("Model for content generation. Can be a full model ID or a common name. Supported models:\n")
	var sortedNames []string
	for name := range SupportedGeminiModels {
		sortedNames = append(sortedNames, name)
	}
	sort.Strings(sortedNames)

	for _, name := range sortedNames {
		info := SupportedGeminiModels[name]
		sb.WriteString(fmt.Sprintf("- *%s*: %s", info.CanonicalName, info.Description))
		if len(info.Aliases) > 0 {
			sb.WriteString(fmt.Sprintf(" (Aliases: *%s*)", strings.Join(info.Aliases, "*, *")))
		}
		sb.WriteString("\n")
	}
	return sb.String()
}
