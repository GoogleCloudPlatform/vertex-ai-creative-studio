# Environment Variables

This document lists environment variables used by the MCP servers in this repository.

*   `ALLOW_UNSAFE_MODELS` (boolean): Optional (`true`/`false`). Allows users to bypass strict local model constraint validation, enabling them to test experimental or pre-release model strings that are not yet hardcoded in the registry. Defaults to `false`.
*   `ENABLE_OPTIONAL_HEADER_CAPTURE` (boolean): Optional (`true`/`false`). Intended for internal debugging. When set to `true`, the server intercepts API requests and injects the raw ADC Bearer token to capture and surface the `x-goog-sherlog-link` header in the tool output. This feature is supported for Imagen, Gemini, NanoBanana, and Lyria, but currently not supported for Veo due to Go SDK limitations with long-running operations. Defaults to `false`.
