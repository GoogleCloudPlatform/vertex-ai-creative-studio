

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
	CanonicalName         string
	Aliases               []string
	MinDuration           int32
	MaxDuration           int32
	DefaultDuration       int32
	MaxVideos             int32
	SupportedAspectRatios []string
}

// SupportedVeoModels is the single source of truth for all supported Veo models.
var SupportedVeoModels = map[string]VeoModelInfo{
	"veo-2.0-generate-001": {
		CanonicalName:         "veo-2.0-generate-001",
		Aliases:               []string{"Veo 2"},
		MinDuration:           5,
		MaxDuration:           8,
		DefaultDuration:       5,
		MaxVideos:             4,
		SupportedAspectRatios: []string{"16:9", "9:16"},
	},
	"veo-3.0-generate-preview": {
		CanonicalName:         "veo-3.0-generate-preview",
		Aliases:               []string{"Veo 3"},
		MinDuration:           8,
		MaxDuration:           8,
		DefaultDuration:       8,
		MaxVideos:             2,
		SupportedAspectRatios: []string{"16:9"},
	},
	"veo-3.0-fast-generate-preview": {
		CanonicalName:         "veo-3.0-fast-generate-preview",
		Aliases:               []string{"Veo 3 Fast"},
		MinDuration:           8,
		MaxDuration:           8,
		DefaultDuration:       8,
		MaxVideos:             2,
		SupportedAspectRatios: []string{"16:9"},
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
		sb.WriteString(fmt.Sprintf("- *%s* (Duration: %d-%ds, Max Videos: %d, Ratios: %s)",
			info.CanonicalName, info.MinDuration, info.MaxDuration, info.MaxVideos, strings.Join(info.SupportedAspectRatios, ", ")))
		if len(info.Aliases) > 0 {
			sb.WriteString(fmt.Sprintf(" Aliases: *%s*", strings.Join(info.Aliases, "*, *")))
		}
		sb.WriteString("\n")
	}
	return sb.String()
}
