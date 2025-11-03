# Worsfold Encoder Web Component

## Overview

The `worsfold-encoder` is a headless Lit-based web component that provides in-browser video-to-GIF conversion using `ffmpeg.wasm`. It is designed to be used within a Mesop application.

## Usage

The component is controlled from Python. You pass it a GCS URI of a video and then trigger the encoding process. It communicates its status and results back to the Mesop application through a series of events.

```python
# In your Mesop page:
import mesop as me
from components.worsfold_encoder.worsfold_encoder import worsfold_encoder

@me.stateclass
class PageState:
    # ... your state ...
    start_encode: bool = False
    selected_video_gcs_uri: str = ""

# ...

worsfold_encoder(
    video_url=state.selected_video_gcs_uri, # Must be a gs:// URI
    config={"fps": 15, "scale": 0.5},
    start_encode=state.start_encode,
    on_log=on_log_handler,
    on_encode_complete=on_complete_handler,
    on_load_complete=on_load_handler,
)
```

## Properties

-   **`video_url` (String):** The `gs://` URI of the video to be converted. The component will call a backend API to get a signed URL for access.
-   **`config` (Object):** A dictionary with encoding parameters. Currently supports `fps` and `scale`.
-   **`start_encode` (Boolean):** A trigger property. Set to `True` from your Python event handler to begin the encoding process.

## Events

-   **`on_load_complete`:** Fired when the `ffmpeg.wasm` library has successfully loaded and the component is ready to encode.
-   **`on_log`:** Streams log messages from the `ffmpeg` process.
-   **`on_progress`:** Streams progress updates during encoding.
-   **`on_encode_complete`:** Fired when the GIF has been successfully created. The event's `value` will be a `blob:` URL of the generated GIF.

## Dependencies & Setup

1.  **`ffmpeg.wasm` Assets:** This component requires the `ffmpeg.wasm` core files. These files must be served from the `/assets/ffmpeg/` directory of the application.

2.  **Signed URL Endpoint:** The component depends on a FastAPI endpoint at `/api/get_signed_url` to get temporary access to GCS resources. This endpoint must be implemented in `main.py`.

3.  **Content Security Policy (CSP):** The application's global CSP in `main.py` must be configured to allow:
    *   Loading the component's JavaScript files.
    *   Loading the `ffmpeg.wasm` assets.
    *   Connecting to the `/api/get_signed_url` endpoint.
    *   Displaying `blob:` URLs in `<img>` tags.
