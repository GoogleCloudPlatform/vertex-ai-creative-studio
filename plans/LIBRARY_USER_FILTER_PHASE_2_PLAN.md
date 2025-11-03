# Phase 2: Library Chooser Components User Filter

**Objective:** Extend the "Mine" vs. "All" user filter to the library chooser components (`infinite_scroll_library.py`, `library_chooser_button.py`, etc.) that are used in other pages. This will be tested in isolation before being integrated into the main application.

---

### 1. Component Analysis

- **Action:** Thoroughly review the code for `components/library/infinite_scroll_library.py` and `components/library/library_chooser_button.py`.
- **Goal:** Understand how they currently fetch data and where the new filter state needs to be passed down. The chooser components likely re-use the same core data fetching function from `common/metadata.py`, but we need to confirm how to pass the new `user_filter` state through the component hierarchy.

### 2. Isolated Testing (`pages/test_uploader.py` & `pages/test_infinite_scroll.py`)

- **Action:** Before modifying the main application pages, implement the filter on the existing test pages.
- **Details:**
  - Modify `pages/test_infinite_scroll.py` to include the "All" vs. "Mine" `me.button_toggle`.
  - Update the test page to pass the filter state into the `infinite_scroll_library` component.
  - This will likely require adding a new parameter to the `infinite_scroll_library` component's function signature (e.g., `user_filter: str = "all"`).
- **Benefit:** This allows us to debug and verify the filter's functionality in a controlled environment without affecting the main VTO, Imagen, or other pages that use the chooser.

### 3. Component Refactoring (`components/library/*`)

- **Action:** Based on the findings from the test page implementation, refactor the necessary library chooser components.
- **Details:**
  - Add the `user_filter` parameter to the function signatures of the components that need it.
  - Ensure the `user_filter` state is passed down through any intermediate components until it reaches the function that calls the main data fetching logic in `common/metadata.py`.

### 4. Final Integration

- **Action:** Once the filter is working correctly and robustly on the test pages, integrate the changes into the main application pages.
- **Details:**
  - Add the "All" vs. "Mine" toggle to the UI where the library chooser is used (e.g., on the VTO page when a user clicks "Choose from Library").
  - Pass the state from this new toggle into the chooser component.

### 5. Regression Plan

- **Parameter Defaults:** All new function/component parameters (`user_filter`) will have a default value of `"all"`. This is the most critical step to prevent regressions. If a page that uses the chooser is not updated, it will continue to call the component without the new parameter, and the component will default to showing "All" results, preserving existing behavior.
- **Phased Rollout:** By implementing and testing on the dedicated test pages first, we isolate the risk and ensure the component is stable before it's used in the production-like pages of the app.
