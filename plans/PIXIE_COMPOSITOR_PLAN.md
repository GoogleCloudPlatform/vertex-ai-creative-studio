# Plan: Creating the Pixie Compositor Suite

This document outlines a phased plan to create the "Pixie Compositor", a powerful, reusable web component for performing a variety of `ffmpeg` operations in the browser. This plan is designed to be non-destructive, building out the new functionality in parallel with the existing `worsfold-encoder`.

---

## Phase 1-4: Initial `worsfold-encoder` Implementation (COMPLETE)

This phase covered the initial creation, debugging, and successful implementation of the `worsfold-encoder` component, which can convert a video to a GIF and save it to the library. The extensive lessons learned from this process are documented in the `WEB_COMPONENT_INTEGRATION_GUIDE.md`.

---

## Phase 5: Create the Foundation for the "Pixie Compositor" (COMPLETE)

**Goal:** Create a new, generic "Pixie Compositor" component by copying and refactoring the existing `worsfold-encoder`, without modifying the original.

**Technical Steps:**

1.  **Create New Directory:** Create a new directory: `components/pixie_compositor/`.
2.  **Copy Files:**
    *   Copy `components/worsfold_encoder/worsfold_encoder.js` to `components/pixie_compositor/pixie_compositor.js`.
    *   Copy `components/worsfold_encoder/worsfold_encoder.py` to `components/pixie_compositor/pixie_compositor.py`.
    *   Copy `pages/test_worsfold_encoder.py` to `pages/test_pixie_compositor.py`.
3.  **Initial Rename:**
    *   In `pixie_compositor.js`: Rename the class to `PixieCompositor` and the custom element to `'pixie-compositor'`.
    *   In `pixie_compositor.py`: Rename the function to `pixie_compositor` and update the `@me.web_component` path and the `name` in `insert_web_component`.
    *   In `test_pixie_compositor.py`: Update the import and the component call to use the new `pixie_compositor`.
4.  **Register New Test Page:**
    *   Update `main.py` to import and register the new `/test_pixie_compositor` page.
    *   Update `config/navigation.json` to add a link to the new test page.

**Validation Test:**

*   Run the application and navigate to the new `/test_pixie_compositor` page.
*   Verify that the new component works exactly like the original `worsfold-encoder` (i.e., it can still create a GIF). This confirms that our copy and rename was successful.

---

## Phase 6: Refactor the Pixie Compositor for Generic Commands

**Goal:** Evolve the new `pixie-compositor` to be a truly generic `ffmpeg` engine.

**Technical Steps:**

1.  **Refactor Lit Component (`pixie_compositor.js`):**
    *   Modify the component to accept a generic `commandArgs: Array` property instead of having the GIF logic hardcoded.
    *   Modify it to accept a list of `inputFiles` and `outputFileNames`.
    *   The `on-complete` event will be updated to return a list of the generated files.
2.  **Refactor Python Wrapper (`pixie_compositor.py`):**
    *   Update the Python wrapper to accept the new `command_args`, `input_files`, and `output_file_names` properties.
3.  **Update the Test Page (`test_pixie_compositor.py`):**
    *   Modify the test page to build the `ffmpeg` command for GIF creation as an array of strings and pass it to the new `command_args` property of the `pixie_compositor` component.

**Validation Test:**

*   Run the application and go to the `/test_pixie_compositor` page.
*   Verify that the refactored component can still create a GIF, this time by receiving the command from the Python backend instead of having it hardcoded.

---

## Phase 7: Build the Pixie Compositor Suite

**Goal:** Create a series of simple, user-friendly Mesop components for each specific `ffmpeg` task, all using the generic `pixie_compositor` component.

**Example Tasks (from Appendix):**

*   Create a video from a still image (`pixie-image-to-video`).
*   Change video resolution (`pixie-video-resizer`).
*   Compress a video (`pixie-video-compressor`).
*   Extract audio from video (`pixie-audio-extractor`).
*   Add a poster image to an audio file (`pixie-audio-poster`).
*   Cut a video (`pixie-video-trimmer`).
*   Concatenate videos (`pixie-video-concatenator`).
*   Layer audio on a video (`pixie-audio-layerer`).

**Implementation Strategy:**

*   For each task, create a new Python component file in `components/pixie_compositor/` (e.g., `video_trimmer.py`).
*   This component will have a simple, task-specific API (e.g., `def video_trimmer(video_gcs_uri: str, start_time: int, end_time: int):`).
*   It will be responsible for building the correct `ffmpeg` command arguments and passing them to the generic `pixie_compositor` component.

---

## Phase 8: Documentation

**Goal:** Document the new Pixie Compositor suite and its usage.

**Technical Steps:**

1.  **Create a `README.md` for the `pixie_compositor` component.**
2.  **Create separate documentation for each user-facing compositing tool.**
3.  **Update the main `developers_guide.md` to reflect the new architecture.**
