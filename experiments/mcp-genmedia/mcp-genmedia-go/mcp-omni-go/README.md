# `mcp-omni-go` MCP Server

This server provides a Model Context Protocol (MCP) interface to Google's Gemini Omni video generation and editing capabilities using the [Cloud Interactions SDK for Go (`cloud-interactions-go`)](https://github.com/ghchinoy/cloud-interactions-go).

## Tools

### `omni_video_generation`

Generates or edits videos using Google's Gemini Omni Interactions API. Supports Text-to-Video (`t2v`), Image-to-Video (`i2v`), Reference-to-Video (`ref2v`), and conversational video editing (`edit`).

**Parameters:**

- `prompt` (string, required): The text prompt describing the video to generate or edit.
- `model` (string, optional): The specific Gemini Omni model version ID. Defaults to `gemini-omni-flash-preview`.
- `mode` (string, optional): Generation mode: `t2v` (Text-to-Video), `i2v` (Image-to-Video), `ref2v` (Reference-to-Video), or `edit` (Video Editing). Defaults to `t2v`.
- `aspect_ratio` (string, optional): Aspect ratio of the generated video (`16:9` or `9:16`). Defaults to `16:9`.
- `duration_seconds` (number, optional): Duration of the video in seconds. Defaults to `10`.
- `images` (string array, optional): List of image file paths or GCS URIs for starting frames (`i2v`), reference character consistency (`ref2v`), or style reference (`edit`).
- `videos` (string array, optional): List of video file paths or GCS URIs to edit (for `edit` mode).
- `previous_interaction_id` (string, optional): ID of a previous interaction turn for multi-turn conversational video editing.
- `output_directory` (string, optional): Local directory path to download and save the generated video MP4 file.
- `gcs_bucket_uri` (string, optional): GCS URI prefix to store the generated video MP4 file.

## Environment Variable Configuration

The server utilizes the following environment variables:

*   `GOOGLE_CLOUD_PROJECT` (string): **Required**. Your Google Cloud Project ID.
    *   **Override**: Can be overridden globally for this specific server by setting `OMNI_PROJECT_ID`.
*   `GOOGLE_CLOUD_LOCATION` (string): The preferred Google Cloud location/region for Vertex AI service calls. Defaults to `us-central1`.
    *   **Override**: Can be overridden by setting `OMNI_LOCATION` or fallback `LOCATION`.
*   `GENMEDIA_BUCKET` (string): Default GCS bucket for saving generated media.
*   `GEMINI_API_KEY` or `GOOGLE_API_KEY` (string): Optional API key for authentication. If omitted, Application Default Credentials (ADC) bearer tokens are used automatically.

## Example Usage

### Text-to-Video Generation

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project

mcptools call omni_video_generation \
  --params '{"prompt": "A drone flyover of a futuristic neon city at twilight", "duration_seconds": 10, "output_directory": "./output"}' \
  mcp-omni-go
```

### Conversational Video Editing (Multi-turn)

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project

mcptools call omni_video_generation \
  --params '{"prompt": "Make the lighting sunset instead of twilight", "previous_interaction_id": "INTERACTION_ID_FROM_PREVIOUS_STEP", "output_directory": "./output"}' \
  mcp-omni-go
```
