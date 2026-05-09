# A2A Integration: Comprehensive Test Plan

This document outlines the testing strategy for exposing GenMedia Creative Studio via the Agent-to-Agent (A2A) Protocol. Testing is broken down per implementation phase and categorizes validation into three pillars:
1.  **Human Regression:** Ensuring the existing Mesop Web UI remains functional.
2.  **Automated (Unit/Integration):** Fast, isolated verification of business logic using pytest.
3.  **External Agent Validation:** End-to-end verification over the wire using our officially supported A2A clients: a2acli (Go CLI) and Apex (Flutter GUI).

---

## Phase 0: Services Layer Refactoring
**Goal:** Decouple business logic into services/ without changing observable behavior.

*   **Human Regression:** 
    *   Manually generate an image, video, and audio track via the Mesop UI.
    *   Verify the assets appear in the Library.
    *   Verify C2PA manifests are still attached (Image Generation).
    *   Verify Analytics logs are still emitted in the Google Cloud console.
*   **Automated:** 
    *   Write pytest unit tests for ImageService.generate_and_save(), mocking the genai SDK and verifying add_media_item_to_firestore is called with the correct schema.
*   **External Agent:** N/A (A2A boundary not yet exposed).

## Phase 1: Foundation & Identity
**Goal:** Expose A2A routes, bypass IAP, and map Tokens to Human Identities.

*   **Human Regression:** 
    *   Verify the /home and standard UI routes are still protected by IAP.
    *   Verify the new Generate A2A Token UI button successfully writes to Firestore.
*   **Automated:** 
    *   Test the A2AAuthInterceptor logic. Provide a mocked valid token and verify it resolves to the correct user_email. Provide an invalid token and expect a 401.
*   **External Agent:** 
    *   Use a2acli: Run a2acli describe --url <creative_studio_url> (unauthenticated) to verify the .well-known/agent-card.json is publicly discoverable.
    *   Use a2acli: Attempt to call a dummy skill without a token to verify the 401 Unauthorized response from the A2A endpoint.

## Phase 2: Tier 1 Skills (The Primitives)
**Goal:** Expose Image, Video, Music, and Speech generation via A2A.

*   **Human Regression:** 
    *   Standard regression: verify UI generation parity.
*   **Automated:** 
    *   Test the CreativeStudioAgentExecutor. Inject a mock Task targeting generate_media, and assert that it correctly routes to ImageService and emits the correct TaskState updates.
*   **External Agent:** 
    *   Use a2acli: Run a2acli send --skill generate_media --input {"text":"A futuristic city"} --token <A2A_AGENT_TOKEN>. Verify the CLI streams the Generating... status and exits with a GCS URI artifact.
    *   Use Apex (Flutter App): Connect to the Studio Agent. Send an image generation prompt. Verify the human-readable streaming updates appear in the chat bubble, and the final image artifact is natively rendered in the chat feed.
    *   **Data Validation:** Go back to the Mesop UI Library and verify the A2A-generated image appears in the humans library, tagged with the agent_id.

## Phase 3: Tier 2 Pixie Persona & Evaluations
**Goal:** Expose conversational editing and synchronous evaluations.

*   **Human Regression:** 
    *   Test the Pixie UI compositor with a standard FFmpeg concatenation.
*   **Automated:** 
    *   Test the routing LLM in the PixieService to ensure it correctly classifies a conversational query (How do I fix this?) vs an execution command (Stitch these).
*   **External Agent:** 
    *   Use Apex (Flutter App): Engage in a multi-turn conversation with the pixie skill. 
        *   Turn 1: Ask for advice on audio syncing. Verify the response is conversational text.
        *   Turn 2: Provide two media URIs and ask it to execute the sync. Verify Pixie transitions to a working state and returns a composited video artifact.
    *   Use a2acli in CI mode: Pass a JSON payload to adherence_and_quality and assert the output strictly matches the expected JSON schema with an exit code of 0.

## Phase 4: Tier 3 Workflows (Orchestrator Offload)
**Goal:** Offload complex, multi-step routines to the A2A endpoint.

*   **Human Regression:** 
    *   Run the Interior Design workflow in the UI.
*   **Automated:** 
    *   Mock the intermediate steps of the Interior Design workflow and assert that the A2A Executor yields at least 3 distinct TaskStatus updates back to the TaskUpdater.
*   **External Agent:** 
    *   Use Apex (Flutter App): Trigger the interior_design skill, passing a floor plan image.
    *   Validate the UX: The Apex UI should cleanly display the progressive updates (Extracting rooms..., Generating 3D model..., Styling...) without timing out the connection, eventually displaying the final video walkthrough.
