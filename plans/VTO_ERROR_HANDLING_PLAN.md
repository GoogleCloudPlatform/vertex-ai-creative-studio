# VTO Page Error Handling and Logging Plan

This document outlines the plan to implement robust, user-friendly error handling and logging for the Virtual Try-On (VTO) page, aligning it with the patterns used in the Veo page and supporting future architectural goals.

## 1. Architectural Goals

*   **API-Ready Models:** The `models/` layer should behave like a standalone API. This means it should perform its core logic and signal success or failure (by returning data or raising an exception) without being concerned with UI presentation.
*   **Consistent UI Components:** The application should use a consistent set of components and patterns for common UI tasks, such as displaying errors. This improves user experience and maintainability.

## 2. Implementation Plan

### Step 2.1: Update Page State (`state/vto_state.py`)

-   **Action:** Add two new fields to the `VtoPageState` dataclass to manage the error dialog's state.
-   **Code:**
    ```python
    error_dialog_open: bool = False
    error_message: str = ""
    ```

### Step 2.2: Modify Model Logic (`models/vto.py`)

-   **Action:** Modify the `generate_vto_image` function to both log the error and then re-raise it, propagating the error to the calling layer. This ensures errors are recorded for debugging while enforcing a clean API-like contract.
-   **Change:**
    -   In the `except` block, add a `logging.error()` call.
    -   Remove the `return None` statement.
    -   Re-raise the exception using `raise`.

### Step 2.3: Update UI Logic (`pages/vto.py`)

-   **Action:** Update the `on_click_generate` event handler to catch the exception raised by the model layer and update the UI state accordingly.
-   **Change:**
    -   Wrap the call to `models.vto.generate_vto_image` in a `try...except` block.
    -   In the `except` block, set `state.error_dialog_open = True` and populate `state.error_message` with a user-friendly message including the exception details.
    -   `yield` to trigger the UI update.

### Step 2.4: Add Error Dialog to UI (`pages/vto.py`)

-   **Action:** Add the reusable `components.dialog.dialog()` component to the `vto_page` render function.
-   **Configuration:**
    -   Bind the dialog's `is_open` property to `state.error_dialog_open`.
    -   Display the content of `state.error_message`.
    -   Add a "Close" button that sets `state.error_dialog_open = False` when clicked.

## 3. Validation and Regression Plan

1.  **Happy Path:** Perform a standard VTO generation to ensure existing functionality is unaffected. The error dialog should not appear.
2.  **Error Path:** Intentionally trigger an API error (e.g., by using an invalid model name temporarily) to verify:
    -   The error is logged to the console/standard logging output.
    -   The error dialog appears on the VTO page with the correct error message.
    -   The application remains stable.
3.  **Cleanup & Final Test:** Revert the change that forced the error and run one final happy path test to confirm the page is left in a working state.

This plan ensures the VTO page becomes more robust, aligns with project architecture, and provides better feedback to the user.
