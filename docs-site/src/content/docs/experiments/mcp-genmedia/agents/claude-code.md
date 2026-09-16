---
title: "MCP Servers for Genmedia x Claude Code"
---

Use the MCP Servers for Genmedia with [Claude Code](https://docs.claude.com/en/docs/claude-code/overview). To install the server binaries, see [Installation](../index.md).

## Agent Plugin (recommended)

Claude Code can install the genmedia servers as an Agent Plugin from this repo, with no manual config. The plugin currently wires only the `nanobanana` image-generation server; the remaining servers will be added later.

```bash
# From a checkout of this repo, add the plugins directory as a marketplace:
claude plugin marketplace add /path/to/vertex-ai-creative-studio/experiments/agent_tools
claude plugin install genmedia@vaics-agent-tools
# Confirm the server connects (first run downloads the pinned release):
claude mcp list        # -> plugin:genmedia:nanobanana ... Connected
```

For the download-on-launch launcher, credentials, and current scope, see the [plugin README](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/blob/main/experiments/agent_tools/plugins/genmedia/README.md).

The plugin needs `GOOGLE_CLOUD_PROJECT` and ADC available (see [Authentication](#authentication)).

## Manual MCP configuration

To use the other servers today, add them manually. Both methods below follow the [Claude Code MCP docs](https://docs.claude.com/en/docs/claude-code/mcp).

Use the CLI:

```bash
claude mcp add --env GOOGLE_CLOUD_PROJECT=YOUR_GOOGLE_CLOUD_PROJECT_ID --env GENMEDIA_BUCKET=gs://YOUR_GENMEDIA_BUCKET veo -- mcp-veo-go
claude mcp add --env GOOGLE_CLOUD_PROJECT=YOUR_GOOGLE_CLOUD_PROJECT_ID --env GENMEDIA_BUCKET=gs://YOUR_GENMEDIA_BUCKET nanobanana -- mcp-nanobanana-go
```

Or add a project-scope `.mcp.json` at the repo root:

```json
{
  "mcpServers": {
    "veo": {
      "command": "mcp-veo-go",
      "args": [],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "YOUR_GOOGLE_CLOUD_PROJECT_ID",
        "GENMEDIA_BUCKET": "gs://YOUR_GENMEDIA_BUCKET",
        "MCP_SERVER_REQUEST_TIMEOUT": "60000"
      }
    },
    "nanobanana": {
      "command": "mcp-nanobanana-go",
      "args": [],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "YOUR_GOOGLE_CLOUD_PROJECT_ID",
        "GENMEDIA_BUCKET": "gs://YOUR_GENMEDIA_BUCKET"
      }
    }
  }
}
```

Run `claude mcp list` to show the servers with a connection status. Add the remaining servers (`gemini`, `chirp3`, `lyria`, `avtool`, `omni`) the same way.

## Authentication

The genmedia MCP servers call Vertex AI from the server process, so each needs Google Cloud Application Default Credentials (ADC) and a project ID in its environment:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project)"
```

For service accounts, set `GOOGLE_APPLICATION_CREDENTIALS` to the key file path. `GENMEDIA_BUCKET` (a `gs://` URI) is optional and sets the default GCS output destination. Long-running models like Veo need a raised per-tool timeout.
