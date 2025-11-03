# Pixie Compositor Web Component

## Overview

The `pixie-compositor` is a powerful, headless Lit-based web component that provides in-browser video and audio processing using `ffmpeg.wasm`. It is designed to be a generic engine that can execute a variety of `ffmpeg` commands, controlled from a Mesop application.

## Current Functionality

As of the initial implementation, this component is a direct copy of the `worsfold-encoder` and is configured to perform video-to-GIF conversion.

## Future Vision (Phase 6 and beyond)

This component will be refactored to become a generic `ffmpeg` engine. It will accept a list of input files and a set of command-line arguments, and it will return the resulting output files. This will allow it to be used as the foundation for a suite of media manipulation tools, such as:

*   Video concatenation
*   Audio layering
*   Video resizing and compression
*   And more...

## Usage

The component is controlled from Python. You pass it the necessary input files and command arguments, and it communicates its status and results back to the Mesop application through a series of events.

```python
# In your Mesop page:
import mesop as me
from components.pixie_compositor.pixie_compositor import pixie_compositor

@me.stateclass
class PageState:
    # ... your state ...
    start_encode: bool = False
    selected_video_gcs_uri: str = ""

# ...

pixie_compositor(
    video_url=state.selected_video_gcs_uri, # This will be refactored to a list of input files
    config={"fps": 15, "scale": 0.5}, # This will be refactored to a generic command
    start_encode=state.start_encode,
    on_log=on_log_handler,
    on_encode_complete=on_complete_handler,
    on_load_complete=on_load_handler,
)
```

## Properties

-   **`video_url` (String):** The `gs://` URI of the video to be converted. (This will be refactored).
-   **`config` (Object):** A dictionary with encoding parameters. (This will be refactored).
-   **`start_encode` (Boolean):** A trigger property to begin the encoding process.

## Events

-   **`on_load_complete`:** Fired when the `ffmpeg.wasm` library has successfully loaded.
-   **`on_log`:** Streams log messages from the `ffmpeg` process.
-   **`on_progress`:** Streams progress updates during encoding.
-   **`on_encode_complete`:** Fired when the processing is complete. The event's `value` will be a data URL of the generated file.

## Dependencies & Setup

1.  **`ffmpeg.wasm` Assets:** This component requires the `ffmpeg.wasm` core files, which must be served from the `/assets/ffmpeg/` directory of the application.

2.  **Signed URL Endpoint:** The component depends on a FastAPI endpoint at `/api/get_signed_url` to get temporary access to GCS resources.

3.  **Content Security Policy (CSP):** The application's global CSP in `main.py` must be configured to allow all the necessary resources for this component to function.
