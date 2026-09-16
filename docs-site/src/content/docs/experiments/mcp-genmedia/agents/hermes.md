---
title: "MCP Servers for Genmedia x Hermes"
---

Use the MCP Servers for Genmedia with Nous Research's [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp). To install the server binaries, see [Installation](../index.md).

Config lives in `~/.hermes/config.yaml` under the top-level `mcp_servers:` key (secrets can also go in `~/.hermes/.env`).

```yaml
mcp_servers:
  veo:
    command: "mcp-veo-go"
    args: []
    env:
      GOOGLE_CLOUD_PROJECT: "YOUR_GOOGLE_CLOUD_PROJECT_ID"
      GENMEDIA_BUCKET: "gs://YOUR_GENMEDIA_BUCKET"
      MCP_SERVER_REQUEST_TIMEOUT: "60000"
  nanobanana:
    command: "mcp-nanobanana-go"
    args: []
    env:
      GOOGLE_CLOUD_PROJECT: "YOUR_GOOGLE_CLOUD_PROJECT_ID"
      GENMEDIA_BUCKET: "gs://YOUR_GENMEDIA_BUCKET"
```

Add the remaining servers (`gemini`, `chirp3`, `lyria`, `avtool`, `omni`) the same way.

Hermes also has CLI helpers: `hermes mcp` (interactive), `hermes mcp add <name>`, `hermes mcp install <name>`, and a runtime `/reload-mcp` command.

Migration note (from the Hermes docs): an `mcpServers` block in `~/.claude.json` maps to `mcp_servers` in Hermes' `config.yaml`.

Hermes is agentskills.io-compatible and stores user skills in `~/.hermes/skills/`, so the genmedia skills work there.

## Authentication

The genmedia MCP servers call Vertex AI from the server process, so each needs Google Cloud Application Default Credentials (ADC) and a project ID in its environment:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project)"
```

For service accounts, set `GOOGLE_APPLICATION_CREDENTIALS` to the key file path. `GENMEDIA_BUCKET` (a `gs://` URI) is optional and sets the default GCS output destination. Long-running models like Veo need a raised per-tool timeout.
