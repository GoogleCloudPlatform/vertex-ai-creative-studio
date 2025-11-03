# Plan for Gemini TTS Feature Implementation

This document outlines the steps to add a new "Gemini TTS" page to the application.

### Phase 1: Backend & Model Logic

- [x] **Create Model Configuration:** Create `config/gemini_tts_models.py` to define the new TTS models (`gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts`).
- [x] **Implement API Interaction:** Create `models/gemini_tts.py` with a `synthesize_speech` function that:
    - [x] Gets a gcloud bearer token.
    - [x] Constructs the headers and JSON payload.
    - [x] Executes a `requests.post` to the TTS API endpoint.
    - [x] Decodes the base64 response and returns the audio bytes.
- [x] **Phase 1 Validation:** Create a standalone test script `test/test_gemini_tts.py` that calls `synthesize_speech` and saves the output to a local `.wav` file for manual verification.

### Phase 2: Frontend UI & State Management

- [x] **Create Page and State:** Create `pages/gemini_tts.py` and define a `@me.stateclass` called `GeminiTtsState` within it to manage UI state.
- [x] **Build the UI:** Implement the page layout in a `@me.page` function, mirroring `pages/lyria.py`. This includes:
    - [x] A `me.textarea` for the input text.
    - [x] A `me.input` for the voice prompt.
    - [x] A `me.select` for model selection.
    - [x] A "Generate" button.
    - [x] A conditional `me.progress_spinner`.
    - [x] An `me.audio` component for the output.
- [x] **Phase 2 Validation:** Manually run the application and navigate to the `/gemini-tts` page. Verify that all UI components render correctly and that state changes (e.g., typing in the text area) are reflected. The "Generate" button won't be fully functional yet.

### Phase 3: Integration & Finalization

- [x] **Implement Event Handler:** In `pages/gemini_tts.py`, create the `on_click` handler for the "Generate" button. This handler will:
    - [x] Call `models.gemini_tts.synthesize_speech`.
    - [x] Use `common.storage.store_to_gcs` to upload the resulting audio bytes.
    - [x] Update the page state with the GCS URL of the audio file.
    - [x] Manage loading and error states.
- [x] **Register Page in Navigation:** Add a "Gemini TTS" entry to `config/navigation.json`.
- [x] **Phase 3 Validation:** Run the application and test the end-to-end flow. Enter text, select a model, click "Generate", and confirm that the audio is generated and can be played back in the UI. Check GCS to ensure the file was uploaded.

### Refinements & Fixes (Post-Completion)

- [x] **Refactor Auth:** Replaced `subprocess`-based auth with the `google-auth` library for Cloud Run compatibility.
- [x] **Add Debug Logging:** Added detailed error logging to the model and page for easier debugging in deployed environments.
- [x] **Implement Library Saving:** Added logic to save generated audio metadata to the Firestore library.
- [x] **Improve UI Layout:** Adjusted input controls to be full-width and use multi-line textareas where appropriate.
- [x] **Add Clear Button:** Implemented a "Clear" button to reset form inputs.
- [x] **Apply Consistent Styling:** Styled the control panel to match other pages in the application.
