---
title: "MCP Servers for Google Cloud Genmedia APIs"
---

This repository provides Model Context Protocol (MCP) servers that enable AI agents and applications to easily integrate and leverage the full breadth and depth of Google Cloud's powerful generative media APIs (Gemini Image, Gemini TTS, Veo, Chirp, Imagen, Lyria) and advanced audio/video compositing capabilities (AVTool).

Each server can be enabled and run separately, allowing flexibility for environments that don't require all capabilities.

## Generative Media & Compositing Capabilities

*   **Nano Banana: [Gemini 3.1 Flash Image](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-1-flash-image) & [Gemini 3 Pro Image](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro-image) & [Gemini 2.5 Flash Image](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash#image)** - for image generation and editing
*   **[Veo 3 & 3.1](https://cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos)** - for video creation
*   **[Gemini TTS](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts)** & **[Chirp 3 HD](https://cloud.google.com/text-to-speech/docs/chirp3-hd)** - for speech synthesis
*   **[Lyria](https://cloud.google.com/vertex-ai/generative-ai/docs/music/generate-music)** - for music generation
*   **[Imagen 3 & 4](https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview)** - for image generation and editing

*   **AVTool** - for audio/video compositing and manipulation

## 🛠️ Agent Skills

We provide a set of expert **Agent Skills** that provide AI agents (like Gemini CLI or Antigravity) with deep domain knowledge on how to use these MCP tools effectively for complex workflows.

*   `genmedia-producer`: Orchestrates multi-step workflows like podcast creation and storyboarding.
*   `genmedia-video-editor`: Expertise in FFmpeg composition, image overlays, and GIF generation.
*   `genmedia-audio-engineer`: Specialist in high-fidelity TTS synthesis and multi-track mixing.
*   `genmedia-image-artist`: Expert in visual generation, prompt optimization, and collaborative refinement.
*   `genmedia-voice-director`: Expert in casting, directing, and generating expressive text-to-speech using Gemini TTS.

See the [Agent Skills](./skills/README.md) directory for more information on how to link or install these skills.

## Installation

**Install MCP Servers:** For detailed installation instructions, including an easy-to-use installer script, please refer to the [Go Implementations README](./mcp-genmedia-go/README.md).

### Easy Installation (Pre-compiled Binaries)

For the fastest setup without needing the Go toolchain installed, you can use our online installer script. This script automatically detects your operating system and architecture, downloads the latest pre-compiled binaries from GitHub Releases, and places them in your `~/.local/bin` directory.

Run the following command in your terminal:

```bash
curl -sL https://raw.githubusercontent.com/GoogleCloudPlatform/vertex-ai-creative-studio/main/experiments/mcp-genmedia/mcp-genmedia-go/install-online.sh | bash
```

*Note: Ensure `~/.local/bin` is added to your system `PATH`.*


## Running the Servers

The MCP servers can be run using different transport protocols. The default is `stdio`.

To start a server in Streamable HTTP mode, use the `--transport http` flag:
```bash
mcp-imagen-go --transport http
```

## Configuration

The servers are configured primarily through environment variables. Key variables include:

*   `PROJECT_ID`: Your Google Cloud project ID.
*   `LOCATION`: The Google Cloud region for the APIs (e.g., `us-central1`).
*   `PORT`: The port for the HTTP server (e.g., `8080`).
*   `GENMEDIA_BUCKET`: The Google Cloud Storage bucket for media assets.

## Available MCP Servers and Capabilities

*   **Gemini Image** Generate and edit images from text prompts.
*   **Gemini TTS** Synthesize high-quality audio from text.
*   **Veo:** Create videos from text or images.
*   **Lyria:** Generate music from text prompts.
*   **Chirp 3 HD:** Synthesize high-quality audio from text.
*   **Imagen:** Generate and edit images from text prompts.
*   **AVTool:** Perform audio/video compositing and manipulation (e.g., combining, concatenating, format conversion).

For a detailed list of tools provided by each server, refer to the [Go Implementations README](./mcp-genmedia-go/README.md).

## Naming Outputs: `output_filename`

Every media-generating tool accepts a single optional `output_filename` (string)
with identical name and semantics across servers, so a client can **predict the
exact output name** from the tool and request. The same computed name is applied
consistently to the inline response, the local `output_directory`, and GCS.

*   **Precedence:** `output_filename` always wins over a server's legacy naming
    parameter; if neither is set, the server's default scheme is used. When
    `output_filename` is unset, behavior is unchanged (no regression).
*   **Extension forced to the true type:** you provide the file *stem* and the
    extension is set from the model's actual output MIME type (`hero.jpeg` on a PNG
    response → `hero.png`; a missing extension is added). **AVTool is exempt** —
    for `ffmpeg` the extension selects the output container, so AVTool keeps the
    extension you provide.
*   **Multiple outputs → `_1..n` suffix:** one output is `<stem>.<ext>`; `n > 1`
    outputs are `<stem>_1.<ext> … <stem>_n.<ext>` (1-based, no zero-padding, in
    generation order).
*   **Collisions overwrite with a warning** (re-running the same name is
    idempotent), and **path traversal is sanitized** to a single safe name.
*   **Imagen & Veo** let the Vertex API name objects (`sample_*`) and then rename
    them to `output_filename`; on success no `sample_*` originals remain.

**Deprecated legacy aliases** (still accepted; prefer `output_filename`, no
removal planned): AVTool `output_file_name`, Lyria `file_name`, and the Chirp 3 /
Gemini TTS `output_filename_prefix` (a *prefix* only — `output_filename` gives the
full name).

## Authentication

The servers use Google's Application Default Credentials (ADC). Ensure you have authenticated by one of the following methods:

1.  Set up ADC: `gcloud auth application-default login`
2.  Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your service account key file.

You may also need to grant your user or service account access to the Google Cloud Storage bucket:
```bash
gcloud storage buckets add-iam-policy-binding gs://BUCKET_NAME \
  --member=user:user@email.com \
  --role=roles/storage.objectUser
```

## Client Configurations

The MCP servers can be used with various clients and hosts. A sample MCP configuration JSON can be found at [genmedia-config.json](./sample-agents/mcp-inspector/genmedia-config.json).

This repository provides AI application samples for:

* [geminicli](./sample-agents/geminicli/)
* [Google ADK (Agent Development Kit)](./sample-agents/adk/README.md)
* [Google Firebase Genkit](./sample-agents/genkit/README.md)

## Development and Contribution

For those interested in extending the existing servers or creating new ones, the `mcp-genmedia-go` directory contains a more detailed `README.md` with information on the architecture and development process. Please refer to the [mcp-genmedia-go/README.md](./mcp-genmedia-go/README.md) for more information.

## License

Apache 2.0

## Disclaimer

This is not an officially supported Google product.
