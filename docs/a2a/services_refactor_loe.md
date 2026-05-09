# Phase 0: Services Layer Refactoring - Level of Effort Assessment

## Executive Summary
To expose GenMedia Creative Studios capabilities via the A2A Protocol, the business logic must be decoupled from the Mesop UI state. Currently, the application handles API invocation, Firestore persistence, Analytics logging, and UI state mutation (e.g., state.is_generating) within single, monolithic functions in the pages/ directory.

This document assesses the Level of Effort (LOE) required to extract these into a clean services/ layer that can be consumed uniformly by both the Mesop UI and the A2A Executor.

---

## 1. ImageService (High LOE)
**Files Affected:** pages/gemini_image_generation.py, pages/banana_studio.py, models/gemini.py

**Analysis:**
The _generate_and_save function in the image generation pages is highly complex (approx 200+ lines). It intertwines:
*   Pre-processing prompts based on the number of requested images.
*   Invoking generate_image_from_prompt_and_images.
*   Capturing telemetry.
*   Extracting C2PA manifests for each generated image.
*   Constructing the MediaItem payload and calling add_media_item_to_firestore.
*   Conditionally launching a secondary Phase 2 evaluation if critique questions are present in the UI state.
*   Managing over 10 distinct UI state variables.

**Refactoring Path:**
We must create a pure ImageService.generate_and_save() that handles the API call, C2PA extraction, and Firestore save. The Phase 2 evaluation must be decoupled into its own discrete service call.

---

## 2. VideoService (Medium LOE)
**Files Affected:** pages/veo.py, models/veo.py

**Analysis:**
The Veo generation logic is slightly cleaner. models/veo.py already exposes a generate_video() function that handles the heavy lifting of the GenAI SDK payload construction.
However, the persistence logic and polling for Long Running Operations (LROs) are still managed in the UI or helper scripts. 

**Refactoring Path:**
Create VideoService.generate_and_save(). The primary challenge will be handling the asynchronous nature of video generation. The service must support yielding status updates (which the Mesop UI can use for progress bars, and the A2A Executor can map to TaskUpdater stream chunks) before returning the final URI and saving to Firestore.

---

## 3. EvalService (Low/Medium LOE)
**Files Affected:** models/evaluators.py, pages/guideline_analysis.py, pages/brand_adherence.py

**Analysis:**
The application has several distinct evaluation paths. They rely on similar underlying Gemini structured outputs but have diverging schemas and implementations.

**Refactoring Path:**
Create a unified EvalService.evaluate_asset(). This service will standardize the JSON schema returned to the caller, making the adherence_and_quality A2A skill robust and predictable for external orchestrators.

---

## 4. PixieService (Medium/High LOE)
**Files Affected:** pages/pixie_compositor.py

**Analysis:**
Pixie is currently a UI-driven compositor. To elevate Pixie to a conversational persona, we need a service that can ingest a chat history, determine intent (e.g., Answer a question vs. Execute an FFmpeg concatenation), and act accordingly.

**Refactoring Path:**
Create PixieService.process_conversation(). This service will likely need a routing LLM call to classify the intent, followed by tool calls to the underlying media processing utilities.

---

## Conclusion
The refactoring is a substantial but necessary architectural modernization. 
*   **Recommendation:** Do not attempt to refactor all services at once. Begin with the **ImageService** as a proof-of-concept. Once the ImageService is powering both the UI and the A2A generate_media skill successfully, apply the pattern to Video, Lyria, and Evals.
