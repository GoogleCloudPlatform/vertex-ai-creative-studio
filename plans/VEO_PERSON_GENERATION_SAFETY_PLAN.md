# Plan: Implement Veo Person Generation Safety Dropdown

**Objective:** To add a "Person Generation" safety setting to the Veo UI, allowing users to control how people are generated in videos. The final implementation uses a dropdown menu directly in the generation controls for a more streamlined user experience, replacing an initial plan for a modal dialog.

---

## Final Implementation Details

This plan outlines the step-by-step process for integrating the "Person Generation" safety feature as a direct dropdown control.

### 1. State Management (`state/veo_state.py`)

* **Task:** Add a field to the `PageState` class to manage the selected safety setting.
* **File:** `state/veo_state.py`
* **Change:**

    ```python
    @me.stateclass
    class PageState:
        # ... existing fields ...
        person_generation: str = "Allow (All ages)"
        # ... other existing fields ...
    ```

#### 2. Model Request Schema (`models/requests.py`)

* **Task:** Update the `VideoGenerationRequest` data model to include the new safety parameter.
* **File:** `models/requests.py`
* **Change:**

    ```python
    class VideoGenerationRequest(BaseModel):
        # ... existing fields ...
        person_generation: str
        # ... other existing fields ...
    ```

#### 3. UI Control (`components/veo/generation_controls.py`)

* **Task:** Add a dropdown menu for the safety setting directly into the generation controls UI.
* **File:** `components/veo/generation_controls.py`
* **Implementation:**
  * A `me.select` component was added with the label "person generation".
  * The options were set to: `"Allow (All ages)"`, `"Allow (Adults only)"`, and `"Don't Allow"`.
  * A new event handler, `on_selection_change_person_generation`, was created to update the `PageState.person_generation` field and `yield` to refresh the UI.
  * The previous settings icon and modal-opening logic were removed.

#### 4. Page Integration & Cleanup (`pages/veo.py`)

* **Task:** Remove all code related to the now-deleted safety modal.
* **File:** `pages/veo.py`
* **Change:**
  * Removed the import for `safety_dialog`.
  * Removed the conditional block that rendered the dialog.

#### 5. Model Generation Logic (`models/veo.py`)

* **Task:** Pass the new safety setting to the Google GenAI SDK.
* **File:** `models/veo.py`
* **Changes:**
    1. A mapping dictionary was added to translate UI strings to API values.

        ```python
        PERSON_GENERATION_MAP = {
            "Allow (All ages)": "allow_all",
            "Allow (Adults only)": "allow_adult",
            "Don't Allow": "dont_allow",
        }
        ```

    2. The `gen_config_args` dictionary was updated to include the `person_generation` parameter, using the map to get the correct API value.

#### 6. File Cleanup

* **Task:** Delete the unused dialog component file.
* **Action:** The file `components/veo/safety_dialog.py` was deleted.

---

### Final Verification Plan

#### 1. UI Verification

* Navigate to the Veo page.
* **Expected:** A dropdown labeled "person generation" is visible in the generation controls row.
* Change the selection to "Allow (Adults only)".
* **Expected:** The selection persists.

#### 2. API Call Verification

* Set the dropdown to "Don't Allow".
* Enter a prompt that includes a person (e.g., "a chef cooking in a kitchen").
* Trigger a video generation.
* **Expected:** The generation either fails with a safety error or produces a video that respects the setting by not showing a person, confirming the parameter was passed correctly.
