---
title: "Agent Tools for Genmedia"
description: "The home for agent-facing tooling — MCP Servers and Agent Skills, and, over time, Agent Plugins — for Google Cloud's generative media APIs."
---

**Agent Tools for Genmedia** is the entry point for the agent-facing tooling that
lets AI agents and applications drive Google Cloud's generative media APIs (Gemini
Image, Gemini TTS, Veo, Chirp, Lyria, and audio/video compositing with AVTool).

It corresponds to the [`experiments/agent_tools/`](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/tree/main/experiments/agent_tools)
directory in the repository, which is the intended home for a consolidated set of
genmedia agent tooling: the existing **MCP Servers** and **Agent Skills**, and — over
time — **Agent Plugins**, gathered together in one place.

:::note[Scope today]
Right now this directory holds **one** artifact: a cross-server smoke test for the
media-generation MCP servers (described below). It does **not** move or replace the
existing [MCP Servers for Genmedia](/vertex-ai-creative-studio/experiments/mcp-genmedia) —
those stay where they are and continue to be the way you run the servers. Bringing
Agent Skills and Agent Plugins into this directory is future work, and the exact
approach is still being decided; nothing here should be read as a committed migration
plan or timeline.
:::

## MCP Servers for Genmedia

The Model Context Protocol (MCP) servers are the shipped, production way to give an
agent access to Google Cloud genmedia. Each server can be run independently, and
they cover image, video, speech, music, and audio/video compositing.

➡️ **See the [MCP Servers for Genmedia](/vertex-ai-creative-studio/experiments/mcp-genmedia)
overview** for the full list of servers, installation, configuration, and
per-server documentation.

## Agent Skills and Agent Plugins

The repository already ships a set of genmedia **Agent Skills** — markdown expertise
that teaches an agent how to use the MCP tools for complex workflows (for example
`genmedia-producer`, `genmedia-video-editor`, and `genmedia-audio-engineer`). These
are documented today under the MCP GenMedia section; see
[Agent Skills](/vertex-ai-creative-studio/experiments/mcp-genmedia/skills/).

Consolidating these skills — and packaging genmedia tooling as **Agent Plugins** —
into `experiments/agent_tools/` is a direction under exploration, not a decided plan
or a shipped layout. This page will grow to point at them as that work lands.

## The generate-and-verify smoke test

The first artifact to live in `experiments/agent_tools/` is
`smoke_generate_and_verify.sh`: a consolidated **generate-and-verify** smoke test
across the `mcp-genmedia-go` servers. For each server it fires one realistic
media-generation `tools/call` (via the external
[`mcptools`](https://github.com/f/mcptools) CLI) and then **verifies that a real
media artifact was produced** — a non-empty local file, or a GCS object that
`gcloud storage ls` can see.

This is intentionally stronger than each server's existing `verify.sh`, which only
does a `go build` + `tools/list` liveness check and never produces media.

### What it covers

| Server | Tool called | Notes |
|---|---|---|
| `mcp-gemini-go` | `gemini_image_generation` | |
| `mcp-nanobanana-go` | `nanobanana_image_generation` | |
| `mcp-veo-go` | `veo_t2v` | Video generation; can take minutes. Veo writes to GCS, so GCS mode is recommended for this server. |
| `mcp-lyria-go` | `lyria_generate_music` | |
| `mcp-chirp3-go` | `chirp_tts` | Local output only (no GCS output parameter). |
| `mcp-omni-go` | `omni_video_generation` | Video generation; can take minutes. |
| `mcp-avtool-go` | `ffmpeg_convert_audio_wav_to_mp3` | Chained off the chirp output (converts chirp's `.wav` to `.mp3`); `SKIP`ped if `ffmpeg` is unavailable or no chirp `.wav` was produced. |

`mcp-common` is a shared library, not a server, and is skipped.
`mcp-imagen-go` is **intentionally not covered**: Imagen models were shut down
across Google (including Vertex AI) on 2026-08-17 and return HTTP 404.

### Requirements

- [`mcptools`](https://github.com/f/mcptools):
  `go install github.com/f/mcptools/cmd/mcptools@latest` (ensure
  `$(go env GOPATH)/bin` is on your `PATH`).
- A `go` toolchain (each server is built before it is called) and `jq`.
- For GCS mode: `gcloud` with application-default credentials.
- `GOOGLE_CLOUD_PROJECT` must be set (required by every server).
- `ffmpeg` — only needed by `mcp-avtool-go`; if it is absent, avtool is `SKIP`ped
  (not failed) and every other server still runs.

### Usage

```bash
# Required
export GOOGLE_CLOUD_PROJECT=your-project

# Optional: write generated media to GCS and verify with `gcloud storage ls`.
# If unset, media is written locally under ./smoke_output/ instead.
export GENMEDIA_BUCKET=gs://your-bucket/some/prefix

# Run all servers
./smoke_generate_and_verify.sh

# Run a subset
./smoke_generate_and_verify.sh veo lyria chirp

# Increase the per-call timeout (default 600s) for slow video models
SMOKE_CALL_TIMEOUT=900 ./smoke_generate_and_verify.sh
```

A per-server summary table is printed at the end, and the exit code is non-zero if
any server fails to produce verified media (a `SKIP` does not fail the run).
Verification never trusts the JSON-RPC response alone — it confirms the artifact
actually exists (listing the GCS destination prefix, or checking for a non-empty
local file), which matters because some servers, notably `mcp-veo-go`, return a
`resource_link` content type that the `mcptools` CLI cannot render even though the
media is real.

For the complete, authoritative details, see the
[`experiments/agent_tools/README.md`](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/blob/main/experiments/agent_tools/README.md)
in the repository.
