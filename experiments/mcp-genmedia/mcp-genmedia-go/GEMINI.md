# MCP Tools for Generative Media - Common Development Guidance

This document provides common guidance for developing and testing the generative media MCP tools.

## General Guidance

### **CRITICAL: Versioning and Changelog**

After making **any** functional or logical code changes, you **must** update both the version number in the code and the `CHANGELOG.md` file. This is not an optional step.

1.  **Increment Version**: In the core MCP code file (e.g., `imagen.go`, `veo.go`), find the `version` constant. Increment it according to the significance of your changes and update the comment to reflect the changes made.

2.  **Update Changelog**: Open the `CHANGELOG.md` file in the `mcp-genmedia-go` directory. Add a new entry for the current date and a bulleted list of the changes you made. Use the existing format and tags (e.g., `**Feat:**`, `**Fix:**`, `**Docs:**`) as a guide.

### Architectural Pattern: Model-Specific Constraints

For MCP tools that support different "models" (e.g., `Imagen 3` vs. `Imagen 4`, `Veo 2` vs. `Veo 3`), we use a centralized, configuration-driven approach to manage model-specific parameters and constraints.

**The Single Source of Truth: `mcp-common/models.go`**

All model definitions reside in `mcp-genmedia-go/mcp-common/models.go`. This file contains:
1.  **`...ModelInfo` Structs**: Data structures that define the unique constraints for each model family (e.g., `ImagenModelInfo`, `VeoModelInfo`).
2.  **`Supported...Models` Maps**: A map for each model family that holds the specific constraint values for every supported model and its aliases.

**Workflow for Adding or Modifying a Model:**

When you need to add a new model or change the parameters of an existing one, follow this pattern:

1.  **Update `mcp-common/models.go`**: 
    *   Add or modify the entry in the appropriate `Supported...Models` map. This is the **only** place where you should define constraints like max images, duration, or supported aspect ratios.

2.  **Update the Server's Handler (`handlers.go`)**: 
    *   The handler logic **must** use the helper functions from `mcp-common` (e.g., `ResolveVeoModel`) to get the model's specific constraints.
    *   It should then validate and, if necessary, adjust the user's input parameters against these constraints (e.g., clamping `num_videos` to the model's `MaxVideos`). Always log a warning when an adjustment is made.

3.  **Update the Server's Tool Definition (`veo.go`, `imagen.go`)**: 
    *   The `model` parameter's description **must** be generated dynamically by calling the appropriate function from `mcp-common` (e.g., `BuildVeoModelDescription`). This ensures the tool's help text is always in sync with the supported models.
    *   Other model-dependent parameter descriptions should be generic (e.g., "Note: the maximum is model-dependent.").

4.  **Update the `README.md`**: 
    *   The `README.md` for the specific server should *not* contain a table of models. Instead, it should refer to `mcp-common/models.go` as the single source of truth.

This pattern ensures that our tools are robust, self-describing, and easy to maintain.

### Enabling Server Capabilities

The MCP Server is modular. Features like `tools`, `prompts`, and `resources` must be explicitly enabled during server initialization. If you encounter errors like 'resources not supported', ensure you are passing the correct `server.With...Capabilities()` option to the `server.NewMCPServer()` constructor in the `main.go` file for the relevant server.

**Example (enabling resources):**
```go
s := server.NewMCPServer(
    "MyServer", 
    "1.0.0",
    server.WithResourceCapabilities(true, true), // This enables resource listing and change notifications
)
```

## Testing

### **CRITICAL: Environment Variables**

Before running **any** verification or installation command (including `verify.sh` and `install.sh`), you **MUST** ensure the `PROJECT_ID` environment variable is set. The servers will fail to initialize and time out without it.

**Example:**
```bash
export PROJECT_ID=$(gcloud config get project)
```

### Mandatory Post-Build Verification

After **any** code change to an MCP server, you **must** run the corresponding `verify.sh` script from the server's directory (e.g., `mcp-imagen-go/verify.sh`).

```bash
./verify.sh
```

**Troubleshooting Timeouts:** If `verify.sh` or other commands time out, the *first* thing to check is that the `PROJECT_ID` environment variable is correctly set for the shell session running the command.

A successful build (`go build`) is **not sufficient**. This script performs a basic "liveness" check by calling the `tools` command with `mcptools`. If the script completes successfully, it confirms that the server builds and is responsive to basic MCP requests. This is the primary guardrail against regressions that cause the server to fail silently on startup.

You should also run the standard Go tests:

```bash
go test ./...
```

### **New Rule: Standardized Verification**

After making any code change to an MCP server, you **must** ensure a `verify.sh` script exists and is up-to-date. If a script does not exist, you must create one by adapting the script from a neighboring MCP server (e.g., `mcp-gemini-go`). All `verify.sh` scripts should perform a basic build and liveness check by calling `mcptools tools`.

### Manual Testing with `mcptools`

The standard way to manually test `stdio`-based MCP servers is with the `mcptools` binary. For more information on `mcptools`, you can read its [README](https://raw.githubusercontent.com/f/mcptools/refs/heads/master/README.md).

#### `call` Command Syntax

The primary command for testing is `mcptools call`. The correct syntax is:

```bash
mcptools call <tool_name> --params '<json_payload>' <path_to_server_binary>
```

*   `<tool_name>`: The name of the tool to call (e.g., `imagen_t2i`).
*   `--params '<json_payload>'`: The arguments for the tool, provided as a single, quoted JSON string.
*   `<path_to_server_binary>`: The path to the compiled MCP server executable.

**Important:** Ensure any required environment variables (like `PROJECT_ID`) are set for the command.

#### Example

This example calls the `imagen_t2i` tool from the `mcp-imagen-go` server with specific parameters.

```bash
export PROJECT_ID=genai-blackbelt-fishfooding

mcptools call imagen_t2i \
  --params '{"prompt": "a majestic lion", "model":"Imagen 3", "output_directory":"./test_output"}' \
  mcp-genmedia-go/mcp-imagen-go/mcp-imagen-go
```

### End-to-End Test Plan

End to end tests are only performed when the MCP Servers for Genmedia are installed and available through a valid MCP Client, such as geminicli.

This document outlines the steps to test the available genmedia tools.

For each test run, create a new directory named with the current date and time (e.g., `test_run_YYYYMMDD_HHMMSS`) within the local output directory to store the results.

*Note: Generative tool calls (Imagen, Veo, Lyria) may occasionally fail or time out. If a generation step fails, retrying or using a pre-existing file for subsequent steps (especially FFmpeg operations) may be necessary to complete the test plan.*

1.  Generate 1-4 images using `imagen_t2i`
    *   Use Imagen 3
2.  Generate 1-4 images using `imagen_t2i`
    *   Use Imagen 4
3.  Generate 1-4 videos from text using `veo_t2v` (using veo-2.0).
    *   Use the `output_file_name` parameter to rename the output appropriately.
4.  Generate 1-4 videos from a random image generated in step 1 using `veo_i2v` (using veo-2.0).
5.  Generate 1-4 8-second videos from text using `veo_t2v` with `veo-3.0-generate-preview`.
    *   Use the `output_file_name` parameter to name the output `veo_t2v_veo3_test_video.mp4`.
6.  Generate 1-4 videos from a random image generated in step 2 using `veo_i2v` with `veo-3.0-generate-preview`.
7.  Generate music using `lyria_generate_music`.
    *   Suggest adding duration to the prompt (e.g., "Upbeat electronic music, 8 seconds long").
8.  List available Chirp voices using `list_chirp_voices`.
9.  Generate speech using `chirp_tts`.
    *   Choose and utilize a voice from the list obtained in step 8.
10. Adjust the volume of the speech to be louder than the music for layering. A good starting point is to raise the speech by +10dB using `ffmpeg_adjust_volume`.
11. Convert the speech generated in step 9 (if WAV) to MP3 using `ffmpeg_convert_audio_wav_to_mp3`.
12. Layer the music generated in step 7 and the adjusted speech from step 10 using `ffmpeg_layer_audio_files`.
13. Concatenate the original speech from step 9 and the adjusted speech from step 10 using `ffmpeg_concatenate_media_files`.
14. Get media information for the video generated in step 3 using `ffmpeg_get_media_info`.
15. Combine the video generated in step 3 with the layered audio from step 12 using `ffmpeg_combine_audio_and_video`.
16. Overlay the image generated in step 1 onto the video generated in step 3 using `ffmpeg_overlay_image_on_video`.
17. Convert the video generated in step 3 to a GIF using `ffmpeg_video_to_gif`.

Once complete, output a report with all prompts used for each model along with the status of the result and filepath of the result (if successful), in two formats, Markdown and JSON:

*   **Report JSON Format**: This report should also be written as a JSON file `report.json` in the test run directory with the following structure.

    ```json
    {
        "test_run": "YYYYMMDD_HHMMSS",
        "total_time_taken": "HH:MM:SS",
        "results": [
            {
                "tool": "tool_name",
                "model": "model_name",
                "prompt": "prompt_text",
                "status": "Success" | "Failed (error_message)",
                "filepath": "/path/to/output_file" | null,
                "tool_parameters": {}
            },
            // ... more results
        ]
    }
    ```

*   **Report Markdown Format**: Convert this JSON file to a Markdown table in a file named `report.md` in the same directory:

*Note: When using `output_directory` with `veo_t2v` or `veo_i2v`, the downloaded file is typically named `sample_0.mp4` (or similar) regardless of the `output_file_name` parameter. To prevent overwriting, ensure you rename the downloaded file immediately after generation if you plan to generate multiple videos to the same directory.*

All generated media will be saved to the GCS bucket `gs://genai-blackbelt-fishfooding-assets` and also downloaded locally to `/Users/ghchinoy/genmedia/genmedia_mcp_tool_test/tool_test_run`.