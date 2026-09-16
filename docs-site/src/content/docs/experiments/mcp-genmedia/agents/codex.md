---
title: "MCP Servers for Genmedia x OpenAI Codex"
---

Use the MCP Servers for Genmedia with the OpenAI Codex CLI, which supports MCP servers as a first-class feature (not experimental). The source of truth is the [Codex MCP docs](https://developers.openai.com/codex/mcp). To install the server binaries, see [Installation](../index.md).

Config lives in `~/.codex/config.toml`, with project overrides in `.codex/config.toml` for trusted projects.

Use the CLI:

```bash
codex mcp add veo --env GOOGLE_CLOUD_PROJECT=YOUR_GOOGLE_CLOUD_PROJECT_ID --env GENMEDIA_BUCKET=gs://YOUR_GENMEDIA_BUCKET -- mcp-veo-go
codex mcp add nanobanana --env GOOGLE_CLOUD_PROJECT=YOUR_GOOGLE_CLOUD_PROJECT_ID --env GENMEDIA_BUCKET=gs://YOUR_GENMEDIA_BUCKET -- mcp-nanobanana-go
```

Or edit `~/.codex/config.toml` directly. Note the env is a nested table, `[mcp_servers.<name>.env]`:

```toml
[mcp_servers.veo]
command = "mcp-veo-go"
args = []

[mcp_servers.veo.env]
GOOGLE_CLOUD_PROJECT = "YOUR_GOOGLE_CLOUD_PROJECT_ID"
GENMEDIA_BUCKET = "gs://YOUR_GENMEDIA_BUCKET"

[mcp_servers.nanobanana]
command = "mcp-nanobanana-go"
args = []

[mcp_servers.nanobanana.env]
GOOGLE_CLOUD_PROJECT = "YOUR_GOOGLE_CLOUD_PROJECT_ID"
GENMEDIA_BUCKET = "gs://YOUR_GENMEDIA_BUCKET"
```

Run `codex mcp list` to confirm. Add the remaining servers (`gemini`, `chirp3`, `lyria`, `avtool`, `omni`) the same way.

Codex's default per-tool timeout is 60s and its server startup timeout is 10s. For Veo and other long jobs, raise `tool_timeout_sec` on the server table.

## Authentication

The genmedia MCP servers call Vertex AI from the server process, so each needs Google Cloud Application Default Credentials (ADC) and a project ID in its environment:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project)"
```

For service accounts, set `GOOGLE_APPLICATION_CREDENTIALS` to the key file path. `GENMEDIA_BUCKET` (a `gs://` URI) is optional and sets the default GCS output destination. Long-running models like Veo need a raised per-tool timeout.
