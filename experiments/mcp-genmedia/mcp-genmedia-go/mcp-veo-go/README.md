# MCP Veo Server (Version: 1.12.0)

This tool provides video generation capabilities using Google's Veo models (via Vertex AI). It is one of the MCP tools for Google Cloud Genmedia services, acting as an MCP server component to allow LLMs and other MCP clients to generate videos from text prompts or source images.

## MCP Tool Definitions

The server exposes the following tools:

### 1. `veo_t2v` (Text-to-Video)

*   **Description**: Generate a video from a text prompt using Veo. Video is saved to GCS and optionally downloaded locally.
*   **Handler**: `veoTextToVideoHandler`
*   **Parameters**:
    *   `prompt` (string, required): Text prompt for video generation.
    *   `bucket` (string, optional): Google Cloud Storage bucket where the API will save the generated video(s) (e.g., "your-bucket/output-folder" or "gs://your-bucket/output-folder"). If not provided, and `GENMEDIA_BUCKET` env var is set, `gs://<GENMEDIA_BUCKET>/veo_outputs/` will be used. One of these (param or env var) is effectively required.
    *   `output_directory` (string, optional): If provided, specifies a local directory to download the generated video(s) to. Filenames will be generated automatically.
    *   `model` (string, optional): Model to use for video generation. Can be a full model ID or a common alias. See the `mcp-common/models.go` file for a complete list of supported models and aliases.
    *   `num_videos` (number, optional): Number of videos to generate. Note: the maximum is model-dependent.
    *   `aspect_ratio` (string, optional): Aspect ratio of the generated videos. Note: supported aspect ratios are model-dependent.
    *   `duration` (number, optional): Duration of the generated video in seconds. Note: the supported duration range is model-dependent.

### 2. `veo_i2v` (Image-to-Video)

*   **Description**: Generate a video from an input image (and optional prompt) using Veo. Video is saved to GCS and optionally downloaded locally. Supported image MIME types: image/jpeg, image/png.
*   **Handler**: `veoImageToVideoHandler`
*   **Parameters**:
    *   `image_uri` (string, required): GCS URI of the input image for video generation (e.g., "gs://your-bucket/input-image.png").
    *   `mime_type` (string, optional): MIME type of the input image. Supported types are 'image/jpeg' and 'image/png'. If not provided, an attempt will be made to infer it from the `image_uri` extension.
    *   `prompt` (string, optional): Optional text prompt to guide video generation from the image.
    *   `bucket` (string, optional): Google Cloud Storage bucket for output. Same logic as `veo_t2v`.
    *   `output_directory` (string, optional): Local directory for download. Same logic as `veo_t2v`.
    *   `model` (string, optional): Model to use. Default: `"veo-2.0-generate-001"`.
    *   `num_videos` (number, optional): Number of videos. Default: `1`. Min: `1`, Max: `4`.
    *   `aspect_ratio` (string, optional): Aspect ratio. Default: `"16:9"`.
    *   `duration` (number, optional): Duration in seconds. Default: `5`. Min: `5`, Max: `8`.

### 3. `veo_interpolate` (Video Interpolation)

*   **Description**: Generate a video by interpolating between a first and last frame. Can be guided by an optional text prompt and reference images. This feature is only available on specific models (e.g., `veo-3.1-generate-preview`).
*   **Handler**: `veoInterpolationHandler`
*   **Parameters**:
    *   `first_frame_uri` (string, required): GCS URI of the first frame (start image) for video interpolation (e.g., "gs://your-bucket/first-frame.png").
    *   `last_frame_uri` (string, required): GCS URI of the last frame (end image) for video interpolation (e.g., "gs://your-bucket/last-frame.png").
    *   `first_frame_mime_type` (string, optional): MIME type of the first frame. Supported types are 'image/jpeg' and 'image/png'. If not provided, it will be inferred from the URI.
    *   `last_frame_mime_type` (string, optional): MIME type of the last frame. Supported types are 'image/jpeg' and 'image/png'. If not provided, it will be inferred from the URI.
    *   `reference_images` (string, optional): A JSON string representing an array of reference image objects. Each object must have a 'uri' (string) and a 'type' (string, either 'ASSET' or 'STYLE'). This feature is only available on specific models.
        *   **Note**: `veo-3.1` models only support the `ASSET` type. The `STYLE` type is supported by models like `veo-2.0-generate-exp`.
        *   Example: `'[{"uri": "gs://your-bucket/ref.png", "type": "ASSET"}]'`
    *   `prompt` (string, optional): Optional text prompt to guide video generation.
    *   All common parameters from `veo_t2v` (like `bucket`, `output_directory`, `model`, etc.) are also applicable.

## Environment Variable Configuration

The tool utilizes the following environment variables:

*   `PROJECT_ID` (string): **Required**. Your Google Cloud Project ID. The application will terminate if this is not set.
*   `LOCATION` (string): The Google Cloud location/region for Vertex AI services.
    *   Default: `"us-central1"`
*   `GENMEDIA_BUCKET` (string): An optional default Google Cloud Storage bucket to use for GCS outputs if the `bucket` parameter is not specified in the tool request. The path `veo_outputs/` will be appended to this bucket.
    *   Default: `""` (empty string).
*   `PORT` (string, for HTTP transport): The port for the HTTP server to listen on.
    *   Default: `"8080"`

## Transports Supported

*   `stdio` (default)
*   `sse` (Server-Sent Events)
*   `http` (Streamable HTTP)

CORS is enabled for the HTTP transport, allowing all origins by default.

## Run

Build the tool using `go build` or `go install`.

*   **STDIO (Default)**:
    ```bash
    ./mcp-veo-go
    # or
    ./mcp-veo-go -transport stdio
    ```
*   **HTTP**:
    ```bash
    ./mcp-veo-go -transport http
    # Optionally set PORT environment variable, e.g., PORT=8084 ./mcp-veo-go -transport http
    ```
    The MCP server will be available at `http://localhost:<PORT>/mcp`.
*   **SSE (Server-Sent Events)**:
    ```bash
    ./mcp-veo-go -transport sse
    # SSE server typically runs on port 8081 by default in this configuration.
    ```
    The MCP server will be available at `http://localhost:8081`.

## Examples

### Text-to-Video (`veo_t2v`)
```json
{
  "method": "tools/call",
  "params": {
    "name": "veo_t2v",
    "arguments": {
      "prompt": "A majestic eagle soaring over a mountain range at sunset.",
      "model": "veo-2.0-generate-001",
      "num_videos": 1,
      "aspect_ratio": "16:9",
      "duration": 8,
      "bucket": "your-gcs-bucket/veo_t2v_outputs",
      "output_directory": "./veo_videos_t2v"
    }
  }
}
```

### Image-to-Video (`veo_i2v`)
```json
{
  "method": "tools/call",
  "params": {
    "name": "veo_i2v",
    "arguments": {
      "image_uri": "gs://your-gcs-bucket/source_images/landscape.png",
      "mime_type": "image/png",
      "prompt": "Animate this landscape with a gentle breeze and flowing river.",
      "model": "veo-2.0-generate-001",
      "num_videos": 1,
      "aspect_ratio": "16:9",
      "duration": 6,
      "bucket": "your-gcs-bucket/veo_i2v_outputs",
    }
  }
}

### Video Interpolation (`veo_interpolate`)
```json
{
  "method": "tools/call",
  "params": {
    "name": "veo_interpolate",
    "arguments": {
      "first_frame_uri": "gs://your-gcs-bucket/source_images/start_frame.png",
      "last_frame_uri": "gs://your-gcs-bucket/source_images/end_frame.png",
      "model": "veo-3.1-generate-preview",
      "prompt": "A car transforming into a robot.",
      "reference_images": "[{\"uri\": \"gs://your-gcs-bucket/style_images/cyberpunk.png\", \"type\": \"ASSET\"}]",
      "bucket": "your-gcs-bucket/veo_interpolate_outputs",
      "output_directory": "./veo_videos_interpolate"
    }
  }
}
```
```
