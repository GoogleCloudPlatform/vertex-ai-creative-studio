# Plan: Decomposed State-Driven Workflow for Character Consistency

This document outlines the architectural refactoring of the Character Consistency feature. The goal is to transform the backend from a monolithic "fire-and-forget" function into a responsive, state-driven workflow that provides real-time feedback to the UI, without sacrificing the ability to run it as a single-call service for other backend processes.

### 1. The Hybrid "Yielding Orchestrator" Approach

The core of this plan is to refactor the `generate_character_video` function into a **Python generator**. Instead of returning only at the end of its multi-minute execution, it will `yield` control and a structured data payload back to the caller after each major step.

This provides two modes of operation from a single implementation:

-   **UI-Informed Mode (Mesop):** The Mesop UI will iterate through the generator, receiving status updates and intermediate data (e.g., candidate images) at each `yield`. This allows the UI to re-render and show progress, creating a responsive user experience.
-   **Batch Mode (Future FastAPI / Backend):** Any other service can call the exact same function but simply iterate through the generator without processing the yielded values, effectively treating it as a single-shot function and only caring about the final outcome.

To facilitate this, we will introduce a new data structure for these updates:

```python
# To be defined in models/character_consistency_models.py
class WorkflowStepResult:
    step_name: str         # e.g., "generate_candidates"
    status: str            # e.g., "complete"
    message: str           # e.g., "Step 4 of 7: Candidate images generated."
    duration_seconds: float
    data: dict             # Payload with results, e.g., {"candidate_urls": [...]}
```

### 2. Detailed Task List

**Task 1: Create the Data Model for Step Results**
1.  In `models/character_consistency_models.py`, define the new `WorkflowStepResult` dataclass.

**Task 2: Refactor the Orchestrator (`models/character_consistency.py`)**
1.  Change the function signature of `generate_character_video` to be a generator: `-> Generator[WorkflowStepResult, None, None]:`.
2.  Inside the function, record start and end times for each major step.
3.  After each step, create and `yield` an instance of `WorkflowStepResult` populated with the step name, status, duration, and any generated data (e.g., GCS URIs).

**Task 3: Refactor the Mesop Event Handler (`pages/character_consistency.py`)**
1.  Add a new field to `PageState` to track the cumulative generation time: `total_generation_time: float = 0.0`.
2.  Rewrite the `on_generate_click` handler to use a `for` loop to iterate over the `generate_character_video` generator.
3.  Inside the loop, update the page state with the message, data, and accumulated time from each yielded `WorkflowStepResult`.
4.  `yield` within the loop to trigger a UI re-render at every step.

**Task 4: Update the UI (`pages/character_consistency.py`)**
1.  Add a new `me.text` component to display the final `total_generation_time`.

```

### 4. Workflow Visualization

Here is a step-by-step breakdown of the entire workflow, formatted for clarity.

---

**➡️ Step 1: Download Reference Images**
*   **Action:** The system receives a list of GCS URIs pointing to the images the user uploaded. It downloads the image data (bytes) for each URI in parallel.
*   **Yields:** A status message confirming the download is complete.

**➡️ Step 2: Generate Character Description**
*   **Action:** The image bytes for each reference photo are sent to the **Gemini 2.5 Pro** model.
    1.  **Forensic Analysis:** Gemini analyzes each image to extract a structured `FacialCompositeProfile` (face shape, eye color, etc.).
    2.  **Natural Language Translation:** The structured profile is then used to generate a concise, natural-language paragraph describing the person's key features.
*   **Yields:** The final character description (derived from the first image).

**➡️ Step 3: Generate Scene Prompt**
*   **Action:** The character description from Step 2 and the user's original scene prompt are sent to **Gemini 2.5 Pro**. It is tasked with creating a detailed, photorealistic prompt suitable for Imagen, including a standard negative prompt.
*   **Yields:** The final Imagen prompt and the negative prompt.

**➡️ Step 4: Generate Candidate Images**
*   **Action:** The system calls the **Imagen 3.0** model. It provides the prompt from Step 3 along with all the original reference images (using `SubjectReferenceImage`) to ensure the generated person is consistent with the source photos.
*   **Yields:** A list of GCS URIs for the newly generated candidate images.

**➡️ Step 5: Select Best Image**
*   **Action:** The original reference images and the new candidate images are all sent to **Gemini 2.5 Pro**. It is tasked with comparing them and selecting the single candidate image that has the highest facial likeness to the person in the original photos.
*   **Yields:** The GCS URI of the single best candidate image.

**➡️ Step 6: Outpaint Best Image**
*   **Action:** The system takes the single best image from Step 5 and sends it to **Imagen 3.0** for outpainting. This extends the image from a 1:1 aspect ratio to a cinematic 16:9 ratio, creating a wider scene for the video.
*   **Yields:** The GCS URI of the final, outpainted image.

**➡️ Step 7: Generate Final Video**
*   **Action:** The outpainted image from Step 6 is sent to the **Veo 3.0** model to be animated into a short video clip.
*   **Yields:** The GCS URI of the final generated video.

**➡️ Step 8: Persist Metadata**
*   **Action:** A final `MediaItem` object is created, containing all the artifacts generated throughout the workflow (all GCS URIs, all prompts, timings, etc.). This object is saved as a single document in Firestore.
*   **This is the final step.** The workflow is now complete.

---

### 5. Validation and Testing Plan

**A. Functional Testing (New Feature)**

1.  **UI Responsiveness:**
    -   **Test:** Run the full workflow from the UI.
    -   **Expected Outcome:** The status message and intermediate images must appear sequentially as each step completes, not all at once.

2.  **Data Integrity:**
    -   **Test:** After a successful run, inspect the final `MediaItem` document in Firestore.
    -   **Expected Outcome:** The document must contain all correct GCS URIs and metadata, identical to the previous implementation.

3.  **Timing Accuracy:**
    -   **Test:** Observe the console logs and the final UI display.
    -   **Expected Outcome:** The logs must show the duration for each individual step. The UI must display a final cumulative time that is the sum of the step durations.

4.  **Error Handling:**
    -   **Test:** Intentionally introduce a failure into a mid-workflow step (e.g., by providing an invalid model name in the config).
    -   **Expected Outcome:** The workflow must halt at the point of failure, and the UI must display the specific error message from that step.

**B. Regression Testing (Side-Effect Prevention)**

To ensure this refactoring does not impact other parts of the application, the following areas must be manually tested:

1.  **Veo Page (`/veo`):**
    -   **Test:** Perform a standard text-to-video generation.
    -   **Expected Outcome:** The page must function correctly, generate a video, and save the result to the library without error.

2.  **Imagen Page (`/imagen`):**
    -   **Test:** Perform a standard text-to-image generation.
    -   **Expected Outcome:** The page must function correctly, generate images, and save the results to the library without error.

3.  **VTO Page (`/vto`):**
    -   **Test:** Perform a standard virtual try-on by uploading a person and product image.
    -   **Expected Outcome:** The page must function correctly and display the generated try-on image.

4.  **Recontextualize Page (`/recontextualize`):**
    -   **Test:** Perform a standard product recontextualization by uploading an image and providing a scene prompt.
    -   **Expected Outcome:** The page must function correctly and display the generated images.

5.  **Library Page (`/library`):**
    -   **Test:** Open the details dialog for assets generated by Veo, Imagen, VTO, and Recontextualize.
    -   **Expected Outcome:** The dialog for each of these asset types must render correctly, showing all relevant metadata and previews as before.
