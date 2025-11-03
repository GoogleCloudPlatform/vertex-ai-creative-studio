# DreamVVT Workflow Integration Plan

**Objective:** To create a new test page in the GenMedia Creative Studio application to implement and test the DreamVVT workflow using Gemini 2.5, Imagen VTO, and Veo 3.

**High-level Plan:**

1.  Create a new test page to house the workflow.
2.  Add new functions to the existing `models` to handle the core logic of the workflow.
3.  Implement the UI for the test page, allowing users to upload a video, select a garment, and view the results.
4.  Test the workflow thoroughly.

---

## File Creation

### 1. New Test Page

A new file will be created at `pages/test_dreamvvt_workflow.py` to serve as the front-end for this new feature.

**`pages/test_dreamvvt_workflow.py`**

```python
import mesop as me
import mesop.labs as mel
from components import page_scaffold
from models import gemini, vto, veo

@me.page(path="/test_dreamvvt_workflow")
def page():
    with page_scaffold.render(page_title="DreamVVT Workflow Test"):
        me.text("DreamVVT Workflow Test Page")

        # 1. Video Upload
        me.text("Step 1: Upload a video")
        # Placeholder for video upload component

        # 2. Garment Selection
        me.text("Step 2: Select a garment")
        # Placeholder for garment selection component

        # 3. Run Workflow Button
        if me.button("Run Workflow"):
            # Placeholder for workflow logic
            pass

        # 4. Results Display
        me.text("Results")
        # Placeholder for displaying keyframes, VTO'd images, and the final video

```

---

## File Modification

### 1. Gemini Model Extension

The `models/gemini.py` file will be updated to include a function that can analyze a video and extract keyframes and descriptions.

**`models/gemini.py`**

```python
# ... existing code ...

def analyze_video_for_dreamvvt(video_path: str) -> dict:
    """Analyzes a video to extract keyframes and descriptions for the DreamVVT workflow."""
    # This is a placeholder for the actual implementation.
    # In a real implementation, this would involve:
    # 1. Using a library like OpenCV to extract frames from the video.
    # 2. Using Gemini to select the most representative keyframes.
    # 3. Using Gemini to generate descriptions for the keyframes and the overall video.
    print(f"Analyzing video at {video_path}")
    return {
        "keyframes": ["frame1.jpg", "frame2.jpg", "frame3.jpg"],
        "keyframe_descriptions": {
            "frame1.jpg": "A person standing in front of a white wall.",
            "frame2.jpg": "A person walking towards the camera.",
            "frame3.jpg": "A person turning around.",
        },
        "video_description": "A person walks towards the camera and then turns around.",
    }

```

### 2. VTO Model Extension

The `models/vto.py` file will be updated to include a function that can perform VTO on a list of keyframes.

**`models/vto.py`**

```python
# ... existing code ...

def perform_vto_on_keyframes(keyframes: list[str], garment_path: str) -> list[str]:
    """Performs VTO on a list of keyframes."""
    # This is a placeholder for the actual implementation.
    # In a real implementation, this would involve iterating through the keyframes
    # and calling the Imagen VTO API for each one.
    print(f"Performing VTO on {len(keyframes)} keyframes with garment {garment_path}")
    return [f"vto_{keyframe}" for keyframe in keyframes]

```

### 3. Veo Model Extension

The `models/veo.py` file will be updated to include a function that can generate a video from an image and a prompt.

**`models/veo.py`**

```python
# ... existing code ...

def generate_video_from_image_and_prompt(image_path: str, prompt: str) -> str:
    """Generates a video from an image and a prompt."""
    # This is a placeholder for the actual implementation.
    # In a real implementation, this would involve calling the Veo 3 API.
    print(f"Generating video from {image_path} with prompt: {prompt}")
    return "final_video.mp4"

```

---

## Testing Strategy

1.  **Unit Tests:**
    *   Create unit tests for the new functions in `models/gemini.py`, `models/vto.py`, and `models/veo.py`. These tests should mock the API calls to the underlying models and verify that the functions are behaving as expected.
2.  **Manual Testing:**
    *   Thoroughly test the new `test_dreamvvt_workflow.py` page.
    *   Test with a variety of input videos and garments.
    *   Verify that the keyframes, VTO'd images, and the final video are all generated correctly.
    *   Verify that the UI is responsive and easy to use.

---

## Regression Risks and Mitigations

1.  **Risk:** The new functionality could interfere with the existing pages in the application.
    *   **Mitigation:** By creating a new test page, we are isolating the new functionality and minimizing the risk of side effects. The new functions in the `models` directory are also self-contained and should not affect the existing code.
2.  **Risk:** The new models could consume a significant amount of resources, potentially slowing down the application or increasing costs.
    *   **Mitigation:** The resource usage of the new models will be carefully monitored during testing. We will also consider adding caching mechanisms to avoid re-processing the same video multiple times.
3.  **Risk:** The new workflow could be slow, leading to a poor user experience.
    *   **Mitigation:** We will investigate ways to optimize the workflow, such as running some of the steps in parallel. We will also provide clear feedback to the user about the progress of the workflow.
