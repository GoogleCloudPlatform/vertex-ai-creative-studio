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

package genmedia

import (
	"fmt"
	"os"

	"github.com/firebase/genkit/go/plugins/mcp"
)

// Launch story (design Decision 1c). The genmedia server binaries reach this
// example the same way they reach the agent_tools plugin: via the pinned,
// SHA-256-double-verifying download-on-launch script bin/genmedia-launch.
// Genkit's mcp.StdioConfig{Command, Args, Env} maps one-to-one onto how
// agent_tools/plugins/genmedia/mcp.json invokes that launcher.

const (
	// DefaultReleaseTag is the pinned genmedia release the bundled launcher
	// verifies against. Keep in sync with bin/genmedia-launch (PINNED_TAG) and
	// the go.mod / README version pins.
	DefaultReleaseTag = "v3.18.0"

	// DefaultLauncher is the launcher path used when EnvLauncher is unset. Tiers
	// run from the module root (genkit start -- go run ./tierN-...), so the
	// relative path resolves against bin/genmedia-launch shipped in this module.
	DefaultLauncher = "./bin/genmedia-launch"

	// EnvLauncher overrides the launcher command. Set it to a bare binary name
	// (e.g. mcp-nanobanana-go) or a passthrough when the genmedia binaries are
	// already on PATH and the download-on-launch bridge is not wanted.
	EnvLauncher = "GENMEDIA_LAUNCH"

	// EnvReleaseTag overrides the genmedia release tag the launcher downloads.
	EnvReleaseTag = "GENMEDIA_RELEASE_TAG"

	// EnvCache overrides the launcher's writable per-user binary cache.
	EnvCache = "GENMEDIA_CACHE"

	// EnvProjectID and EnvGoogleCloudProject are the two accepted spellings for
	// the Google Cloud project the genmedia servers write to. Either is passed
	// through to the launched server.
	EnvProjectID          = "PROJECT_ID"
	EnvGoogleCloudProject = "GOOGLE_CLOUD_PROJECT"
)

// serverBinaries maps a friendly server nickname to the genmedia server binary
// the launcher execs. Tier 0 uses only "nanobanana"; the full set is listed so
// Tiers 1-3 (veo/lyria/avtool/...) consume the same interface without change.
var serverBinaries = map[string]string{
	"nanobanana": "mcp-nanobanana-go",
	"veo":        "mcp-veo-go",
	"gemini":     "mcp-gemini-go",
	"lyria":      "mcp-lyria-go",
	"chirp3":     "mcp-chirp3-go",
	"avtool":     "mcp-avtool-go",
	"omni":       "mcp-omni-go",
}

// ServerBinary resolves a friendly server nickname to its genmedia binary name.
func ServerBinary(server string) (string, error) {
	bin, ok := serverBinaries[server]
	if !ok {
		return "", fmt.Errorf("genmedia: unknown server %q", server)
	}
	return bin, nil
}

// LauncherPath returns the launcher command: the EnvLauncher override if set,
// otherwise DefaultLauncher (the bundled bin/genmedia-launch).
func LauncherPath() string {
	if v := os.Getenv(EnvLauncher); v != "" {
		return v
	}
	return DefaultLauncher
}

// releaseTag returns the genmedia release tag: the EnvReleaseTag override if
// set, otherwise DefaultReleaseTag.
func releaseTag() string {
	if v := os.Getenv(EnvReleaseTag); v != "" {
		return v
	}
	return DefaultReleaseTag
}

// StdioFor builds the stdio transport config that launches the given genmedia
// server through bin/genmedia-launch. It is the single source of the launch
// wiring shared by every tier.
//
// Args are "<binary> --transport stdio", matching agent_tools' mcp.json. Env
// carries only the genmedia-specific variables; the mcp-go stdio transport
// merges these onto os.Environ(), so PATH/HOME (needed by the launcher script)
// are inherited from the parent process.
func StdioFor(server string) (*mcp.StdioConfig, error) {
	bin, err := ServerBinary(server)
	if err != nil {
		return nil, err
	}

	env := []string{
		EnvReleaseTag + "=" + releaseTag(),
	}
	// Pass project + cache through only when present, so we never clobber an
	// inherited value with an empty string.
	for _, key := range []string{EnvProjectID, EnvGoogleCloudProject, EnvCache} {
		if v := os.Getenv(key); v != "" {
			env = append(env, key+"="+v)
		}
	}

	return &mcp.StdioConfig{
		Command: LauncherPath(),
		Args:    []string{bin, "--transport", "stdio"},
		Env:     env,
	}, nil
}
