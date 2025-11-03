# Plan: Resolving Library Data Freshness Issues

This document outlines the plan to fix the issue where the Media Library and the "Choose from Library" component do not automatically display newly generated assets.

**Status: Completed**

## 1. Analysis of the Problem

The root cause of the issue is a "load-once" data fetching pattern in both the main library page (`pages/library.py`) and the image selector component (`components/library/library_image_selector.py`).

-   **`library_image_selector.py`**: This component, used by the chooser button, fetches a list of images from Firestore only when it is first initialized. It uses a state flag (`is_loading`) that prevents it from ever re-fetching data, causing it to display a stale list of images.
-   **`pages/library.py`**: The main library page fetches media items only on its initial load, controlled by the `initial_url_param_processed` flag. It does not refresh its content when the user navigates back to it after generating new media, making it appear that the new items are missing.

The core issue is that the UI components are not designed to react to changes in the underlying Firestore database.

## 2. Proposed Solution

The solution is to replace the "load-once" pattern with a reliable mechanism for triggering data refreshes. After verifying the behavior of Mesop's event model, we will not use the `on_load` event, as it is a page-level event that fires only once per browser session.

Instead, we will use a combination of state management and explicit user action.

1.  **Chooser Button (`library_image_selector`)**: Implement a state-passing mechanism. The parent component (`library_chooser_button`) will control when its child (`library_image_selector`) refreshes. When the "Choose from Library" dialog is opened, the parent will signal to the child that it must re-fetch its data.
2.  **Main Library (`pages/library.py`)**: Add a manual "Refresh" button to the UI. This gives the user explicit and predictable control over when the library view is updated with the latest content from the server.

This approach is robust, aligns with Mesop's idiomatic state management patterns, and provides a clear user experience.

## 3. Task Breakdown

### Task 1: Fix the Library Chooser Button

-   **File:** `components/library/library_chooser_button.py`
    -   Modify the local `State` to include a `needs_refresh: bool` flag.
    -   In the `open_dialog` click handler, set `state.needs_refresh = True`.
    -   Pass this `needs_refresh` flag as a parameter to the `library_image_selector` component.
    -   After the `library_image_selector` is rendered, set `state.needs_refresh = False` to reset the trigger.
-   **File:** `components/library/library_image_selector.py`
    -   Update the component signature to accept the `needs_refresh: bool` parameter.
    -   Remove the internal `is_loading` flag from its local state.
    -   Use the `needs_refresh` parameter to conditionally re-fetch data from `get_media_for_page` at the beginning of the component function.

### Task 2: Add Refresh Button to Main Library

-   **File:** `pages/library.py`
    -   Add a new event handler function, `on_refresh_click`, that calls the existing `_load_media_and_update_state` function.
    -   In the `library_content` function, add a `me.button` with an icon (e.g., `refresh`) next to the filter controls.
    -   Wire the button's `on_click` event to the new `on_refresh_click` handler.

## 4. Testing and Verification Plan

1.  **Add Temporary Logging:** Place `print("DEBUG: ...")` statements in the `library_image_selector` data fetching block and the `on_refresh_click` handler in `pages/library.py` to confirm they are being triggered correctly.
2.  **Test the Library Chooser:**
    -   Navigate to a page that uses the `library_chooser_button` (e.g., VTO page).
    -   Open the chooser dialog and observe the initial set of images. Close it.
    -   Navigate to the Imagen page and generate a new image.
    -   Navigate back to the VTO page.
    -   **Verification:** Open the chooser dialog again. The `DEBUG` log for the selector should appear in the console, and the newly generated image should be visible at the top of the list.
3.  **Test the Main Library Page:**
    -   Navigate to the Library page and observe the initial media.
    -   Navigate to the Veo page and generate a new video.
    -   Navigate back to the Library page.
    -   **Verification (Initial State):** The new video should **not** be present initially.
    -   **Verification (Refresh Button):** Click the new "Refresh" button. The `DEBUG` log for the refresh handler should appear, and the library grid should update to show the new video at the top.

## 5. Regression Risk Assessment

-   **Risk:** Low.
-   **Analysis:** The proposed changes are highly localized.
    -   The chooser button fix is self-contained within the chooser and selector components. It modifies how the selector loads data but does not change the selection mechanism itself (`on_select` event), so it should not affect pages that consume the selection event.
    -   Adding a refresh button to the library page is an additive change. It introduces a new UI element and handler but does not alter the existing pagination or filtering logic.
-   **Mitigation:** The testing plan is designed to verify that the core functionality of both the chooser (selecting an image) and the library (filtering, pagination, viewing details) remains unaffected after the changes are applied.
