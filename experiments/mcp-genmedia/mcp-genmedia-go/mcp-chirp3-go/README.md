# MCP Chirp 3 HD Server 

This tool provides Text-to-Speech (TTS) capabilities using Google Cloud TTS with Chirp3-HD voices. It is one of the MCP tools for Google Cloud Genmedia services, acting as an MCP server component to enable LLMs and other MCP clients to synthesize speech.

## MCP Tool Definitions

The following tools are exposed by this server:

### 1. `chirp_tts`

*   **Description**: Synthesizes speech from text using Google Cloud TTS with Chirp3-HD voices. Returns audio data and optionally saves it locally.
*   **Handler**: `chirpTTSHandler`
*   **Parameters**:
    *   `text` (string, required): The text to synthesize into speech.
    *   `voice_name` (string, optional): The specific Chirp3-HD voice name to use (e.g., "en-US-Chirp3-HD-Zephyr").
        *   If not provided, defaults to "en-US-Chirp3-HD-Zephyr" if available, otherwise the first available Chirp3-HD voice.
    *   `output_filename_prefix` (string, optional): A prefix for the output WAV filename if saving locally. A timestamp and .wav extension will be appended.
        *   Default: `"chirp_audio"`
    *   `output_directory` (string, optional): If provided, specifies a local directory to save the generated audio file to. Filenames will be generated automatically using the prefix. If not provided, audio data is returned in the response.
    *   `pronunciations` (array of strings, optional): An array of custom pronunciations. Each item should be a string in the format 'phrase:phonetic_representation' (e.g., 'tomato:təˈmeɪtoʊ'). All items must use the same encoding specified by `pronunciation_encoding`.
    *   `pronunciation_encoding` (string, optional, enum: "ipa", "xsampa"): The phonetic encoding used for the `pronunciations` array.
        *   Default: `"ipa"`

### 2. `list_chirp_voices`

*   **Description**: Lists Chirp3-HD voices, filtered by the provided language (either descriptive name or BCP-47 code).
*   **Handler**: `listChirpVoicesHandler`
*   **Parameters**:
    *   `language` (string, required): The language to filter voices by. Can be a descriptive name (e.g., 'English (United States)') or a BCP-47 code (e.g., 'en-US').

## Environment Variable Configuration

The tool utilizes the following environment variables:

*   `GOOGLE_CLOUD_PROJECT` (string): **Required**. Your Google Cloud Project ID. The application will terminate if this is not set. Note: `PROJECT_ID` is also supported as a fallback.
    *   **Override**: You can override this globally for this specific server by setting `CHIRP3_PROJECT_ID`.
*   `GOOGLE_CLOUD_LOCATION` (string): The preferred Google Cloud region for Chirp3-HD services. Supported regions are: `global`, `us`, `eu`, `asia-southeast1`, `europe-west2`, and `asia-northeast1`.
    *   Default: `"global"` (Note: if you inherit `"us-central1"` from a generic `.env` file, the server will automatically map it to `"us"` or `"global"` to prevent errors, as Chirp3-HD does not support `us-central1`).
    *   **Fallback**: `LOCATION` is also supported as a fallback for `GOOGLE_CLOUD_LOCATION`.
    *   **Override**: You can override this globally for this specific server by setting `CHIRP3_LOCATION`.
*   `PORT` (string, for HTTP/SSE transport): The port for the server to listen on if using HTTP or SSE transport.
    *   Default for HTTP: `"8080"` (from `getEnv` call in `main` for HTTP).
    *   Default for SSE: `"8081"` (if `-p` flag is not used and transport is `sse`). The `-p` flag can override this.

## Transports Supported

*   `stdio` (default)
*   `sse` (Server-Sent Events)
*   `http` (Streamable HTTP)

CORS is enabled for the HTTP transport, allowing all origins by default.

## Run

Build the tool using `go build` or `go install`.

*   **STDIO (Default)**:
    ```bash
    ./mcp-chirp3-go
    # or
    ./mcp-chirp3-go -transport stdio
    ```
*   **HTTP**:
    ```bash
    ./mcp-chirp3-go -transport http 
    # Optionally set PORT environment variable, e.g., PORT=8082 ./mcp-chirp3-go -transport http
    ```
    The MCP server will be available at `http://localhost:<PORT>/mcp`.
*   **SSE (Server-Sent Events)**:
    ```bash
    ./mcp-chirp3-go -transport sse -p <SSE_PORT>
    # Example: ./mcp-chirp3-go -transport sse -p 8081
    ```
    The MCP server will be available at `http://localhost:<SSE_PORT>`.

## Examples

### List Chirp Voices
```json
{
  "method": "tools/call",
  "params": {
    "name": "list_chirp_voices",
    "arguments": {
      "language": "english (australia)"
    }
  }
}
```

### Chirp TTS Synthesis
```json
{
  "method": "tools/call",
  "params": {
    "name": "chirp_tts",
    "arguments": {
      "text": "Hello from the Model Context Protocol and Chirp3!",
      "voice_name": "en-US-Chirp3-HD-Zephyr",
      "output_directory": "./audio_output" 
    }
  }
}
```
