---
title: "`mcp-gemini-transcribe-go` MCP Server"
---

This server provides synchronous speech-to-text transcription using Google's **Gemini 3.5 Transcribe** model (`gemini-3.5-transcribe-preview`) via the Vertex `genai` client.

It is the single-purpose, standalone sibling of the `gemini_transcribe` tool that is also bundled into the all-in-one [`mcp-gemini-go`](../mcp-gemini-go/) server. Both share the exact same implementation via `mcp-common`, so their behavior can never drift — use this standalone server when you only need transcription and want a minimal surface.

This server uses the **synchronous** transcription API (the `generate_content` path on `gemini-3.5-transcribe-preview`), **not** the live/streaming API. It is intended for pre-recorded files up to ~15 minutes, not for real-time streaming.

> **Note:** Gemini 3.5 Transcribe is served only in the `global` location. This server defaults `LOCATION` to `global`; leave `LOCATION`/`GOOGLE_CLOUD_LOCATION` unset (or set to `global`) for transcription to work.

## Tools

### `gemini_transcribe`

Transcribes a pre-recorded audio file to text using Google's Gemini 3.5 Transcribe model (synchronous mode). Supports language hints, custom vocabulary biasing, speaker diarization, word-level timestamps, and smart formatting.

**Parameters:**

- `input_audio` (string, required): The audio to transcribe — either a local file path or a `gs://` URI. Supported formats include WAV, MP3, OGG/Opus, FLAC, M4A/AAC, AIFF, AMR, WEBM, and PCM.
- `mime_type` (string, optional): The MIME type of the audio (e.g. `audio/wav`, `audio/mpeg`, `audio/ogg`). Inferred from the file extension when omitted (`.m4a`/`.mp4`/`.aac` infer `audio/mp4`).
- `model` (string, optional): The transcription model. Defaults to `gemini-3.5-transcribe-preview`.
- `language_codes` (string array, optional): BCP-47 language hints (e.g. `["en-US", "es-ES"]`). Omit for automatic language detection.
- `custom_vocabulary` (string array, optional): Up to 1000 phrases (brand names, proper nouns, domain terms) that bias recognition. Most reliable when `language_codes` is also set.
- `enable_diarization` (boolean, optional): Label individual speakers (up to 8). Incompatible with `smart_formatting`.
- `enable_word_timestamps` (boolean, optional): Return word-level start/end offsets. Incompatible with `smart_formatting`.
- `smart_formatting` (boolean, optional): Use SMART mode — filler-word removal, light grammatical cleanup, and automatic formatting. Incompatible with `enable_diarization` and `enable_word_timestamps`.
- `output_directory` (string, optional): Local directory to save the transcription result (JSON) to.
- `gcs_bucket_uri` (string, optional): GCS URI prefix to store the transcription result (JSON).
- `output_filename` (string, optional): Base name for the saved transcript. The extension is forced to `.json`. See [Naming Outputs](../index.md#naming-outputs-output_filename).

The plain transcript is always returned as the first text content item. When speaker diarization or word-level timestamps are requested, a second text content item carries the full structured result as JSON (transcript, per-segment speaker labels, and word timings).

## Environment Variable Configuration

The tool utilizes the following environment variables:

*   `GOOGLE_CLOUD_PROJECT` (string): **Required**. Your Google Cloud Project ID. Note: `PROJECT_ID` is also supported as a fallback.
*   `GOOGLE_CLOUD_LOCATION` (string): The preferred Google Cloud location. For Gemini 3.5 Transcribe this defaults to `global` (the only location where the model is served).
    *   **Fallback**: `LOCATION` is also supported as a fallback for `GOOGLE_CLOUD_LOCATION`.
*   `GENMEDIA_BUCKET` (string): An optional default Google Cloud Storage bucket to use for GCS outputs if the `gcs_bucket_uri` parameter is not specified in the tool request.
*   `PORT` (string, for HTTP transport): The port for the HTTP server to listen on. Default: `8080`.

## Transports Supported

*   `stdio` (default)
*   `sse` (Server-Sent Events)
*   `http` (Streamable HTTP)

CORS is enabled for the HTTP transport, allowing all origins by default.

## Run

Build the tool using `go build` or `go install`.

*   **STDIO (Default)**:
    ```bash
    ./mcp-gemini-transcribe-go
    # or
    ./mcp-gemini-transcribe-go -transport stdio
    ```
*   **HTTP**:
    ```bash
    ./mcp-gemini-transcribe-go -transport http
    # Optionally set PORT, e.g. PORT=8084 ./mcp-gemini-transcribe-go -transport http
    ```
    The MCP server will be available at `http://localhost:<PORT>/mcp`.
*   **SSE (Server-Sent Events)**:
    ```bash
    ./mcp-gemini-transcribe-go -transport sse
    ```
    The MCP server will be available at `http://localhost:8081`.

## Example Usage

### Transcribe a GCS audio file

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)

mcptools call gemini_transcribe \
  --params '{"input_audio": "gs://your-gcs-bucket/audio/meeting.wav", "language_codes": ["en-US"], "output_directory": "./transcripts"}' \
  mcp-gemini-transcribe-go
```

### Transcribe with diarization and word timestamps

```bash
mcptools call gemini_transcribe \
  --params '{"input_audio": "./samples/interview.mp3", "enable_diarization": true, "enable_word_timestamps": true, "output_directory": "./transcripts"}' \
  mcp-gemini-transcribe-go
```
