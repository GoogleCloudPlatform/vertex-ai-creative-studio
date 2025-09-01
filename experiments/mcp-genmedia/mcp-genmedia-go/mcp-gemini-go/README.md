# `mcp-gemini-go` MCP Server

This server provides an MCP interface to Google's Gemini models, allowing for multimodal content generation.

## Tools

### `gemini_image_generation`

Generates content (text and/or images) based on a multimodal prompt.

**Parameters:**

- `prompt` (string, required): The text prompt for content generation.
- `model` (string, optional): The specific Gemini model to use. Defaults to `gemini-1.5-pro-latest`.
- `images` (string array, optional): A list of local file paths or GCS URIs for input images.
- `output_directory` (string, optional): Local directory to save any generated image(s) to.
- `gcs_bucket_uri` (string, optional): GCS URI prefix to store any generated images.

### `gemini_audio_tts`

Synthesizes speech from text using Gemini models, allowing for granular control over style, pace, tone, and emotional expression through natural-language prompts.

**Parameters:**

- `text` (string, required): The text to synthesize (up to 800 characters).
- `prompt` (string, optional): Stylistic instructions on how to synthesize the content.
- `voice_name` (string, optional): The voice to use. Defaults to `Callirrhoe`. Use the `list_gemini_voices` tool to see all options.
- `model_name` (string, optional): The model to use. Defaults to `gemini-2.5-flash-preview-tts`.
- `output_directory` (string, optional): Local directory to save the generated audio file to.
- `output_filename_prefix` (string, optional): A prefix for the output WAV filename.

### `list_gemini_voices`

Lists the available single-speaker voices for use with the Gemini-TTS models.

## Resources

### `gemini://language_codes`

Provides a list of supported languages and their BCP-47 codes. Currently, only `en-US` is supported.

## Example Usage

### Generating an Image

```bash
export PROJECT_ID=your-gcp-project

mcptools call gemini_image_generation \
  --params '{"prompt": "a picture of a cat sitting on a table", "output_directory": "./output"}' \
  mcp-gemini-go
```

### Generating Audio

First, ensure the `PROJECT_ID` environment variable is set. Then, you can call the `gemini_audio_tts` tool. The following example generates an audio file and saves it to a local directory named `tts_output`.

```bash
export PROJECT_ID=$(gcloud config get-value project)

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
