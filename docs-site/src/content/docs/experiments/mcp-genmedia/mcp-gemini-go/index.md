---
title: "`mcp-gemini-go` MCP Server"
---

This server provides an MCP interface to Google's Gemini models, allowing for multimodal content generation.

## Tools

### `gemini_image_generation`

Generates content (text and/or images) based on a multimodal prompt.

**Parameters:**

- `prompt` (string, required): The text prompt for content generation.
- `model` (string, optional): The specific Gemini model to use. Defaults to `gemini-3.1-flash-image`.
- `aspect_ratio` (string, optional): Aspect ratio of the generated image(s), e.g. `1:1`, `16:9`, `21:9`. Defaults to `1:1`. Supported ratios are model-dependent; unsupported values fall back to `1:1`.
- `image_size` (string, optional): Size of the generated image(s): `1K`, `2K`, or `4K`. When unset the model's default (`1K`) is used. Supported sizes are model-dependent; unsupported values are ignored.
- `images` (string array, optional): A list of local file paths or GCS URIs for input images.
- `output_directory` (string, optional): Local directory to save any generated image(s) to.
- `output_filename` (string, optional): Base name for the output(s), e.g. `hero.png`. The extension is forced to the true image type and, when more than one image is generated, a `_1..n` suffix is inserted before the extension. Applied identically to local files and GCS objects. See [Naming Outputs](../index.md#naming-outputs-output_filename).
- `gcs_bucket_uri` (string, optional): GCS URI prefix to store any generated images.

When images are uploaded to GCS, `gemini_image_generation` appends one MCP `resource_link` content item per image (`uri` = the `gs://` URI, plus `name`, `mimeType`, and a 1-based `description`); the text summary is unchanged. This applies to image generation only — `gemini_audio_tts` does **not** emit resource links. See [Resource Links for GCS Outputs](../index.md#resource-links-for-gcs-outputs).

### `gemini_audio_tts`

Synthesizes speech from text using Gemini models, allowing for granular control over style, pace, tone, and emotional expression through natural-language prompts.

**Parameters:**

- `text` (string, required): The text to synthesize (up to 800 characters).
- `prompt` (string, optional): Stylistic instructions on how to synthesize the content.
- `voice_name` (string, optional): The voice to use. Defaults to `Callirrhoe`. Use the `list_gemini_voices` tool to see all options.
- `model_name` (string, optional): The model to use. Defaults to `gemini-3.1-flash-tts-preview`.
- `output_directory` (string, optional): Local directory to save the generated audio file to.
- `output_filename` (string, optional): Full base name for the output WAV file, e.g. `greeting.wav`. The extension is forced to `.wav`. Takes precedence over `output_filename_prefix` (which only supplies a prefix). See [Naming Outputs](../index.md#naming-outputs-output_filename).
- `output_filename_prefix` (string, optional): **Deprecated — prefer `output_filename`.** A prefix for the output WAV filename. Still accepted for backward compatibility.

### `gemini_transcribe`

Transcribes a pre-recorded audio file to text using Google's **Gemini 3.5 Transcribe** model in **synchronous** mode (the `generate_content` path on `gemini-3.5-transcribe-preview`, **not** the live/streaming API). Intended for pre-recorded files up to ~15 minutes. Supports language hints, custom vocabulary biasing, speaker diarization, word-level timestamps, and smart formatting.

> **Note:** Gemini 3.5 Transcribe is served only in the `global` location. `mcp-gemini-go` already defaults to `global`; leave `LOCATION`/`GOOGLE_CLOUD_LOCATION` unset (or set to `global`) for transcription to work.

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

This tool is also available as a single-purpose, standalone server: [`mcp-gemini-transcribe-go`](../mcp-gemini-transcribe-go/). Both share the same implementation via `mcp-common`, so their behavior never drifts.

### `list_gemini_voices`

Lists the available single-speaker voices for use with the Gemini-TTS models.

## Resources

### `gemini://language_codes`

Provides a list of supported languages and their BCP-47 codes. Currently, only `en-US` is supported.

## Environment Variable Configuration

The tool utilizes the following environment variables:

*   `GOOGLE_CLOUD_PROJECT` (string): **Required**. Your Google Cloud Project ID.
    *   **Override**: You can override this globally for this specific server by setting `GEMINI_PROJECT_ID`.
*   `GOOGLE_CLOUD_LOCATION` (string): The preferred Google Cloud location/region for Google Cloud AI services.
    *   Default: `"us-central1"`
    *   **Fallback**: `LOCATION` is also supported as a fallback for `GOOGLE_CLOUD_LOCATION`.
    *   **Override**: You can override this globally for this specific server by setting `GEMINI_LOCATION`.
*   `ALLOW_UNSAFE_MODELS` (boolean): Optional (`true`/`false`). Allows users to bypass strict local model constraint validation, enabling them to test experimental or pre-release model strings that are not yet hardcoded in the registry.
    *   Default: `false`
*   `ENABLE_OPTIONAL_HEADER_CAPTURE` (boolean): Optional (`true`/`false`). Intended for internal debugging. When set to `true`, the server intercepts API requests and injects the raw ADC Bearer token to capture and surface the `x-goog-sherlog-link` header in the tool output. This feature is supported for Gemini.
    *   Default: `false`

## Example Usage

### Generating an Image

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project

mcptools call gemini_image_generation \
  --params '{"prompt": "a picture of a cat sitting on a table", "output_directory": "./output"}' \
  mcp-gemini-go
```

### Generating Audio

First, ensure the `GOOGLE_CLOUD_PROJECT` environment variable is set. Then, you can call the `gemini_audio_tts` tool. The following example generates an audio file and saves it to a local directory named `tts_output`.

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)

mcptools call gemini_audio_tts \
  --params '{"text": "Hello, this is a test of the Gemini Text-to-Speech API.", "output_directory": "./tts_output"}' \
  mcp-gemini-go
```

### Testing Direct Audio Output (Advanced)

If you want to test the direct audio output without saving to a file via the `output_directory` parameter, you can send a raw JSON-RPC request to the server. This is necessary because the `mcptools` client does not support rendering audio content to the terminal.

The following command pipes a `tools/call` request to the server, parses the JSON response with `jq` to extract the base64-encoded audio data, decodes it, and saves it to a local file.

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"gemini_audio_tts","arguments":{"text":"This is a direct JSON-RPC output test."}}}' | \
mcp-gemini-go | \
jq -r '.result.content[] | select(.type == "audio") | .data' | \
base64 --decode > test_direct_jsonrpc.wav
```

### Transcribing Audio

First, ensure the `GOOGLE_CLOUD_PROJECT` environment variable is set. Then call the `gemini_transcribe` tool with either a local file path or a `gs://` URI. The following example transcribes an audio file stored in GCS with an English language hint and saves the JSON result to a local directory named `transcripts`.

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)

mcptools call gemini_transcribe \
  --params '{"input_audio": "gs://your-gcs-bucket/audio/meeting.wav", "language_codes": ["en-US"], "output_directory": "./transcripts"}' \
  mcp-gemini-go
```

To label individual speakers and return word-level timestamps, enable diarization and word timestamps:

```bash
mcptools call gemini_transcribe \
  --params '{"input_audio": "./samples/interview.mp3", "enable_diarization": true, "enable_word_timestamps": true, "output_directory": "./transcripts"}' \
  mcp-gemini-go
```
