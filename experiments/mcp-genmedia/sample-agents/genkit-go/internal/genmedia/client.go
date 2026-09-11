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

// Package genmedia is the shared fan-out interface for the Genkit Go genmedia
// example series. Tier 0 establishes its shape — how you get an MCP client for
// a genmedia server (client.go / launch.go), how you inject the quirks the LLM
// cannot see (quirks.go) — and Tiers 1-3 consume it without breaking changes.
package genmedia

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/mcp"
)

// NewClient connects to a single genmedia MCP server by its friendly nickname
// (e.g. "nanobanana"), launching it over stdio through bin/genmedia-launch.
//
// It wraps mcp.NewGenkitMCPClient with the shared StdioFor launch wiring so no
// tier re-derives the launch story. The returned *mcp.GenkitMCPClient exposes
// GetActiveTools(ctx, g), lifecycle (Disconnect/Restart/...), and everything
// the later tiers need; the caller owns Disconnect.
//
// ctx and g are accepted for interface stability across the series (Tiers 1-3
// and the multi-server host path can use them); the single-client connect does
// not require them today.
func NewClient(ctx context.Context, g *genkit.Genkit, server string) (*mcp.GenkitMCPClient, error) {
	stdio, err := StdioFor(server)
	if err != nil {
		return nil, err
	}

	return mcp.NewGenkitMCPClient(mcp.MCPClientOptions{
		Name:  server,
		Stdio: stdio,
	})
}

// ToolRefs adapts the []ai.Tool returned by GetActiveTools into the []ai.ToolRef
// that genkit.Generate's ai.WithTools expects. Shared so every tier converts
// identically.
func ToolRefs(tools []ai.Tool) []ai.ToolRef {
	refs := make([]ai.ToolRef, 0, len(tools))
	for _, t := range tools {
		refs = append(refs, t)
	}
	return refs
}
