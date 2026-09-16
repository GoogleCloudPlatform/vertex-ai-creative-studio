---
title: "MCP Servers for Genmedia x DeepSeek Harness (dsh)"
---

Use the MCP Servers for Genmedia with the DeepSeek harness ([deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/mcp-memory.md), `dsh`), a Cordis "everything is a plugin" harness in developer preview. It supports MCP servers (stdio and streamable-http) through its first-party plugin `@deepseek-ai/dsh-mcp-client`. To install the server binaries, see [Installation](../index.md).

This is a developer preview, so expect breaking changes.

Add a server as a Cordis plugin entry in a patch file (`$DSH_HOME/cordis.patch.yml`, where `$DSH_HOME` defaults to `~/.dsh`), or apply a patch ad hoc with `dsh web --patch <file>`.

```yaml
- id: veo
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: veo
    transport: stdio
    command: mcp-veo-go
    args: []
    env:
      GOOGLE_CLOUD_PROJECT: YOUR_GOOGLE_CLOUD_PROJECT_ID
      GENMEDIA_BUCKET: gs://YOUR_GENMEDIA_BUCKET
- id: nanobanana
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: nanobanana
    transport: stdio
    command: mcp-nanobanana-go
    args: []
    env:
      GOOGLE_CLOUD_PROJECT: YOUR_GOOGLE_CLOUD_PROJECT_ID
      GENMEDIA_BUCKET: gs://YOUR_GENMEDIA_BUCKET
```

Tools appear as `mcp__<serverName>__<tool>`. Add the remaining servers (`gemini`, `chirp3`, `lyria`, `avtool`, `omni`) the same way.

> **Important:** The dsh stdio bridge strips ambient variables whose names look like credentials, and all `DSH_*` variables, before launching the child process. You MUST put `GOOGLE_CLOUD_PROJECT`, `GENMEDIA_BUCKET`, and any credential path in the entry's `config.env` rather than relying on your shell environment.

dsh has native `SKILL.md` discovery via `@deepseek-ai/dsh-skill-filesystem`, which scans project and user roots plus `~/.dsh` and `~/.agents`, so the genmedia skills work there.

## Authentication

The genmedia MCP servers call Vertex AI from the server process, so each needs Google Cloud Application Default Credentials (ADC) and a project ID. For dsh, set these in the entry's `config.env`, not your shell:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project)"
```

For service accounts, set `GOOGLE_APPLICATION_CREDENTIALS` to the key file path (again, in `config.env` for dsh). `GENMEDIA_BUCKET` (a `gs://` URI) is optional and sets the default GCS output destination. Long-running models like Veo need a raised per-tool timeout.
