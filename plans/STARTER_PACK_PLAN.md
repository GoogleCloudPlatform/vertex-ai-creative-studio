# Starter Pack Page Implementation Plan

This document outlines the plan to create a new "Starter Pack" page in the application. This page will allow users to generate "starter pack" collages from images of outfits ("looks") and, conversely, generate images of models wearing the items from a "starter pack."

## 1. Feature Overview

The "Starter Pack" page will have two core workflows, both leveraging the Gemini 2.5 Flash Image generation model:

1.  **Look to Starter Pack:** The user uploads or selects an image of a person wearing an outfit. The model analyzes the image to extract the featured products and generates a "starter pack" or mood board collage.
2.  **Starter Pack to Look:** The user provides a "starter pack" image and a model image (which can be uploaded or generated using the existing virtual model feature). The model then generates an image of the virtual model wearing the ensemble from the starter pack.

## 2. File Structure

The following files will be created or modified:

**New Files:**

*   `pages/starter_pack.py`: Will contain the Mesop UI components and page layout.
*   `state/starter_pack_state.py`: Will manage the state for the Starter Pack page.
*   `models/starter_pack.py`: Will house the business logic for interacting with the Gemini model for the two workflows.

**Modified Files:**

*   `main.py`: To register the new `/starter-pack` page route.
*   `config/navigation.json`: To add "Starter Pack" to the main navigation menu.

## 3. State Management (`state/starter_pack_state.py`)

A new state class, `StarterPackState`, will be created. It will be responsible for managing the UI state and will include the following fields:

```python
@me.stateclass
class StarterPackState:
    # Input images
    look_image_uri: str
    starter_pack_image_uri: str
    model_image_uri: str

    # Output images
    generated_starter_pack_uri: str
    generated_look_uri: str

    # Virtual model generation inputs (similar to VTO)
    virtual_model_prompt: str

    # Loading indicators
    is_generating_starter_pack: bool
    is_generating_look: bool
    is_generating_virtual_model: bool
```

## 4. UI and Page Layout (`pages/starter_pack.py`)

The UI will be heavily inspired by the `vto.py` page, featuring a two-column layout.

*   **Page Definition:** A new `@me.page` function will be created, linking to the `StarterPackState`.
*   **Left Column (Inputs):** This column will contain the controls for the two workflows, likely separated by tabs or expansion panels.
    *   **Workflow 1 (Look to Starter Pack):**
        *   An image upload/chooser component for the "look" image.
        *   A "Generate Starter Pack" button.
    *   **Workflow 2 (Starter Pack to Look):**
        *   An image upload/chooser for the "starter pack" image.
        *   An image upload/chooser for the model image. This will include the "Create Virtual Model" functionality from `vto.py`.
        *   A "Generate Look" button.
*   **Right Column (Outputs):** This column will display the results.
    *   A dedicated area to display the generated "starter pack" image.
    *   A dedicated area to display the generated "look" image.
    *   Loading spinners will be displayed over these areas when a generation process is active.

## 5. Backend Logic (`models/starter_pack.py`)

This new module will contain the core logic for the feature.

*   **`generate_starter_pack(look_image_uri: str) -> str`:**
    *   Takes the GCS URI of the "look" image.
    *   Constructs a prompt: "Analyze the image to extract the featured products for a mood board."
    *   Calls the Gemini 2.5 Flash Image generation model (reusing logic from `models/gemini.py`) with the prompt and the input image.
    *   Saves the resulting image to GCS.
    *   Returns the GCS URI of the generated starter pack image.

*   **`generate_look(starter_pack_uri: str, model_image_uri: str) -> str`:**
    *   Takes the GCS URIs of the "starter_pack" and "model" images.
    *   Constructs a prompt: "Try this ensemble on the given model."
    *   Calls the Gemini 2.5 Flash Image generation model with the prompt and both input images.
    *   Saves the resulting image to GCS.
    *   Returns the GCS URI of the generated look.

*   **Virtual Model Integration:** The existing virtual model generation logic from `models/virtual_model_generator.py` will be called to create a model when requested.

## 6. Event Handlers (`pages/starter_pack.py`)

Event handlers will connect the UI to the backend logic.

*   **File Uploads:** Handlers for `on_upload` will save the uploaded images to GCS (using `common/storage.py`) and update the corresponding URI in `StarterPackState`.
*   **Button Clicks:** `on_click` handlers for the generate buttons will:
    1.  Set the appropriate `is_generating_...` flag in the state to `True`.
    2.  `yield` to show the loading spinner.
    3.  Call the relevant function from `models/starter_pack.py`.
    4.  Update the state with the returned GCS URI for the generated image.
    5.  Set the `is_generating_...` flag back to `False`.
    6.  `yield` to display the final image.

## 7. Integration Steps

1.  **Create Files:** Create the three new files: `pages/starter_pack.py`, `state/starter_pack_state.py`, and `models/starter_pack.py`.
2.  **Populate Files:** Implement the logic as described above, starting with the state and model, and then building the UI.
3.  **Register Page:** Add the new page to `main.py`.
4.  **Update Navigation:** Add a new entry to `config/navigation.json` to make the page accessible from the side navigation.
5.  **Testing:** Thoroughly test both workflows.

---

## Implementation Notes & Lessons Learned

This section details the final implementation and key learnings from the development process, which deviated from or added detail to the initial plan.

### Final UI/UX:

*   **Tabbed Interface:** The two workflows are presented in the `components.tab_nav.tab_group` custom component, with the output area dynamically updating to show only the result for the currently selected workflow.
*   **Layout:** The page uses the standard `page_frame` component to ensure consistent padding and header placement.
*   **Virtual Model Creation:** The "Create Virtual Model" button generates a model using a randomized prompt (based on the logic from the VTO page), removing the need for user input.

### Backend & Data Flow:

*   **Library Integration:** All generated images (Starter Packs, Looks, and Virtual Models) are now saved to the Firestore library via `common.metadata.add_media_item`. The corresponding comments and source image URIs are also saved.
*   **GCS URI Handling:** A key lesson was the distinction between URI formats:
    *   The backend Gemini API requires `gs://` URIs for image inputs.
    *   The frontend `me.image` component requires public `https://...` URLs for its `src` attribute.
    *   The final implementation stores `gs://` URIs in the state and uses a `gcs_uri_to_https_url` helper function to convert them for display in the UI just before rendering.

### Component API Lessons:

*   **`me.UploadedFile`:** The file contents are accessed via the `.getvalue()` method, not a `.contents` attribute.
*   **`me.progress_spinner`:** This component does not accept a `style` argument. To style it (e.g., add margins), it must be wrapped in a styled `me.box`.