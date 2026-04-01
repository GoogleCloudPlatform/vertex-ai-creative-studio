# Environment Variables

This document lists environment variables used by the MCP servers in this repository.

| Variable | Required | Description | Default | Servers |
| :--- | :--- | :--- | :--- | :--- |
| `GOOGLE_CLOUD_PROJECT` | Yes | The primary Google Cloud Project ID used for API calls and GCS operations. | None | All |
| `PROJECT_ID` | Fallback | Legacy fallback for `GOOGLE_CLOUD_PROJECT`. | None | All |
| `<PREFIX>_PROJECT_ID` | No | Server-specific override for `GOOGLE_CLOUD_PROJECT` (e.g., `VEO_PROJECT_ID`, `IMAGEN_PROJECT_ID`). | None | All |
| `GOOGLE_CLOUD_LOCATION` | No | The preferred Google Cloud location/region for Vertex AI services (e.g., `us-central1`, `europe-west2`). | `us-central1`* | All |
| `LOCATION` | Fallback | Fallback for `GOOGLE_CLOUD_LOCATION`. | `us-central1`* | All |
| `<PREFIX>_LOCATION` | No | Server-specific override for location (e.g., `CHIRP3_LOCATION=eu`). | None | All |
| `ALLOW_UNSAFE_MODELS` | No | Optional (`true`/`false`). Allows users to bypass strict local model constraint validation to test experimental or pre-release model strings. | `false` | Veo, Imagen, Gemini, NanoBanana, Lyria |
| `ENABLE_OPTIONAL_HEADER_CAPTURE` | No | Optional (`true`/`false`). Intended for internal debugging. Injects raw Bearer token to capture `x-goog-sherlog-link`. | `false` | Imagen, Gemini, NanoBanana, Lyria |
| `GENMEDIA_BUCKET` | No | A default GCS bucket to use for outputs if one isn't specified in a tool request. | None | All |
| `VERTEX_API_ENDPOINT` | No | Overrides the Base URL of the Vertex AI client for testing against staging, preview, or sandbox environments. | None | Veo, Imagen, Gemini, NanoBanana, Lyria |
| `GCS_DOWNLOAD_TIMEOUT` | No | Timeout for GCS download/streaming operations. Accepts Go duration strings (e.g. `"30s"`, `"5m"`). | `5m` | All |
| `MCP_CUSTOM_PATH` | No | Overrides the system `PATH` for `ffmpeg` and `ffprobe` tool executions. | None | AVTool |
| `PORT` | No | Specifies the port for the `http` transport. | `8080` | All |
| `OTEL_ENABLED` | No | Enables OpenTelemetry tracing when set to `true`. | `false` | All |

*\*Note: `mcp-chirp3-go` dynamically falls back to `global` if it detects the default `us-central1` region, as Chirp3-HD does not support that region.*
