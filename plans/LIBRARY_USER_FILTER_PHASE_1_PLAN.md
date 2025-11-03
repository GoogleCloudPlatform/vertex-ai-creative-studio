# Phase 1: Main Library Page User Filter

**Objective:** Implement a "Mine" vs. "All" user filter on the main library page (`pages/library.py`). The filter will be a non-multiselect toggle, defaulting to "All".

---

### 1. State Management (`pages/library.py`)

- **Action:** Add a new state variable to the `LibraryState` class (or equivalent state class for the page).
- **Code:** `user_filter: str = "all"`
- **Details:** This will hold the current state of the filter, either `"all"` or `"mine"`.

### 2. UI Controls (`pages/library.py`)

- **Action:** Add a new `me.button_toggle` to the filter bar area.
- **Details:**
  - The toggle will have two buttons: "All" and "Mine".
  - It will be configured as a single-select toggle: `multi_select=False`.
  - The `on_click` event handler will update the `user_filter` state variable and trigger a refresh of the library's data.

### 3. Data Fetching Logic (`common/metadata.py`)

- **Action:** Modify the primary data fetching function (`get_media_for_page`).
- **Details:**
  - Add a new optional parameter: `filter_by_user_email: str | None = None`.
  - **Implementation Note:** The filtering is performed in Python *after* the initial data fetch. A `.where()` clause was not used in the Firestore query to avoid issues with composite indexes, as the query already includes an `order_by("timestamp")` clause.
  - Inside the function, after fetching a batch of documents, iterate through them and apply the user filter by checking the `user_email` field of each document against the `filter_by_user_email` parameter.

### 4. Connecting UI to Data (`pages/library.py`)

- **Action:** Update the library's main data loading function.
- **Details:**
  - When calling the function from `common/metadata.py`, check the `state.user_filter`.
  - If `state.user_filter == "mine"`, pass the current user's email (from the global `AppState`) as the `filter_by_user_email` argument.
  - If `state.user_filter == "all"`, pass `None`.

### 5. Testing and Regression Plan

- **Default Behavior:** The filter will default to "All". Because the `filter_by_user_email` argument will be `None`, the Firestore query will be identical to the current implementation, ensuring no change in behavior for users not interacting with the filter.
- **Additive Change:** The `.where()` clause is purely additive and is only applied when the "Mine" filter is active. This minimizes the risk of side effects on existing media type or error filters.
- **Manual Verification:** After implementation, the feature will be tested by toggling between "All" and "Mine" and verifying that the displayed assets correctly reflect the selection based on the logged-in user.
