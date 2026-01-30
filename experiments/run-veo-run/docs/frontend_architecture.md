# Frontend Architecture & Component Hierarchy

This document outlines the architecture of the **Run, Veo, Run** frontend application.

## Tech Stack
*   **Framework:** [Lit](https://lit.dev/) (Web Components)
*   **Language:** TypeScript
*   **Build Tool:** Vite
*   **Styling:** CSS Variables + [Material Design 3](https://m3.material.io/) (via `@material/web`)
*   **State Management:** Reactive properties within Lit components (local state).

## Component Hierarchy

The application is structured as a single-page application (SPA) encapsulated within a main custom element.

### 1. Root Component: `<run-veo-run>`
*   **File:** `src/run-veo-run.ts`
*   **Role:** The main application container and state manager.
*   **Responsibilities:**
    *   **State:** Manages global app state:
        *   `genMode`: Current generation mode (Text, Image, Storyboard, Ingredients, Upload).
        *   `videoUri`: URI of the currently displayed video.
        *   `sourceUri`: GCS URI of the source video (used for extension).
        *   `prompt`: User's text prompt.
        *   `isRunning`: Loading state.
        *   `config`: Settings like Model and Aspect Ratio.
    *   **Layout:** Renders the header, video player, tabs, controls, and footer.
    *   **Logic:**
        *   Handles API calls (via `api/` layer).
        *   Manages the "Continuity Loop" (Gemini analysis + Veo extension).
        *   Enforces business logic (e.g., locking Aspect Ratio in Ingredients mode).

### 2. Child Components

#### `<image-upload>`
*   **File:** `src/components/image-upload.ts`
*   **Role:** Handles image file selection, preview, and upload.
*   **Usage:**
    *   **Start Frame:** In Image-to-Video and Storyboard modes.
    *   **End Frame:** In Storyboard mode.
    *   **Ingredients:** For uploading style/character references.
*   **Events:** Dispatches `upload-complete` with the GCS URI upon success.

#### `<video-upload>`
*   **File:** `src/components/video-upload.ts`
*   **Role:** Handles video file selection, validation, preview, and upload.
*   **Responsibilities:**
    *   **Validation:** Enforces strict constraints before upload:
        *   **MIME:** `video/mp4` only.
        *   **Duration:** 1s to 30s.
        *   **Resolution:** 720p or 1080p (16:9 or 9:16).
    *   **Preview:** Uses an HTML `<video>` element for playback validation.
*   **Usage:** In "Upload" mode to provide a base for extension.

### 3. API Layer
The application logic is decoupled from UI components via the `api/` directory.

*   **`src/api/veo.ts`**:
    *   `generateVideo(options)`: Calls `/api/veo/generate`.
    *   `extendVideo(uri, prompt, model)`: Calls `/api/veo/extend`.
    *   Type definitions for `GenerateOptions` and `VeoResponse`.
*   **`src/api/gemini.ts`**:
    *   `analyzeVideo(uri)`: Calls `/api/gemini/analyze` to get visual context description.

## Data Flow

1.  **User Input:** User interacts with UI (Tabs, Uploads, Text Field).
2.  **State Update:** `<run-veo-run>` updates its `@state` properties.
3.  **Action:** User clicks "Run Simulation" / "Extend Timeline".
4.  **API Call:**
    *   **Continuity (Optional):** Frontend calls `analyzeVideo` -> Backend (Gemini) -> Returns context string.
    *   **Generation:** Frontend combines prompt + context -> calls `generateVideo` or `extendVideo` -> Backend (Veo) -> Returns Signed URL.
5.  **Render:** `<run-veo-run>` updates `videoUri`, triggering the `<video>` element to play the new clip.
