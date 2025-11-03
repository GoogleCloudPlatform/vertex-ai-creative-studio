# Finalized Plan for Character Consistency Page

This plan outlines the steps to create a new "Character Consistency" page in the `veo-app` Mesop application. It reflects the final implementation after initial development and debugging.

## 1. Scaffolding and Page Creation

- **Create New Files:**
    - `veo-app/pages/character_consistency.py`: UI and page logic.
    - `veo-app/state/character_consistency_state.py`: Page-specific state.
    - `veo-app/models/character_consistency.py`: Core generation logic.
    - `veo-app/models/character_consistency_models.py`: Pydantic models for this feature.
- **Register Page:**
    - Add the new page component import and `@me.page` route to `veo-app/main.py`.
    - Add a new entry in `veo-app/config/navigation.json` for the side navigation, ensuring correct JSON syntax.

## 2. Configuration (`config/default.py`)

- Add new model names to the `Default` dataclass to centralize configuration:
    - `CHARACTER_CONSISTENCY_GEMINI_MODEL: str = "gemini-2.5-pro"`
    - `CHARACTER_CONSISTENCY_IMAGEN_MODEL: str = "imagen-3.0-capability-001"`
    - `CHARACTER_CONSISTENCY_VEO_MODEL: str = "veo-3.0-generate-preview"`

## 3. Data Models and Persistence (`common/metadata.py`)

- **`MediaItem` Dataclass:**
    - Extend the dataclass with new fields to store all artifacts from the workflow.
    - **`media_type`:** This field is the designated identifier for the workflow and must be set to `"character_consistency"`.
    - **`mime_type`:** This must be set to `"video/mp4"` for the final artifact.
    - **New Fields:** `source_character_images`, `character_description`, `imagen_prompt`, `veo_prompt`, `candidate_images`, `best_candidate_image`, `outpainted_image`.
- **`get_media_item_by_id` Function:**
    - The timestamp retrieval logic was corrected to handle both `datetime.datetime` and `firestore.Timestamp` objects by checking for the presence of the `.isoformat()` method, resolving a critical `isinstance()` bug.

## 4. Core Logic (`models/character_consistency.py`)

- **Orchestration Function:**
    - The primary function `generate_character_video` orchestrates the entire workflow.
- **Storage Integration:**
    - Use `store_to_gcs` for uploads and `download_from_gcs` for retrievals.
    - All generated artifacts must be saved with a unique filename using `uuid.uuid4()` to prevent collisions.
- **Logging:**
    - Implement comprehensive logging at each major step to provide visibility and aid in debugging.

## 5. UI and State Management (`pages/`)

- **`pages/character_consistency.py`:**
    - **Component Structure:** The page content must be wrapped in the `page_scaffold` and `page_frame` components and use the shared `header` component for a consistent look and feel.
    - **File Uploads:** Use the `me.uploader` component. The `on_upload` handler calls `store_to_gcs` and appends the returned GCS URIs to the page state.
    - **Event Handling:** The `on_generate_click` handler calls the backend orchestrator and then uses `get_media_item_by_id` to fetch the completed record and update the UI with the final and intermediate artifacts.
- **`pages/library.py`:**
    - **Media Details Dialog:** The dialog logic was enhanced to provide a richer display for this new asset type.
    - **Conditional Rendering:** An `elif` condition was added to check if `item.media_type == "character_consistency"`. If true, the dialog will render the main video and, directly beneath it, a small thumbnail of the `best_candidate_image`.

## 6. Architectural Principles and Refactoring Path

- **Core Principle:** `models/character_consistency.py` should act as a **workflow orchestrator**, delegating all API interactions to centralized services.

- **Refactoring Status & Next Steps:**
    - **Gemini (Complete):** All Gemini-related logic has been successfully refactored into new, reusable functions within `models/gemini.py`.
    - **Imagen (To Do):** The Imagen API calls are still made directly from `character_consistency.py`. The next step is to enhance `models/image_models.py` to support the `SubjectReferenceImage` type and then refactor the orchestrator to call this centralized service.
    - **Veo (To Do):** The Veo API call is also direct. This should be refactored to use the existing `generate_video` function in `models/veo.py`.