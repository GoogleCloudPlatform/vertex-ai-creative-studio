### Revised Plan for Chirp3 HD Feature Implementation

#### Phase 1: Backend & Configuration

- [x] **Analyze Reference Snippet:** I will analyze the official Google Cloud Python snippet for Text-to-Speech to ensure the implementation uses the standard `google-cloud-texttospeech` client library correctly.

- [x] **Create New Model Logic (`models/chirp_3hd.py`):**
    *   A new file will be created at `models/chirp_3hd.py`.
    *   It will contain a function, `synthesize_chirp_speech(text: str, voice_name: str, language_code: str) -> bytes`, adapted from the reference snippet. This function will not include parameters for a style prompt or a model name.

- [x] **Create New Configuration (`config/chirp_3hd.py`):**
    *   A new `config/chirp_3hd.py` file will be created.
    *   To avoid data duplication, this file will **import** the `GEMINI_TTS_VOICES` and `GEMINI_TTS_LANGUAGES` variables from the existing `config/gemini_tts.py` file and re-export them for use by the Chirp3 HD page.

#### Phase 2: Frontend UI & State Management

1.  **Create the Page and State (`pages/chirp_3hd.py`):**
    *   The main UI file will be created at `pages/chirp_3hd.py`, adapted from `pages/gemini_tts.py`.
    *   A new state class, `Chirp3hdState`, will be defined, omitting the `prompt` and `selected_model` fields. It will include a boolean state for the info dialog.

2.  **Build the User Interface:**
    *   The UI will be adapted from the Gemini TTS page, but the "Voice Prompt" `textarea` and the "Model" `select` dropdown will be removed.
    *   An "info" button will be added to the header. The content for its dialog will be synthesized from the Chirp3 HD documentation URL you provided.

#### Phase 3: Integration & Finalization

1.  **Implement Event Handlers:**
    *   The `on_click_generate` handler will be updated to call the new `synthesize_chirp_speech` function.
    *   The logic for saving the generated audio to GCS and Firestore will be adapted, ensuring the `model` field in the `MediaItem` is correctly set to "Chirp3 HD".
    *   Preset logic will be carried over and simplified.

2.  **Register Page & Update Navigation:**
    *   The new page will be imported and registered with a route (e.g., `/chirp-3hd`) in `main.py`.
    *   I will then locate the **existing** "Chirp3 HD" entry in `config/navigation.json` and update it by adding the `route` property, making it a clickable link in the side navigation.
