# MCP Omni Server

This tool provides video generation (with optional embedded audio) using Google's
Gemini Omni model (`gemini-omni-flash-preview`) via the **Vertex Interactions API**.
It is one of the MCP tools for Google Cloud Genmedia services, acting as an MCP
server component to allow LLMs and other MCP clients to generate videos from a text
prompt, optionally conditioned on input images and/or videos.

Unlike the other genmedia servers (which use the Vertex `genai` client), Omni is
reachable only through the Interactions API, so this server calls the shared
`common.GenerateOmniVideo` helper (which owns the Interactions client) rather than a
`genai.Client`. The Interactions endpoint is **global-only**: `LOCATION` defaults to
`global` and the API call is always made against the `global` endpoint.

## MCP Tool Definitions

The server exposes the following tool:

### 1. `omni_video_generation`

*   **Description**: Generates video (with optional embedded audio) from a text
    prompt, optionally conditioned on input images and/or videos, using Google's
    Gemini Omni model via the Vertex Interactions API. Returns MP4(s) saved locally
    and/or to GCS.
*   **Handler**: `omniVideoGenerationHandler`
*   **Parameters**:
    *   `prompt` (string, required): The text prompt describing the video to generate.
    *   `model` (string, optional): Model to use. Can be the canonical model ID
        (`gemini-omni-flash-preview`) or a common alias (e.g. `Omni`,
        `Gemini Omni Flash`). See `mcp-common/models.go` for the supported list.
        Defaults to `gemini-omni-flash-preview`.
    *   `images` (array of string, optional): Up to 10 input images to condition
        generation on. Each entry is a local file path or a `gs://` URI. The MIME
        type is inferred from the file extension: `image/png`, `image/jpeg`,
        `image/webp`, `image/gif`, `image/heic`, `image/heif`.
    *   `videos` (array of string, optional): Input videos to reference or edit.
        Each entry is a local file path or a `gs://` URI (e.g. `video/mp4`,
        `video/webm`, `video/quicktime`).
    *   `sample_count` (number, optional): Number of videos to generate (1-3,
        default 1). Clamped to the model maximum of 3.
    *   `temperature` (number, optional): Sampling temperature, `0.0`-`2.0` (higher
        = more varied). Sent in `generation_config`.
    *   `top_p` (number, optional): Nucleus sampling probability mass, `0.0`-`1.0`.
        Sent in `generation_config`.
    *   `output_directory` (string, optional): Local directory to save the generated
        video(s) to. Filenames (`omni_<timestamp>_<n>.mp4`) are generated
        automatically.
    *   `gcs_bucket_uri` (string, optional): GCS URI prefix to store generated
        video(s) (e.g., `your-bucket/outputs/`). If not provided and
        `GENMEDIA_BUCKET` is set, `gs://<GENMEDIA_BUCKET>/omni_outputs/` is used.
        For each uploaded video a best-effort V4 signed HTTPS URL is also returned
        (see `OMNI_SIGNED_URL_EXPIRY_HOURS`).

## Authentication

This server uses **Application Default Credentials (ADC)** to authenticate to the
Vertex Interactions API — run `gcloud auth application-default login` locally, or
rely on the attached service account when running on Google Cloud. The Interactions
API is invoked against the **`global`** location only; per-region overrides do not
apply to the Interactions call itself.

## Environment Variable Configuration

The tool utilizes the following environment variables:

*   `GOOGLE_CLOUD_PROJECT` (string): **Required**. Your Google Cloud Project ID. The
    application will terminate if this is not set. Note: `PROJECT_ID` is also
    supported as a fallback.
    *   **Override**: You can override this globally for this specific server by
        setting `OMNI_PROJECT_ID`.
*   `GOOGLE_CLOUD_LOCATION` (string): The preferred Google Cloud location. For Omni
    this defaults to `global` and the Interactions call is always made against the
    `global` endpoint.
    *   **Fallback**: `LOCATION` is also supported as a fallback for
        `GOOGLE_CLOUD_LOCATION`.
    *   **Override**: You can override this globally for this specific server by
        setting `OMNI_LOCATION`.
*   `GENMEDIA_BUCKET` (string): An optional default Google Cloud Storage bucket to
    use for GCS outputs if the `gcs_bucket_uri` parameter is not specified in the
    tool request. The path `omni_outputs/` will be appended to this bucket.
    *   Default: `""` (empty string).
*   `OMNI_SIGNED_URL_EXPIRY_HOURS` (number): Validity, in hours, of the V4 signed
    HTTPS URL returned for each uploaded video. Clamped to `168` (the V4 maximum);
    `0` disables signed-URL generation (the `gs://` URI is still returned). Signing
    under ADC without a private key requires `roles/iam.serviceAccountTokenCreator`
    on the runtime service account (non-fatal if absent).
    *   Default: `24`
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
    ./mcp-omni-go
    # or
    ./mcp-omni-go -transport stdio
    ```
*   **HTTP**:
    ```bash
    ./mcp-omni-go -transport http
    # Optionally set PORT environment variable, e.g., PORT=8084 ./mcp-omni-go -transport http
    ```
    The MCP server will be available at `http://localhost:<PORT>/mcp`.
*   **SSE (Server-Sent Events)**:
    ```bash
    ./mcp-omni-go -transport sse
    # SSE server typically runs on port 8081 by default in this configuration.
    ```
    The MCP server will be available at `http://localhost:8081`.

## Examples

### Text-to-Video (`omni_video_generation`)
```json
{
  "method": "tools/call",
  "params": {
    "name": "omni_video_generation",
    "arguments": {
      "prompt": "A majestic eagle soaring over a mountain range at sunset.",
      "sample_count": 1,
      "gcs_bucket_uri": "your-gcs-bucket/omni_outputs",
      "output_directory": "./omni_videos"
    }
  }
}
```

### Image-conditioned generation (`omni_video_generation`)
```json
{
  "method": "tools/call",
  "params": {
    "name": "omni_video_generation",
    "arguments": {
      "prompt": "Animate this landscape with a gentle breeze and flowing river.",
      "images": ["gs://your-gcs-bucket/source_images/landscape.png"],
      "output_directory": "./omni_videos"
    }
  }
}
```
