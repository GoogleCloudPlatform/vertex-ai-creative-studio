# MCP Lyria Server

This tool provides music generation capabilities using Google's Lyria models (via Vertex AI). It is one of the MCP tools for Google Cloud Genmedia services, functioning as an MCP server component to allow LLMs and other MCP clients to generate music from text prompts.

## MCP Tool Definition

The following tool is exposed by this server:

### 1. `lyria_generate_music`

*   **Description**: Generates music from a text prompt using Lyria. Optionally saves to GCS and/or a local directory. Audio data is returned directly ONLY if neither GCS nor local path is specified.
*   **Handler**: `lyriaGenerateMusicHandler`
*   **Parameters**:
    *   `prompt` (string, required): Text prompt for music generation.
    *   `negative_prompt` (string, optional): A negative prompt to instruct the model to avoid certain characteristics.
    *   `seed` (number, optional): Random seed (uint32) for music generation for reproducibility.
    *   `sample_count` (number, optional): Number of music samples (uint32) to generate.
        *   Default: `1` (from `defaultSampleCount`).
        *   Min: `1`.
        *   Note: Currently, only the first sample is processed and returned/saved.
    *   `output_gcs_bucket` (string, optional): Google Cloud Storage bucket name (without `gs://` prefix). If provided, audio is saved to GCS. If this parameter is empty but the `GENMEDIA_BUCKET` environment variable is set, `GENMEDIA_BUCKET` will be used.
    *   `file_name` (string, optional): Desired file name (e.g., "my_song.wav"). Used for GCS object and local file. If omitted, a unique name like "lyria_output_&lt;uid&gt;.wav" is generated.
    *   `local_path` (string, optional): Local directory path. If provided, audio is saved locally.
    *   `model_id` (string, optional): Specific Lyria model ID to use for the Vertex AI endpoint.
        *   Defaults to the value of the `DEFAULT_LYRIA_MODEL_ID (Deprecated)` environment variable, or `"lyria-3-clip-preview"` if the variable is not set.

## Environment Variable Configuration

The tool utilizes the following environment variables:

*   `GOOGLE_CLOUD_PROJECT` (string): **Required**. Your Google Cloud Project ID. The application will terminate if this is not set. Note: `PROJECT_ID` is also supported as a fallback.
    *   **Override**: You can override this globally for this specific server by setting `LYRIA_PROJECT_ID`.
*   `LOCATION` (string): The primary Google Cloud location for services.
    *   Default: `"us-central1"`
    *   Also used as the default for `LYRIA_LOCATION (Deprecated for V3)` if `LYRIA_LOCATION (Deprecated for V3)` is not set.
*   `LYRIA_LOCATION (Deprecated for V3)` (string): The specific Google Cloud location for the Lyria model endpoint.
    *   Default: Value of `LOCATION` environment variable (e.g., `"us-central1"`).
*   `LYRIA_MODEL_PUBLISHER (Deprecated)` (string): The publisher of the Lyria model in Vertex AI.
    *   Default: `"google"`
*   `DEFAULT_LYRIA_MODEL_ID (Deprecated)` (string): The default Lyria model ID to be used if not specified in the request.
    *   Default: `"lyria-3-clip-preview"` (fallback if the environment variable is not set).
*   `GENMEDIA_BUCKET` (string): An optional default Google Cloud Storage bucket to use for GCS outputs if `output_gcs_bucket` is not specified in the tool request. The object name will be `lyria_outputs/<generated_filename>.wav` within this bucket.
    *   Default: `""` (empty string, meaning no default GCS output path is formed from this variable unless `output_gcs_bucket` is also absent).
*   `ALLOW_UNSAFE_MODELS` (boolean): Optional (`true`/`false`). Allows users to bypass strict local model constraint validation, enabling them to test experimental or pre-release model strings that are not yet hardcoded in the registry.
    *   Default: `false`
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
    ./mcp-lyria-go
    # or
    ./mcp-lyria-go -transport stdio
    ```
*   **HTTP**:
    ```bash
    ./mcp-lyria-go -transport http
    # Optionally set PORT environment variable, e.g., PORT=8085 ./mcp-lyria-go -transport http
    ```
    The MCP server will be available at `http://localhost:<PORT>/mcp`.
*   **SSE (Server-Sent Events)**:
    ```bash
    ./mcp-lyria-go -transport sse
    # SSE server typically runs on port 8081 by default in this configuration.
    ```
    The MCP server will be available at `http://localhost:8081`.

## Example

### Lyria Music Generation (Save to Local Directory)
```json
{
  "method": "tools/call",
  "params": {
    "name": "lyria_generate_music",
    "arguments": {
      "prompt": "An upbeat electronic track with a catchy melody, suitable for a retro video game.",
      "model_id": "lyria-3-clip-preview",
      "sample_count": 1,
      "local_path": "./lyria_output",
      "file_name": "my_retro_tune.wav"
    }
  }
}
```

### Lyria Music Generation (Save to GCS)
```json
{
  "method": "tools/call",
  "params": {
    "name": "lyria_generate_music",
    "arguments": {
      "prompt": "A calming ambient piece with piano and strings.",
      "output_gcs_bucket": "your-genmedia-output-bucket",
      "file_name": "calm_ambient.wav"
    }
  }
}
```

### Lyria Music Generation (Return Base64 Data)
```json
{
  "method": "tools/call",
  "params": {
    "name": "lyria_generate_music",
    "arguments": {
      "prompt": "A short, energetic rock riff."
    }
  }
}
```
