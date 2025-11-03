
# Plan: Adding "Negative Prompt" to Veo

The goal is to add an optional "Negative Prompt" text field to the Veo generation page. This input will be used by the Veo model to avoid certain concepts in the generated video, and the value will be saved and displayed in the library.

Here are the detailed steps:

**Step 1: Update State Management (`state/veo_state.py`)**
*   **Task:** Add a new field to the `VeoState` class to hold the negative prompt's value.
*   **File:** `state/veo_state.py`
*   **Change:**
    ```python
    @me.stateclass
    class VeoState:
        # ... existing fields ...
        prompt: str = "..."
        # Add the new field below
        negative_prompt: str = ""
        # ... other existing fields ...
    ```

**Step 2: Update the Model Request Schema (`models/requests.py`)**
*   **Task:** Add the optional `negative_prompt` field to the `VideoGenerationRequest` to ensure data is passed consistently to the model layer.
*   **File:** `models/requests.py`
*   **Change:**
    ```python
    class VideoGenerationRequest(BaseModel):
        # ... existing fields ...
        model_version_id: str
        # Add the new field below
        negative_prompt: Optional[str] = None
        reference_image_gcs: Optional[str] = None
        # ... other existing fields ...
    ```

**Step 3: Add the UI Input Field (`components/veo/generation_controls.py`)**
*   **Task:** Add a `me.Textarea` for the "Negative Prompt" in the generation controls component.
*   **File:** `components/veo/generation_controls.py`
*   **Change:** Add the following snippet inside the main `me.box` alongside the other controls like aspect ratio and resolution.
    ```python
    me.text("Negative Prompt", style=me.Style(font_weight="bold"))
    me.textarea(
        label="Enter concepts to avoid",
        on_input=on_input_negative_prompt, # This handler will be created in pages/veo.py
        value=state.negative_prompt,
        rows=2,
        style=me.Style(width="100%"),
    )
    ```

**Step 4: Implement UI Logic (`pages/veo.py`)**
*   **Task:** Create the event handler for the new input field and pass the negative prompt value when calling the generation function.
*   **File:** `pages/veo.py`
*   **Changes:**
    1.  Define the new event handler:
        ```python
        def on_input_negative_prompt(e: me.InputEvent):
            state = me.state(VeoState)
            state.negative_prompt = e.value
            yield
        ```
    2.  Update the `on_click_generate` function to pass the new handler and state value to the `generation_controls` component.
    3.  In `on_click_generate`, when creating the `VideoGenerationRequest`, populate the new `negative_prompt` field from the state.

**Step 5: Update the Model Generation Logic (`models/veo.py`)**
*   **Task:** Modify the `generate_video` function to accept the negative prompt and pass it to the GenAI SDK.
*   **File:** `models/veo.py`
*   **Change:** Inside the `generate_video` function, check if `request.negative_prompt` has a value and, if so, include it in the parameters sent to the Veo model.
    ```python
    # Inside generate_video function
    params = {
        # ... existing params
    }
    if request.negative_prompt:
        params["negative_prompt"] = request.negative_prompt

    # The call to the SDK will then be:
    # video_edit_ops = model.generate_videos(..., **params)
    ```

**Step 6: Update Metadata Storage (`common/metadata.py`)**
*   **Task:** Add the `negative_prompt` to the `MediaItem` dataclass and save it to Firestore.
*   **File:** `common/metadata.py`
*   **Changes:**
    1.  Add `negative_prompt: Optional[str] = None` to the `MediaItem` dataclass.
    2.  In `save_video_to_firestore`, extract `negative_prompt` from the request and include it in the `raw_data` dictionary and the `MediaItem` instance.

**Step 7: Display the Negative Prompt in the Library (`components/library/image_details.py`)**
*   **Task:** Update the library's detail view to show the negative prompt if it was used for a video.
*   **File:** `components/library/image_details.py`
*   **Change:** In the `image_details` component, add logic to check for `media_item.negative_prompt` and display it, similar to how the main prompt is displayed.
    ```python
    # Inside image_details component
    if item.negative_prompt:
        me.text("Negative Prompt:", style=me.Style(font_weight="bold"))
        me.text(item.negative_prompt)
    ```

### Verification Plan

1.  **Automated Test:** I will create a new test in `test/test_veo_generation_flow.py` that sets a negative prompt in the state, triggers generation, and asserts that the mocked `generate_video` and `save_video_to_firestore` functions are called with the correct negative prompt value.
2.  **Manual Test:** I will run the app, enter text into the new "Negative Prompt" field, generate a video, and confirm it appears correctly in the library's detail view.
