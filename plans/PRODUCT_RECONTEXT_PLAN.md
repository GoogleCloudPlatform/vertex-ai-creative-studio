# Product in Scene (Recontextualization) Feature Plan

This document outlines the detailed plan for implementing the new "Product in Scene" feature, which uses the Imagen Product Recontextualization model.

---

### Phase 1: Analysis and Foundational Setup

- [x] **Analyze `test/recontext_simple.py`:** Thoroughly analyze this file to understand the exact API call structure for the `imagen-product-recontext` model, including how to pass multiple images and the prompt.
- [x] **Update Configuration (`config/default.py`):**
    - [x] Add a new attribute for the model name: `MODEL_IMAGEN_PRODUCT_RECONTEXT: str = os.environ.get("MODEL_IMAGEN_PRODUCT_RECONTEXT", "imagen-product-recontext-preview-06-30")`.
- [x] **Update Data Model (`common/metadata.py`):**
    - [x] Add the new field `source_images_gcs: list[str] = field(default_factory=list)` to the `MediaItem` dataclass.
    - [x] Refactor the metadata saving logic. The new `add_media_item` function in `common/metadata.py` will be made more flexible to accept arbitrary keyword arguments (`**kwargs`). This will allow it to save any media type's specific fields.
    - [x] The `on_generate` handlers in both `pages/vto.py` and the new `pages/recontextualize.py` will be updated to call this flexible `add_media_item` function, passing their unique fields (e.g., `person_image_gcs`, `product_image_gcs` for VTO) as keyword arguments. This preserves all specific metadata in Firestore.

### Phase 2: Backend Model Integration

- [x] **Create New Model Function (`models/image_models.py`):**
    - [x] Create a new function, `recontextualize_product_in_scene`, that accepts a list of GCS URIs and an optional prompt.
    - [x] Implement the function's logic based on the analysis from Phase 1.
    - [x] The function will return a list of GCS URIs for the generated images.

### Phase 3: Frontend Page Creation

- [x] **Create New Page (`pages/recontextualize.py`):**
    - [x] Create the new file using `pages/vto.py` as a structural template.
- [x] **Create New State Class (`state/recontext_state.py`):**
    - [x] Create a new state file to manage the page's specific state (list of uploaded images, prompt, loading status, results).
- [x] **Implement UI Components in `pages/recontextualize.py`:**
    - [x] Implement a multi-image uploader where the user uploads one file at a time, and thumbnails of uploaded images are displayed.
    - [x] Add a `me.input` for the optional scene prompt.
- [x] **Implement Event Handlers in `pages/recontextualize.py`:**
    - [x] `on_upload`: Handles adding a new file to the state and uploading it to GCS.
    - [x] `on_click_generate`: Orchestrates the generation process, calls the backend model, and logs the metadata with `comment="product recontext"`.
- [x] **Register New Page:**
    - [x] Add the new page route to `main.py`.
    - [x] Add the new page to the side navigation in `config/navigation.json`.

### Phase 4: Library Integration

- [x] **Update `pages/library.py`:**
    - [x] Update `get_media_for_page` to correctly read `source_images_gcs` and `comment` from Firestore and populate them into the `MediaItem` object.
- [x] **Update `components/library/image_details.py`:**
    - [x] Add a conditional rendering block that checks `if item.comment == "product recontext":`.
    - [x] Inside the block, display a "Source Images" title and render the images from `item.source_images_gcs` as small thumbnails in a horizontal row.

### Phase 5: Testing and Verification Plan

- [x] **Manual End-to-End Test:**
    1.  **Asset Generation:** If necessary, use the Imagen page to generate sample assets (e.g., a standalone product on a white background, a wooden table, a plant) using Imagen 4 Fast. Save these locally.
    2.  **Navigate:** Go to the new "Product in Scene" page.
    3.  **Upload:** Upload 1-4 product images (using the assets from step 1 if needed). Verify that thumbnails appear correctly.
    4.  **Generate:** Enter a descriptive prompt (e.g., "on a wooden table, next to a plant") and click "Generate".
    5.  **Verify Loading:** Confirm a loading spinner appears.
    6.  **Verify Result:** Confirm the generated image appears in the results area.
    7.  **Navigate to Library:** Go to the "Library" page.
    8.  **Verify Grid View:** Confirm the new generation appears as the first item.
    9.  **Verify Detail View:** Click the new item. In the dialog, verify:
        - The main generated image is displayed.
        - The comment "product recontext" is visible in the metadata.
        - The source product images are displayed as small thumbnails in a horizontal row.
