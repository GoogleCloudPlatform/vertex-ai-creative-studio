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

// NewHost connects to SEVERAL genmedia MCP servers at once, by their friendly
// nicknames, and returns an *mcp.MCPHost that aggregates their tools. It is the
// multi-server fan-out path Tier 2 uses: one host, many servers, exposed to the
// model through host.GetActiveTools so a single genkit.Generate turn can pick any
// tool across all of them (disambiguated in the system prompt, not by a rename
// layer — see tier2-producer for the in-prompt crosswalk).
//
// Each server is launched over stdio through bin/genmedia-launch via the shared
// StdioFor wiring, so the multi-server path reuses exactly the launch story the
// single-client path established. The MCP client namespaces every tool as
// "<nickname>_<toolName>" (e.g. "veo_veo_i2v"), which is what keeps four servers'
// tools distinct in one toolset.
//
// mcp.NewMCPHost logs and continues when an individual server fails to connect,
// so a healthy host can still be returned with some servers missing. Callers
// MUST confirm the tools they need are actually present (e.g. by checking
// host.GetActiveTools for the expected tool names) rather than assuming every
// requested server connected. The caller owns Disconnect for each server.
func NewHost(ctx context.Context, g *genkit.Genkit, servers ...string) (*mcp.MCPHost, error) {
	configs := make([]mcp.MCPServerConfig, 0, len(servers))
	for _, server := range servers {
		stdio, err := StdioFor(server)
		if err != nil {
			return nil, err
		}
		configs = append(configs, mcp.MCPServerConfig{
			Name: server,
			Config: mcp.MCPClientOptions{
				Name:  server,
				Stdio: stdio,
			},
		})
	}

	return mcp.NewMCPHost(g, mcp.MCPHostOptions{
		Name:       "genmedia-producer",
		MCPServers: configs,
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
