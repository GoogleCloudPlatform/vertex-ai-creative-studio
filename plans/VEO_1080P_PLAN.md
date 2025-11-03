# Definitive Plan: Refactor and Enhance Veo Generation for 1080p Support

**Guiding Principle:** Refactor the video generation process to establish a clean, formal boundary between the "frontend" (the Mesop UI) and the "backend" (the model logic). This will be achieved by creating a dedicated request schema, making the model logic independent of the UI, and preparing the codebase for an easy future transition to a dedicated API service like FastAPI.

---

### Detailed Implementation & Task Checklist

This section details every change made during this session, organized by architectural layer.

**Phase 1: Defining the Data Schemas & Contracts** `[X]`

*   `[X]` **API Contract (`models/requests.py`):** Created a new file to define a Pydantic `VideoGenerationRequest` model. This acts as a formal, version-controlled contract between the UI and the model layer.
*   `[X]` **Model Configuration (`config/veo_models.py`):** Added the `resolutions: List[str]` attribute to the `VeoModelConfig` dataclass and populated the list for all existing Veo models.
*   `[X]` **Database Schema (`common/metadata.py`):** Promoted `resolution` to a first-class citizen by adding `resolution: Optional[str] = None` as a top-level field to the `MediaItem` dataclass.
*   `[X]` **UI State (`state/veo_state.py`):** Added the `resolution: str` field to the `PageState` class to hold the user's selection from the UI.

**Phase 2: Refactoring the Backend Logic** `[X]`

*   `[X]` **Model Layer (`models/veo.py`):** Refactored the `generate_video` function. Its signature was changed from `(state, resolution)` to `(request: VideoGenerationRequest)`, making it completely independent of the Mesop UI framework.

**Phase 3: Refactoring the Frontend Logic** `[X]`

*   `[X]` **UI Controller (`pages/veo.py`):** Refactored the `on_click_veo` event handler. It now acts as a translator, creating a formal `VideoGenerationRequest` object from the UI state and passing it to the decoupled model layer.
*   `[X]` **UI Component (`components/veo/generation_controls.py`):** Modified the "Resolution" `me.select` component to be always visible, but conditionally `disabled` based on the capabilities of the selected Veo model.

**Phase 4: Updating Data Handling & Display** `[X]`

*   `[X]` **Data Write (`pages/veo.py`):** Updated the `on_click_veo` handler to populate the top-level `item_to_log.resolution` field before saving to Firestore.
*   `[X]` **Data Read (`common/metadata.py`):** Updated the `get_media_item_by_id` and `get_media_for_page` functions to correctly read the new top-level `resolution` field from Firestore documents.
*   `[X]` **Data Display (`pages/library.py`):** Updated the library UI to correctly display the resolution. This includes the `pill` in the grid view and the text in the details dialog, both of which now read from the top-level `item.resolution` field and default to `"720p"` if it's not present.

---

### Verification Checklist (Manual)

*   `[ ]` **Veo Page UI Verification:**
    *   `[ ]` **Test Case 1 (Veo 2 Model):** Select a Veo 2 model. **Expected:** The "Resolution" dropdown is visible but *disabled*, and its value is "720p".
    *   `[ ]` **Test Case 2 (Veo 3 Model):** Select a Veo 3 model. **Expected:** The "Resolution" dropdown is visible and *enabled*, allowing selection between "720p" and "1080p".
*   `[ ]` **Generation & Firestore Verification:**
    *   `[ ]` **Test Case 3 (1080p Generation):** Generate a 1080p video with a Veo 3 model. Inspect the new Firestore document. **Expected:** The document contains a top-level field `"resolution": "1080p"`.
*   `[ ]` **Library Display Verification:**
    *   `[ ]` **Test Case 4 (New Video):** Open the 1080p video from the previous test in the library. **Expected:** The details dialog shows "Resolution: 1080p".
    *   `[ ]` **Test Case 5 (Old Video):** Find an older video generated before this change. **Expected:** The details dialog shows "Resolution: 720p" as a fallback.

---

### Architectural Justification & Future-Proofing

This refactoring is a strategic investment in the application's maintainability and future scalability.

**1. Separation of Concerns:** The core benefit is creating a strong boundary between the UI (the "what") and the backend logic (the "how").
    *   The **UI Layer** (`pages/veo.py`) is responsible for gathering user input.
    *   The **Model Layer** (`models/veo.py`) is responsible for executing the business logic of video generation.
    *   The **Contract** (`models/requests.py`) is the single, unambiguous bridge between them.

**2. Preparing for a FastAPI Backend:** This architecture makes a future migration to a dedicated backend service trivial.

*   **Current Flow:**
    ```
    Mesop UI State -> VideoGenerationRequest -> generate_video(request)
    ```
    The Mesop event handler acts as the "client" that builds the request object.

*   **Future FastAPI Flow:**
    ```
    HTTP POST with JSON -> VideoGenerationRequest -> generate_video(request)
    ```
    In the future, a FastAPI endpoint will receive an HTTP request. FastAPI will automatically parse the JSON body, validate it against the *exact same* `VideoGenerationRequest` model, and then call the *exact same* `generate_video` function.

The critical `generate_video` function will require **zero changes** to work in the new FastAPI environment. We are effectively building the API-ready backend component *now* and simply calling it from our current UI.