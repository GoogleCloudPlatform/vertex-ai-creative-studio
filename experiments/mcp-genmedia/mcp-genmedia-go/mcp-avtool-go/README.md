# AV Compositing Tool (avtool)

Version: 2.0.0

## Overview

`avtool` is a versatile Model Context Protocol (MCP) server designed for various audio and video processing tasks. It leverages powerful command-line utilities like FFMpeg and FFprobe to offer a range of compositing and media manipulation capabilities. This tool can be run with different transport protocols (STDIO, HTTP (Streamable HTTP), SSE) to integrate into various workflows.

## Features

The `avtool` provides the following functionalities, exposed as MCP tools:

*   **`ffmpeg_get_media_info`**:
    *   Retrieves detailed information about a media file (streams, format, metadata, etc.) using `ffprobe`.
    *   Input: URI of the media file (local path or GCS URI).
    *   Output: JSON string containing the media information.

*   **`ffmpeg_convert_audio_wav_to_mp3`**:
    *   Converts WAV audio files to MP3 format.
    *   Input: URI of the input WAV audio file.
    *   Output: MP3 audio file. Can be saved locally and/or to a GCS bucket.

*   **`ffmpeg_video_to_gif`**:
    *   Creates an animated GIF from an input video file.
    *   Uses a two-pass FFMpeg process (palette generation and use) for optimal quality.
    *   Inputs: URI of the input video file, scale width factor, FPS.
    *   Output: GIF image file. Can be saved locally and/or to a GCS bucket.

*   **`ffmpeg_combine_audio_and_video`**:
    *   Combines a separate video file and an audio file into a single video file with the new audio track.
    *   Inputs: URI of the input video file, URI of the input audio file.
    *   Output: Combined video file (e.g., MP4). Can be saved locally and/or to a GCS bucket.

*   **`ffmpeg_overlay_image_on_video`**:
    *   Overlays a static image onto a video at specified X/Y coordinates.
    *   Inputs: URI of the input video file, URI of the input image file, X coordinate, Y coordinate.
    *   Output: Video file with the image overlay. Can be saved locally and/or to a GCS bucket.

*   **`ffmpeg_concatenate_media_files`**:
    *   Concatenates multiple media files (videos or audios) into a single output file.
    *   **Behavior for WAV output**: If the intended output file has a `.wav` extension, all input files *must* be PCM WAV audio files. The tool will attempt to directly concatenate them, preserving the PCM audio codec. If any input is not a PCM WAV file, or if PCM WAV inputs have differing characteristics (sample rate, sample format, channel count), the operation is rejected. The error message will guide the user to either:
    a) Convert all inputs to a common PCM WAV format using an external tool if precise WAV-to-WAV characteristic changes are needed.
    b) Convert inputs to a compatible intermediate format like MP3 (using `ffmpeg_convert_audio_wav_to_mp3` if applicable) and then concatenate to a more flexible output format like M4A.
    c) Choose a different output format directly (e.g., M4A, MP4) for the concatenation, which allows `avtool` to handle the necessary conversions.
    *   **Behavior for other outputs (e.g., MP4, M4A)**: For non-WAV outputs, or if inputs are video/mixed, the tool employs a two-stage process: first standardizing inputs (e.g., to common resolution/FPS for video, and AAC audio in an MP4 container), then concatenating these standardized files using the FFMpeg concat demuxer for robustness.
    *   Input: Array of URIs for the input media files.
    *   Output: Concatenated media file. Can be saved locally and/or to a GCS bucket.

*   **`ffmpeg_adjust_volume`**:
    *   Adjusts the volume of an audio file by a specified decibel (dB) amount.
    *   Inputs: URI of the input audio file, volume change in dB.
    *   Output: Audio file with adjusted volume. Can be saved locally and/or to a GCS bucket.

*   **`ffmpeg_layer_audio_files`**:
    *   Layers (mixes) multiple audio files together into a single audio track.
    *   Input: Array of URIs for the input audio files.
    *   Output: Mixed audio file. Can be saved locally and/or to a GCS bucket.

## Requirements

*   **Go**: Version 1.18 or higher (as per `go.mod` if specified, otherwise latest stable).
*   **FFMpeg**: Must be installed and accessible in the system PATH.
*   **FFprobe**: Must be installed and accessible in the system PATH (usually comes with FFMpeg).
*   **Google Cloud Storage (Optional)**: For reading inputs from or writing outputs to GCS, appropriate credentials and setup are required.

## Configuration

The tool is configured using environment variables:

*   `MCP_CUSTOM_PATH`: (Optional) Overrides the system `PATH` for `ffmpeg` and `ffprobe` tool executions. Useful for pointing to custom binary installations (e.g., Homebrew) without polluting the host environment.
*   `GOOGLE_CLOUD_PROJECT`: (Required for GCS operations) Your Google Cloud Project ID. Note: `PROJECT_ID` is also supported as a fallback.
    *   **Override**: You can override this globally for this specific server by setting `AVTOOL_PROJECT_ID`.
*   `GENMEDIA_BUCKET`: (Optional) Default Google Cloud Storage bucket to use for outputs if not specified in the tool request.
*   `LOCATION`: (Optional) Google Cloud location (e.g., `us-central1`). Defaults to `us-central1`. Primarily for GCS client initialization context.
*   `PORT`: (Optional, for HTTP transport) The port for the HTTP server to listen on. Defaults to `8080`.

## Running the Tool

Build the tool using `go build` in the project directory.

Run the compiled executable with a transport flag:

*   **STDIO (Default)**:
    ```bash
    ./avtool
    # or
    ./avtool -transport stdio
    ```
*   **HTTP**:
    ```bash
    ./avtool -transport http
    # Optionally set PORT environment variable, e.g., PORT=8081 ./avtool -transport http
    ```
    The MCP server will be available at `http://localhost:<PORT>/mcp`.
*   **SSE (Server-Sent Events)**:
    ```bash
    ./avtool -transport sse
    ```
    The MCP server will be available at `http://localhost:8081` (default SSE port).

## How to Use

`avtool` acts as an MCP (Media Control Protocol) server. Client applications can interact with it by sending MCP `CallToolRequest` messages (e.g., via JSON-RPC) to invoke the features listed above. The server will process the request, perform the media operations, and return an `mcp.CallToolResult`.

Input files can be specified as local file system paths or as GCS URIs (e.g., `gs://your-bucket/path/to/file.mp4`).
Output files can be saved to a specified local directory and/or uploaded to a GCS bucket. If no output locations are specified, temporary files are created for processing and then cleaned up.

## Development

For a detailed description of the `ffmpeg` and `ffprobe` commands used in this service, see the `compositing_recipes.md` file.

The codebase is structured as follows:

*   `avtool.go`: Main application entry point, MCP server setup, transport handling.
*   `mcp_handlers.go`: MCP tool registration and the top-level handler functions for each tool.
*   `ffmpeg_commands.go`: Functions that build and execute FFMpeg commands.
*   `ffprobe_commands.go`: Functions that build and execute FFprobe commands.

The `mcp-common` package provides common functionality for configuration, file handling, and GCS operations.

To add a new tool:
1.  Define the FFMpeg/FFprobe command logic (if new) in `ffmpeg_commands.go` or `ffprobe_commands.go`.
2.  Create a new handler function in `mcp_handlers.go`.
3.  Register the tool in `avtool.go` by calling the `add<NewToolName>Tool(s, cfg)` function.
