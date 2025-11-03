# Plan: Per-Page Settings & Info Dialog

This document outlines the plan to implement a reusable, page-specific dialog system that can be triggered from the header. This will allow users to get more information about the current page and view its specific settings.

## 1. High-Level Strategy

The core principle is that each page will own and manage its own dialog content and state. The header component will be modified to be a generic trigger, but it will have no knowledge of what the dialog contains. This ensures a clean separation of concerns and makes the components highly reusable.

**Control Flow:**
1.  A page (e.g., `pages/portraits.py`) renders the `header` component, passing a flag to show an info icon and a callback function (`on_info_click`).
2.  When the user clicks the info icon, the header invokes the provided callback function.
3.  The callback function, defined within the page file, updates the page's state to open the dialog (e.g., `state.info_dialog_open = True`).
4.  The page's render function, detecting the state change, then renders a generic `dialog` component, populating it with page-specific content.

## 2. Task Breakdown

### Task 2.1: Refactor Header Component

**File:** `components/header.py`

-   [ ] Modify the `header` component's function signature to accept two new optional parameters:
    -   `show_info_button: bool = False`
    -   `on_info_click: typing.Callable = None`
-   [ ] Update the header's layout to use flexbox (`justify-content: space-between`) to position the title on the left and the new icon on the right.
-   [ ] Add a conditionally rendered `me.icon_button` for the info icon that calls `on_info_click` when clicked.

### Task 2.2: Implement Pilot on "Motion Portraits" Page

**Files:** `pages/portraits.py`, `state/veo_state.py` (assuming it shares state)

-   [ ] **State:** Add a new field `info_dialog_open: bool = False` to the relevant state class.
-   [ ] **Event Handlers:** In `pages/portraits.py`, create two new functions:
    -   `open_info_dialog(e: me.ClickEvent)`: Sets `info_dialog_open = True`.
    -   `close_info_dialog(e: me.ClickEvent)`: Sets `info_dialog_open = False`.
-   [ ] **Integration:** Update the `header` call in the page to pass `show_info_button=True` and `on_info_click=open_info_dialog`.
-   [ ] **Dialog Content:** Add a conditional block to the page layout that renders the `dialog` component when `info_dialog_open` is true. The dialog content will include:
    -   The description from `config/about_content.json` for the "motion_portraits" section.
    -   A display of the current page-specific settings.

### Task 2.3: Rollout to Other Pages

-   [ ] **Imagen Page (`pages/imagen.py`):**
    -   **Settings to show:** `prompt`, `negative_prompt`, `selected_model`, `aspect_ratio`.
-   [ ] **Veo Page (`pages/veo.py`):**
    -   **Settings to show:** `prompt`, `negative_prompt`, `selected_model`, `duration`, input image/video URI.
-   [ ] **Virtual Try-On Page (`pages/vto.py`):**
    -   **Settings to show:** `person_image_gcs`, `garment_image_gcs`, `VTO_MODEL_ID`.
-   [ ] **Product in Scene Page (`pages/recontextualize.py`):**
    -   **Settings to show:** `product_image`, `prompt`, `MODEL_IMAGEN_PRODUCT_RECONTEXT`.
-   [ ] **Character Consistency Page (`pages/character_consistency.py`):**
    -   **Settings to show:** `character_prompt`, `CHARACTER_CONSISTENCY_GEMINI_MODEL`, `CHARACTER_CONSISTENCY_IMAGEN_MODEL`, `CHARACTER_CONSISTENCY_VEO_MODEL`.

## 3. Validation and Testing

-   [ ] **Component Validation:**
    -   On a pilot page (e.g., Motion Portraits), click the info icon. **Expected:** The dialog appears.
    -   Verify the dialog displays the correct description from `about_content.json`.
    -   Verify the dialog displays the correct, current settings from the page's state.
    -   Click the dialog's close button. **Expected:** The dialog closes.
-   [ ] **Regression Testing:**
    -   **Risk:** The header is a shared component. Changes could affect pages that do *not* use the new feature.
    -   **Test:** Load pages that do not have the info dialog implemented (e.g., the Home page, Library). **Expected:** The header should render correctly without the info icon and without any layout issues.
    -   Navigate between pages. **Expected:** The header should update correctly, showing the icon only on pages where it is configured.

## 4. Documentation Updates

-   [ ] **Update `developers_guide.md`:**
    -   **Location:** The best place for this is a new subsection within "Core Development Patterns and Lessons Learned" titled **"Creating Page-Specific Dialogs."** This presents it as a reusable pattern for future development.
    -   **Content:** The new section should explain the control flow (page owns the dialog, header is a generic trigger). It should provide a clear, step-by-step guide on how to add a settings/info dialog to a new page, using the Motion Portraits implementation as a template.

This plan provides a comprehensive path to implementing the feature, ensuring it is robust, well-tested, and properly documented.