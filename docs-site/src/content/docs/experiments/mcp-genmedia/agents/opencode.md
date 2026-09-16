---
title: "MCP Servers for Genmedia x Opencode"
---

Use the MCP Servers for Genmedia with [Opencode](https://opencode.ai/docs/mcp-servers/) (sst/opencode), which supports local (stdio) and remote MCP servers. To install the server binaries, see [Installation](../index.md).

Add servers under the top-level `mcp` key of `opencode.json` (project) or `~/.config/opencode/opencode.json` (global). Note that `command` is a JSON array (argv), the env key is `environment`, and each server needs `"type": "local"` and `"enabled": true`.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "veo": {
      "type": "local",
      "command": ["mcp-veo-go"],
      "enabled": true,
      "environment": {
        "GOOGLE_CLOUD_PROJECT": "YOUR_GOOGLE_CLOUD_PROJECT_ID",
        "GENMEDIA_BUCKET": "gs://YOUR_GENMEDIA_BUCKET",
        "MCP_SERVER_REQUEST_TIMEOUT": "60000"
      }
    },
    "nanobanana": {
      "type": "local",
      "command": ["mcp-nanobanana-go"],
      "enabled": true,
      "environment": {
        "GOOGLE_CLOUD_PROJECT": "YOUR_GOOGLE_CLOUD_PROJECT_ID",
        "GENMEDIA_BUCKET": "gs://YOUR_GENMEDIA_BUCKET"
      }
    }
  }
}
```

There is no CLI to add a stdio server, so edit the JSON. Add the remaining servers (`gemini`, `chirp3`, `lyria`, `avtool`, `omni`) the same way.

Opencode also reads Agent Skills from `.opencode/skills`, `.claude/skills`, and `.agents/skills`, so the genmedia skills work there too (see the [Skills docs](https://opencode.ai/docs/skills/)).

## Authentication

The genmedia MCP servers call Vertex AI from the server process, so each needs Google Cloud Application Default Credentials (ADC) and a project ID in its environment:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project)"
```

For service accounts, set `GOOGLE_APPLICATION_CREDENTIALS` to the key file path. `GENMEDIA_BUCKET` (a `gs://` URI) is optional and sets the default GCS output destination. Long-running models like Veo need a raised per-tool timeout.
