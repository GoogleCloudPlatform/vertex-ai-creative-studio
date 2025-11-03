### Plan: Advanced Chirp3 HD Features

This plan outlines the addition of advanced audio controls and custom pronunciation features to the Chirp3 HD page.

#### Feature 1: Audio Configuration Sliders

-   **[x] Backend:**
    -   [x] Modify `synthesize_chirp_speech` in `models/chirp_3hd.py` to accept `speaking_rate`, `pitch`, and `volume_gain_db`.
    -   [x] Pass new parameters to the `texttospeech.AudioConfig` object.
-   **[x] Frontend:**
    -   [x] Add `speaking_rate`, `pitch`, `volume_gain_db` fields to `Chirp3hdState` in `pages/chirp_3hd.py`.
    -   [x] Add a new row of three `me.slider` components to the UI.
    -   [x] Implement `on_change` handlers for each slider.
    -   [x] Update `on_click_generate` to pass the new state values.
    -   [x] Update `on_click_clear` to reset the new state values.
-   **[x] Testing Point 1:** Verify that the sliders appear and control the generated audio's pace, pitch, and volume.
    -   **NOTE:** The `pitch` slider has been disabled in the UI and backend as the feature is not currently supported by the Chirp3 HD API.

#### Feature 2: Custom Pronunciations

-   **[x] Backend:**
    -   [x] Modify `synthesize_chirp_speech` to accept a `pronunciations` list.
    -   [x] If the list is provided, create `texttospeech.CustomPronunciation` objects and pass them to the `client.synthesize_speech` request.
-   **[x] Frontend:**
    -   [x] Add `custom_pronunciations`, `current_phrase_input`, `current_pronunciation_input` to `Chirp3hdState`.
    -   [x] Add a new "Custom Pronunciations" section to the UI with input fields and an "Add" button.
    -   [x] Dynamically render the list of added pronunciations with "Remove" buttons.
    -   [x] Implement `on_add_pronunciation` and `on_remove_pronunciation` event handlers.
    -   [x] Update `on_click_generate` and `on_click_clear` to handle the new state.
-   **[x] Testing Point 2:** Verify that custom pronunciations can be added, removed, and correctly affect the generated audio.