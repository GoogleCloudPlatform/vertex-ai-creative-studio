# agent_tools

This directory is the intended future home for a consolidated set of agent
tooling for the `vertex-ai-creative-studio` project — MCP Servers (existing,
under `../mcp-genmedia/`), Agent Skills, and Agent Plugins. It starts small:
its first artifact is a cross-server smoke test for the media-generation MCP
servers.

> **Scope note:** This directory does **not** move or replace the existing
> `../mcp-genmedia/` servers. It only adds new agent-facing tooling alongside
> them. The broader migration is future work.

## `smoke_generate_and_verify.sh`

A consolidated **generate-and-verify** smoke test across the eight
`mcp-genmedia-go` servers. For each server it fires one realistic
media-generation `tools/call` (via the external
[`mcptools`](https://github.com/f/mcptools) CLI) and then **verifies that a
real media artifact was produced** — a non-empty local file, or a GCS object
that `gcloud storage ls` can see.

This is intentionally stronger than each server's existing `verify.sh`, which
only does a `go build` + `tools/list` liveness check and never produces media.

### What it covers

| Server | Tool called | Notes |
|---|---|---|
| `mcp-gemini-go` | `gemini_image_generation` | |
| `mcp-nanobanana-go` | `nanobanana_image_generation` | |
| `mcp-veo-go` | `veo_t2v` | Video generation; can take minutes. Called with an explicit `model` (`veo-3.1-fast-generate-001`) — with no model the server falls back to `veo-2.0-generate-001`, which rejects the default `generate_audio=true`. Veo writes to GCS, so **GCS mode is recommended** for this server. |
| `mcp-lyria-go` | `lyria_generate_music` | |
| `mcp-chirp3-go` | `chirp_tts` | Local output only (no GCS output param). |
| `mcp-omni-go` | `omni_video_generation` | Video generation; can take minutes. |
| `mcp-avtool-go` | `ffmpeg_convert_audio_wav_to_mp3` | avtool transforms existing media, so this call is **chained off** the chirp output (converts chirp's `.wav` to `.mp3`). `SKIP`ped with a clear reason if `ffmpeg` is not installed or no chirp `.wav` is available. |

`mcp-common` is a shared library, not a server, and is skipped.

`mcp-imagen-go` is **intentionally not covered**: Imagen models were shut down
across Google (including Vertex AI) on 2026-08-17 and return HTTP 404, so there
is no value in smoke-testing them going forward.

### Requirements

- [`mcptools`](https://github.com/f/mcptools):
  `go install github.com/f/mcptools/cmd/mcptools@latest`
  (ensure `$(go env GOPATH)/bin` is on your `PATH`).
- `go` toolchain (each server is built before it is called).
- `jq`.
- For GCS mode: `gcloud` with application-default credentials.
- `GOOGLE_CLOUD_PROJECT` must be set (required by every server).
- `ffmpeg` — only needed by `mcp-avtool-go`. If it is absent, avtool is
  `SKIP`ped (not failed); every other server runs normally.

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

### Output

- Generated media goes to GCS (`$GENMEDIA_BUCKET`) or to
  `./smoke_output/<server>/` (gitignored).
- Each server's raw `tools/call` response is saved to
  `./smoke_output/<server>/response.json` for debugging.
- A per-server summary table is printed at the end:

  ```
  SERVER               TOOL                             RESULT         ARTIFACT / DETAIL
  mcp-gemini-go        gemini_image_generation          PASS           gs://.../smoke_gemini.png
  mcp-veo-go           veo_t2v                          PASS           gs://.../smoke_veo.mp4
  ...
  ```

Exit code is non-zero if any server fails to produce verified media. `SKIP`
(e.g. avtool without a chirp input) does not fail the run.

### How verification works (and why it's robust)

Verification never trusts the JSON-RPC response alone — it confirms the media
artifact actually exists:

- **GCS mode:** each server is given a unique destination prefix
  (`$GENMEDIA_BUCKET/smoke_<timestamp>/<server>/`) and the script lists that
  prefix with `gcloud storage ls` afterwards. This is deliberately independent
  of the response body: some servers (notably `mcp-veo-go`) return a
  `resource_link` content type that the `mcptools` CLI cannot render, so the
  video is real even though the CLI prints an "unsupported content type" error.
  Listing the destination catches this correctly.
- **Local mode:** the script checks for a non-empty file in the server's
  `smoke_output/<server>/` directory (ignoring the saved `response.json`). To
  prevent a stale artifact from a previous run reporting a false PASS, if that
  directory already exists and is non-empty the script prints a `WARN` and
  **moves it aside** to `smoke_output/<server>.stale-<timestamp>/` (nothing is
  deleted) before the call, so verification reflects only the current run.

In both modes the size check requires a non-zero-byte artifact, so an empty
placeholder object/file cannot report a false PASS.
