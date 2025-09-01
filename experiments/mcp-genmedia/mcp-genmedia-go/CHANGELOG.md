# Changelog

## 2025-08-31

*   **Feat:** Added `gemini_audio_tts` and `list_gemini_voices` tools to the `mcp-gemini-go` server to provide speech synthesis capabilities using Gemini TTS models.
*   **Feat:** The new tools support all 30 voices available in the Gemini TTS documentation.
*   **Feat:** Added a `gemini://language_codes` resource to the `mcp-gemini-go` server to list supported languages.
*   **Docs:** Updated the `mcp-gemini-go/README.md` with documentation and usage examples for the new TTS tools and resource.

## 2025-08-29

*   **Feat:** Added a new `mcp-gemini-go` server to provide an MCP interface for Google's Gemini models.
*   **Feat:** The new server includes a `gemini_image_generation` tool for multimodal (text and image) content generation.
*   **Fix:** Resolved multiple build and dependency issues in the new server, including correcting Go module versions and fixing compilation errors.
*   **Docs:** Updated the main project `README.md` to include the `mcp-gemini-go` server in the installation instructions and the list of available servers.
*   **Chore:** Improved the `install.sh` script to verify that the `PROJECT_ID` environment variable is set, preventing a common installation failure.

## 2025-08-14

*   **Feat:** The `mcp-veo-go` tool now generates descriptive, unique filenames for downloaded videos (e.g., `veo-veo-2.0-generate-001-20250814-153000-0.mp4`), matching the behavior of the Imagen tool.
*   **Fix:** The `mcp-veo-go` tool now automatically prepends `gs://` to the GCS bucket name if it is missing, preventing an "Unsupported output storage uri" error.
*   **Feat:** Added a new `EnsureGCSPathPrefix` helper function to `mcp-common` to provide a consistent way to normalize GCS paths.
*   **Chore:** Incremented the version number for `mcp-veo-go`.
*   **Fix:** Improved logging in `mcp-common` to clarify fallback behavior for environment variables.
*   **Feat:** Updated Imagen 4 model names to production versions.
*   **Chore:** Incremented the version number for `mcp-imagen-go`.

## 2025-07-31

*   **Feat:** Added prompt support to all MCP servers to eliminate the `prompts not supported` error.
*   **Feat:** Implemented a `list-voices` prompt in `mcp-chirp3-go` that lists available voices and can be filtered by language.
*   **Feat:** Added a `chirp://language_codes` resource to `mcp-chirp3-go` to expose the supported language codes.
*   **Feat:** Implemented a `generate-image` prompt in `mcp-imagen-go` that wraps the `imagen_t2i` tool.
*   **Feat:** Implemented a `generate-video` prompt in `mcp-veo-go` that wraps the `veo_t2v` tool.
*   **Feat:** Implemented a `generate-music` prompt in `mcp-lyria-go` that wraps the `lyria_generate_music` tool.
*   **Feat:** Implemented a `create-gif` prompt in `mcp-avtool-go` that wraps the `ffmpeg_video_to_gif` tool.
*   **Refactor:** Refactored the voice listing logic in `mcp-chirp3-go` into a reusable helper function.
*   **Chore:** Incremented the version number for all MCP servers.

## 2025-07-19

*   **Feat:** Implemented dynamic, model-specific constraints for `mcp-imagen-go` and `mcp-veo-go`. This includes support for model aliases (e.g., "Imagen 4", "Veo 3") and validation of parameters like image count, video duration, and aspect ratios based on the selected model.
*   **Refactor:** Centralized all model definitions and constraints for both Imagen and Veo into a new `mcp-common/models.go` file. This creates a single source of truth and simplifies future maintenance.
*   **Fix:** Restored the server startup logic in `mcp-imagen-go` to prevent the server from exiting prematurely.
*   **Refactor:** Updated `mcp-imagen-go` and `mcp-veo-go` to use the new centralized model configuration.
*   **Docs:** Updated the tool descriptions for `mcp-imagen-go` and `mcp-veo-go` to be self-describing, dynamically listing all supported models and their constraints.
*   **Docs:** Updated the `README.md` files for `mcp-imagen-go` and `mcp-veo-go` to refer to the new `mcp-common/models.go` file as the single source of truth.
*   **Docs:** Added a new "Architectural Pattern" section to the `GEMINI.md` file to document the new configuration-driven approach for model constraints.
*   **Docs:** Added detailed instructions for testing MCP servers with `mcptools` to the project's `GEMINI.md`.
*   **Test:** Added `verify.sh` scripts to `mcp-imagen-go` and `mcp-veo-go` to provide a mandatory, post-build liveness check.

## 2025-06-10

*   **Docs:** Added comprehensive Go documentation to all public functions and methods in the `mcp-avtool-go`, `mcp-chirp3-go`, `mcp-common`, `mcp-imagen-go`, `mcp-lyria-go`, and `mcp-veo-go` packages to improve code clarity and maintainability.

## 2025-06-07

*   **Refactor:** Simplified the shared `mcp-common` configuration by removing redundant and service-specific fields (`LyriaLocation`, `LyriaModelPublisher`, `DefaultLyriaModelID`).
*   **Refactor:** Updated `mcp-lyria-go` to use the general `Location` and manage its own constants for model publisher and ID, decoupling it from the shared config.
*   **Fix:** Removed incorrect and unreachable error handling for `common.LoadConfig()` from `veo-go`, `mcp-imagen-go`, and `mcp-lyria-go`.
*   **Feat:** Added support for custom API endpoints in `mcp-imagen-go` and `veo-go` via the `VERTEX_API_ENDPOINT` environment variable. This allows for easier testing against preview or sandbox environments.
*   **Fix:** Resolved build errors in all MCP modules.
*   **Refactor:** Refactored `mcp-avtool-go`, `mcp-imagen-go`, `mcp-lyria-go`, and `veo-go` to use the shared `mcp-common` module.
*   **Feat:** Instrumented `mcp-avtool-go`, `mcp-imagen-go`, `mcp-lyria-go`, and `veo-go` with OpenTelemetry for tracing.
*   **Fix:** Resolved `go mod tidy` dependency issues in `mcp-avtool-go` and `mcp-imagen-go`.
*   **Fix:** Corrected errors in `mcp-chirp3-go` and refactored to use the `mcp-common` package.
*   **Docs:** Added a `README.md` to the `mcp-common` package.
*   **Docs:** Updated the `README.md` in `mcp-avtool-go` to reflect the current capabilities of the service.
*   **Docs:** Added `compositing_recipes.md` to `mcp-avtool-go` to document the `ffmpeg` and `ffprobe` commands used.
*   **Docs:** Updated the root `README.md` with a "Developing MCP Servers for Genmedia" section.
