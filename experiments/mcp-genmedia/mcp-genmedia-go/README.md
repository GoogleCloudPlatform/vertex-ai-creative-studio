# MCP Servers for Genmedia: Go Implementations

This directory houses the Go language implementations of Model Context Protocol (MCP) servers designed to interface with Google Cloud's generative media APIs. Each subdirectory contains a standalone MCP server that can be built and run independently.

These servers enable MCP clients (such as AI agents or other applications) to leverage powerful media generation and manipulation capabilities.

## Getting Started: Installation

### Easy Installation (Recommended)

For a guided experience, you can use the interactive installer script. It will help you choose which MCP servers to install, check for prerequisites like Go, and provide instructions for configuring your system.

1.  **Run the Installer Script**
    From this `mcp-genmedia-go` directory, execute the following command:
    ```bash
    ./install.sh
    ```

2.  **Follow the On-Screen Instructions**
    The script will present you with a menu to install a single server or all of them. It will also check if Go is installed and if your `PATH` is configured correctly.

![run the install.sh](../assets/install-mcp-genmedia.gif)

### Manual Installation

This project uses a Go workspace (`go.work`) to manage the multiple modules. The following steps will ensure all dependencies are correctly synchronized and the server binaries are installed.

**Prerequisites:**
*   Go (version 1.18 or later is recommended for workspace support)
*   Git
*   Google Cloud CLI

**Instructions:**

1.  **Navigate to the Workspace Directory**
    All commands should be run from this `mcp-genmedia-go` directory.

2.  **Tidy Workspace Dependencies**
    This command synchronizes the dependencies between the modules in the workspace. This is a crucial step to avoid build errors.
    ```bash
    go work sync
    ```

3.  **Install the Binaries**
    This command explicitly builds and installs all the MCP server applications into your Go bin directory (`$GOPATH/bin` or `$GOBIN`).
    ```bash
    go install ./mcp-avtool-go ./mcp-chirp3-go ./mcp-gemini-go ./mcp-imagen-go ./mcp-lyria-go ./mcp-veo-go
    ```

4.  **Verify the Installation**
    Check that the binaries are available in your path.
    ```bash
    ls $(go env GOBIN)/mcp-*
    ```

### Validate the Installation

Before validating, ensure your Google Cloud project ID is set as an environment variable:
```bash
export PROJECT_ID=$(gcloud config get project)
# Or, if you prefer to set it manually:
# export PROJECT_ID="your-google-cloud-project-id"
```

With the MCP servers for genmedia installed, you can test that they're available by sending a STDIO "tools/list" command (substitute the MCP server in question as needed):

```bash
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | mcp-imagen-go
```
For a more readable output, you can pipe it to `jq` (if installed):
```bash
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | mcp-imagen-go | jq .
```

Either of these should result in a JSON response with a list of tools, similar to this (output truncated for brevity):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "imagen_t2i",
        "description": "Generate an image with Imagen 3...",
        // ... more tool details
      }
    ]
  }
}
```

## Using Prompts

In addition to tools, the MCP servers now support prompts, providing a more interactive and user-friendly way to access their core functionality. Prompts guide the user through a task, asking for required information if it's not provided.

### Listing and Using Prompts

You can list the available prompts for a server using the `prompts/list` method:

```bash
echo '{"jsonrpc":"2.0","method":"prompts/list","id":1}' | mcp-imagen-go | jq .
```

To use a prompt, you call the `prompts/get` method with the prompt's name and any required arguments. If you omit a required argument, the server will respond with a message asking for it.

**Example: Using the `generate-image` prompt with `mcp-imagen-go`**

```bash
# Call the prompt with a required argument
export PROJECT_ID=$(gcloud config get project)
echo '{"jsonrpc":"2.0","method":"prompts/get","id":2,"params":{"name":"generate-image","arguments":{"prompt":"a futuristic cityscape at sunset"}}}' | mcp-imagen-go | jq .

# Call the prompt without a required argument
echo '{"jsonrpc":"2.0","method":"prompts/get","id":3,"params":{"name":"generate-image"}}' | mcp-imagen-go | jq .
```

This will result in a more conversational interaction, making the servers easier to use for interactive clients.

## Client Configurations

The MCP servers can be used with various clients and hosts. A sample MCP configuration JSON can be found at [genmedia-config.json](../sample-agents/mcp-inspector/genmedia-config.json).

This repository provides AI application samples for:

*   [Google ADK (Agent Development Kit)](../sample-agents/adk/README.md)
*   [Google Firebase Genkit](../sample-agents/genkit/README.md)
*   [Google Gemini CLI](../sample-agents/geminicli/README.md)


## Available Go MCP Servers:

*   **`mcp-avtool-go`**:
    *   Provides audio/video compositing and manipulation tools by instrumenting `ffmpeg` and `ffprobe`.
    *   Capabilities include media info retrieval, format conversion (e.g., WAV to MP3), GIF creation, combining audio/video, overlaying images, concatenating files, volume adjustment, and audio layering.
    *   Supports local file paths and GCS URIs for inputs/outputs.

*   **`mcp-chirp3-go`**:
    *   Offers Text-to-Speech (TTS) synthesis using Google Cloud TTS with Chirp3-HD voices.
    *   Tools: `chirp_tts` for synthesis (with custom pronunciation support) and `list_chirp_voices` for discovering available voices.
    *   Audio can be returned as base64 data or saved to a local directory.

*   **`mcp-gemini-go`**:
    *   Provides a multimodal interface to Google's Gemini models.
    *   Tools include `gemini_image_generation` for generating text and images, and `gemini_audio_tts` for synthesizing speech with Gemini TTS models.
    *   Also includes the `list_gemini_voices` helper tool and the `gemini://language_codes` resource.
    *   Output can be saved to a local directory or GCS.

*   **`mcp-imagen-go`**:
    *   Enables image generation using Google's Imagen models via Vertex AI.
    *   Tool: `imagen_t2i` for text-to-image generation.
    *   Supports various parameters like aspect ratio and number of images. Output can be directed to GCS, saved locally (including download from GCS if API saves there), or returned as base64 data.

*   **`mcp-lyria-go`**:
    *   Facilitates music generation using Google's Lyria models via Vertex AI.
    *   Tool: `lyria_generate_music` for creating music from text prompts.
    *   Supports parameters like negative prompts and seed. Output can be directed to GCS, saved locally, or returned as base64 data.

*   **`mcp-veo-go`**:
    *   Provides video generation capabilities using Google's Veo models via Vertex AI.
    *   Tools: `veo_t2v` (text-to-video) and `veo_i2v` (image-to-video).
    *   Supports parameters like aspect ratio and duration. Videos are saved to GCS by the API and can optionally be downloaded to a local directory.

## Common Features:

*   **Transport Protocols**: Most servers support `stdio` (default), `http` (streamable HTTP with CORS), and `sse` (Server-Sent Events, legacy) transports.
*   **Google Cloud Authentication**: Relies on Application Default Credentials (ADC) or service account keys.

## Configuration (Environment Variables)

All servers in this project are configured using environment variables. While some servers have unique variables, the following are common to most of them:

### Using a `.env` File

For easier local development, you can place a `.env` file in the directory where you run the MCP server. The server will automatically load environment variables from this file.

**Precedence Order:**

1.  **Environment variables set in the shell:** These take the highest precedence.
2.  **Variables in the `.env` file:** These are loaded but will **not** override any variables already set in your shell.

This allows you to have default values in your `.env` file and override them for specific cases by setting the variable in your terminal.

**Available Variables:**

The following variables can be defined in your `.env` file or as shell environment variables:

*   `PROJECT_ID` (string): **Required**. Your Google Cloud Project ID. The application will terminate if this is not set.
*   `LOCATION` (string): The Google Cloud location/region for Vertex AI services. Defaults to `us-central1` if not set.
*   `GENMEDIA_BUCKET` (string): An optional default Google Cloud Storage bucket to use for GCS outputs if a bucket is not specified in a tool request.
*   `PORT` (string): Specifies the port for the `http` transport. If not set, it defaults to `8080`. Note that for the `sse` transport, most servers use a hardcoded port (typically `8081`) to avoid conflicts.

*Example:*
```bash
export PROJECT_ID="your-google-cloud-project-id"
export LOCATION="us-central1"
```

### Local Development & OpenTelemetry

When running the MCP servers locally, you may want to connect to a local OpenTelemetry (OTel) collector for tracing. By default, the servers attempt a secure (TLS) connection. If your local collector is running in insecure mode, you will need to set the following environment variable to disable TLS:

```bash
# This tells the application to use an insecure connection for the OTLP exporter.
export OTEL_EXPORTER_OTLP_INSECURE=true
```

When deploying the application to a production environment (like GKE, Cloud Run, etc.), you should **not** set this variable. The application will correctly default to requiring a secure TLS connection to the OTel collector.

You can also specify the OTel collector endpoint using an environment variable:

```bash
# Example for a local collector
export OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"
```
If `OTEL_EXPORTER_OTLP_ENDPOINT` is not set, it will default to `localhost:4317`.

Please refer to the `README.md` file within each server's subdirectory for detailed information on its specific tools, parameters, environment variables, and usage examples.

## Developing MCP Servers for Genmedia

This section provides guidance on how to understand the architecture and extend or create a new MCP server for Genmedia.

### Architecture

The MCP servers in this repository are all structured in a similar way. They all use the `mcp-common` package for configuration, file handling, and OpenTelemetry. They all use the `mcp-go` library to create the MCP server and tools. They all support the same transport protocols (`stdio`, `http`, and `sse`).

The `mcp-common` package provides the following functionality:

*   **Configuration**: The `config.go` file provides a way to load configuration from environment variables.
*   **File Utilities**: The `file_utils.go` file provides utility functions for working with files.
*   **GCS Utilities**: The `gcs_utils.go` file provides utility functions for working with Google Cloud Storage.
*   **OpenTelemetry**: The `otel.go` file provides a function for initializing OpenTelemetry.

### Extending an Existing Server

To extend an existing server, you'll need to do the following:

1.  Add a new tool to the server. You can do this by calling the `AddTool` method on the `server.MCPServer` struct.
2.  Implement the tool's handler function. The handler function will be called when the tool is invoked. The handler function should take a `context.Context` and a `mcp.CallToolRequest` as input and should return a `mcp.CallToolResult` and an error.

### Creating a New Server

To create a new server, you'll need to do the following:

1.  Create a new directory for the server.
2.  Create a new `go.mod` file for the server.
3.  Create a new `main.go` file for the server.
4.  In the `main.go` file, you'll need to do the following:
    1.  Create a new `server.MCPServer` struct.
    2.  Add one or more tools to the server.
    3.  Start the server.
