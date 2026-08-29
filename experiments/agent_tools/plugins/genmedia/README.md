# genmedia — Agent Plugin

Packages the Google Cloud **genmedia** MCP servers as an installable
[Agent Plugin](https://agent-plugins.org) so an Agent-Plugins-aware client can
install one plugin and get the servers **launchable** — no manual binary build
and no hand-edited MCP client config.

This plugin currently wires **only the `nanobanana` image-generation server**.
The remaining six genmedia servers (veo, chirp3, gemini, lyria, avtool, omni)
are not yet wired; they will be added using the same launcher and manifest.

## What's here

| File | Purpose |
|---|---|
| `plugin.json` | Agent Plugins v1.0.0 manifest (closed schema). |
| `mcp.json` | Agent Plugins v1.0.0 MCP launch descriptor (`nanobanana`, stdio). Spec-canonical form. |
| `.mcp.json` | **Claude Code**-native MCP descriptor (see [Client compatibility](#client-compatibility)). |
| `bin/genmedia-launch` | POSIX download-on-launch launcher (linux/darwin). |
| `skills/genmedia-image/SKILL.md` | Agent Skill: generate images via `nanobanana_image_generation` (see [Skills](#skills)). |
| `.gitignore` | Keeps the runtime download cache out of git. |

## Skills

Alongside the launchable servers, this plugin ships **Agent Skills** — prose
workflow expertise that *calls* the genmedia MCP tools (modeled on the `ai-pop`
precedent). A skill assumes the relevant MCP server is already configured (this
plugin's `mcp.json` / `.mcp.json`, or a manual MCP config).

| Skill | Tool | Purpose |
|---|---|---|
| `genmedia-image` | `nanobanana_image_generation` | Generate a still image from a text prompt (optionally guided by reference images), with control over aspect ratio, resolution, and local vs GCS output; verifies the artifact by existence. |

More genmedia skills (video, speech, and goal-driven orchestrators) are planned.

## How it works — download on launch

Agent Plugins have **no install/fetch phase**: `mcp.json` describes *how to
launch* a server, not *how to obtain* it, and its `command` is a fixed string
that cannot select a per-OS/arch binary at runtime. The genmedia servers are
distributed as a **single GoReleaser release** containing all seven binaries per
platform. `bin/genmedia-launch` bridges that gap. On first launch of a server it:

1. **Detects** OS/arch (`uname`) → maps to the release asset
   `genmedia-mcp-servers_<os>_<arch>.tar.gz`.
2. **Downloads** that tarball + the release `checksums.txt` from the pinned
   GitHub Release (default tag **`v3.18.0`**).
3. **Verifies** the tarball's SHA-256 against **both** a value pinned inside the
   launcher **and** the downloaded `checksums.txt`. A mismatch on either aborts
   before anything runs — this rejects a corrupted download *and* a
   moved/re-tagged release.
4. **Extracts** the seven server binaries into a persistent writable cache.
5. **Execs** the requested server, which speaks MCP over stdio.

First launch downloads one tarball (~80 MB) once; every server then runs from
that single extraction, and subsequent launches are **exec-only** (no
re-download). The binary embeds its version (`-X main.version`), so provenance is
checkable — the pinned `v3.18.0` binaries report `Version: 3.18.0`.

### Pinning / updating the server version

The release is pinned in two coordinated places — the launcher's `PINNED_TAG`
(+ its `PINNED_SHA256_*` values) and the `GENMEDIA_RELEASE_TAG` env value in the
manifests. **Bumping the version means updating both together.** Setting
`GENMEDIA_RELEASE_TAG` to a *different* tag downloads that release and verifies
it against its own `checksums.txt` only (the launcher warns that no pinned SHA is
available for an off-pin tag).

## Credentials & configuration

Secrets and project config are **never** baked into the distributable manifest.
The manifests set only non-secret operational values (the pinned release tag).
You supply the genmedia runtime configuration through **your own environment**:

| Variable | Required | Purpose |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | **Yes** | GCP project for Vertex AI calls. |
| Application Default Credentials (ADC) | **Yes** | `gcloud auth application-default login`, or a service-account identity. |
| `GENMEDIA_BUCKET` | Optional | Default GCS destination (`gs://bucket/prefix`). Enables "GCS mode". |
| `LOCATION` | Optional | Vertex region; defaults per server (e.g. `global`/`us-central1`). |

### Output modes (same convention as the smoke suite and `ai-pop`)

- **Local mode (default):** pass `output_directory` to a tool; the artifact is
  written to that local path.
- **GCS mode:** pass `gcs_bucket_uri` (or set `GENMEDIA_BUCKET`); the artifact is
  written to GCS. In GCS mode the server returns an MCP `resource_link` content
  type that some clients cannot render even though the file was written — always
  **verify by destination listing** (`gcloud storage ls <prefix>`), not by
  reading the tool's rendered response.

## Install

### Claude Code (validated end to end)

```bash
# From a checkout of this repo, add this directory as a marketplace:
claude plugin marketplace add /path/to/vertex-ai-creative-studio/experiments/agent_tools
claude plugin install genmedia@vaics-agent-tools

# Confirm the server launches and connects (first run downloads the release):
claude mcp list        # -> plugin:genmedia:nanobanana ... ✔ Connected
```

Then, in a Claude Code session (with `GOOGLE_CLOUD_PROJECT` set and ADC
available), the `nanobanana_image_generation` tool is callable and writes a real
image to your requested `output_directory` / `gcs_bucket_uri`.

### Other clients

Any Agent-Plugins-aware client reads `mcp.json`; the launcher is client-agnostic.
Native repackaging for Gemini CLI / Antigravity, and manual-config fallback docs
for other clients, are planned.

## Client compatibility

Two MCP descriptors ship here because the ecosystem hasn't fully converged:

- **`mcp.json`** — the Agent Plugins v1.0.0 canonical form: relative
  `command: ./bin/genmedia-launch`, `cwd: ${PLUGIN_ROOT}`, cache under
  `${PLUGIN_DATA}`.
- **`.mcp.json`** — what **Claude Code (v2.1.222)** actually reads. Claude Code
  resolves `command` against the process working directory (not `${PLUGIN_ROOT}`)
  and provides its own `${CLAUDE_PLUGIN_ROOT}` placeholder, so it needs
  `command: ${CLAUDE_PLUGIN_ROOT}/bin/genmedia-launch`. Claude Code's plugin
  marketplace manifest also requires an `owner` object (see
  `../../.claude-plugin/marketplace.json`).

Both point at the **same launcher** and the **same pinned release** — only the
thin descriptor differs. Keeping both means the plugin is spec-conformant *and*
works today in the known-good client.

## Containment

Per Agent Plugins §4.1, every path a client resolves stays inside the plugin
root. The `command` is inside the plugin (`./bin/genmedia-launch`); downloaded
binaries are written only to the client-designated writable cache
(`${PLUGIN_DATA}` for spec clients, or `~/.cache/genmedia/bin` as a standalone
fallback) — never via a `../` escape, and the launcher creates no symlinks.

## Current scope

Only `nanobanana` is wired. `lyria` is deliberately deferred (a client-side
audio-parsing fix rides in a later pinned release); `avtool` needs `ffmpeg` at
runtime; a Windows launcher is not yet available.
