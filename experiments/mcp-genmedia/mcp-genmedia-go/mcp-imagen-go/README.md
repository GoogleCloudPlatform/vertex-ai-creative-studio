# MCP Imagen Server

This tool provides image generation capabilities using Google's Imagen models (via Vertex AI). It is one of the MCP tools for Google Cloud Genmedia services, functioning as an MCP server component to allow LLMs and other MCP clients to generate images from text prompts.

## MCP Tool Definition

The following tool is exposed by this server:

### 1. `imagen_t2i`

*   **Description**: Generates an image based on a text prompt using Google's Imagen models. The image can be returned as base64 data, saved to a local directory, or stored in a Google Cloud Storage bucket.
*   **Handler**: `imagenGenerationHandler` (via wrapper)
*   **Parameters**:
    *   `prompt` (string, required): Prompt for text to image generation.
    *   `model` (string, optional): The model for image generation. Can be a full model ID or a common alias. See the `mcp-common/models.go` file for a complete list of supported models and aliases.
    *   `num_images` (number, optional): Number of images to generate.
        *   Default: `1`
        *   Note: The maximum number of images depends on the selected model (see table above).
    *   `aspect_ratio` (string, optional): The aspect ratio for the generated image.
        *   Default: `"1:1"`
        *   Common values: `"1:1"` (square), `"16:9"` (widescreen), `"9:16"` (portrait)
    *   `gcs_bucket_uri` (string, optional): GCS URI prefix to store the generated images (e.g., "your-bucket/outputs/" or "gs://your-bucket/outputs/"). If provided, images are saved to GCS instead of returning bytes directly.
    *   `output_directory` (string, optional): If provided, specifies a local directory to save the generated image(s) to.

### Resources

The server exposes the following resources:

*   `imagen://models`: Returns a JSON object detailing the supported Imagen models and their aliases. You can read this resource using `mcptools resources get imagen://models ./mcp-imagen-go`.
*   `imagen://segmentation_classes`: Returns a JSON object of supported classes for semantic masking in image editing.

## Environment Variable Configuration

The tool utilizes the following environment variables:

*   `PROJECT_ID` (string): **Required**. Your Google Cloud Project ID. The application will terminate if this is not set.
*   `LOCATION` (string): The Google Cloud location/region for Vertex AI services.
    *   Default: `"us-central1"`
*   `GENMEDIA_BUCKET` (string): An optional default Google Cloud Storage bucket to use for GCS outputs if `gcs_bucket_uri` is not specified in the tool request. The path `imagen_outputs/` will be appended to this bucket.
    *   Default: `""` (empty string, meaning no default GCS output path is formed from this variable unless `gcs_bucket_uri` is also absent).
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
    ./mcp-imagen-go
    # or
    ./mcp-imagen-go -transport stdio
    ```
*   **HTTP**:
    ```bash
    ./mcp-imagen-go -transport http
    # Optionally set PORT environment variable, e.g., PORT=8083 ./mcp-imagen-go -transport http
    ```
    The MCP server will be available at `http://localhost:<PORT>/mcp`.
*   **SSE (Server-Sent Events)**:
    ```bash
    ./mcp-imagen-go -transport sse
    # SSE server typically runs on port 8081 by default in this configuration.
    ```
    The MCP server will be available at `http://localhost:8081`.

## Example

### Imagen Text-to-Image Generation
```json
{
  "method": "tools/call",
  "params": {
    "name": "imagen_t2i",
    "arguments": {
      "prompt": "A photorealistic image of a cat wearing a small wizard hat, sitting on a pile of ancient books.",
      "model": "imagen-3.0-generate-002",
      "num_images": 1,
      "aspect_ratio": "1:1",
      "output_directory": "./imagen_output"
    }
  }
}
```
