# A2A Integration Analysis: GenMedia Creative Studio vs Lyria Studio

## 1. Architectural Comparison: IAP and Machine Identity

A review of the sister project (**Lyria Studio**) reveals a critical architectural hurdle for Agent-to-Agent (A2A) integration: **Google Cloud Identity-Aware Proxy (IAP)**.

### The GenMedia Creative Studio Approach
GenMedia Creative Studio is structured around a central **FastAPI** `app` which mounts the Mesop WSGI application alongside REST endpoints. 
Instead of building a detached background worker that constantly polls Firestore, we will leverage the native **A2A Python SDK (v1.0)**. 
1. We will expose the A2A routes (`/a2a/rest`, `/a2a/jsonrpc`) directly on the FastAPI app.
2. We will configure the Google Cloud Load Balancer / IAP to **exclude** the `/.well-known/` and `/a2a/` URL paths from IAP protection.
3. We will protect the `/a2a/` routes using the A2A SDKs built-in Auth Interceptors.

### Authentication & Identity Mapping
To ensure that A2A generated assets securely appear in a humans library, we will implement a **Token-to-Human Mapping** architecture:
*   Users will generate an `A2A_AGENT_TOKEN` within the Studio UI. This token is saved in Firestore linked to their `user_email`.
*   When an external agent calls the Studio using this token, the A2A Auth Interceptor resolves the token to the human owner.
*   The `MediaItem` schema will be updated to include an `agent_id` or `generated_by` field. This ensures the asset saves to the humans library but is cleanly marked as agent-generated.

## 2. The Services Layer Prerequisite (Phase 0)

Currently, the orchestration of AI generation, Firestore persistence, and analytics logging is heavily coupled inside the UI event handlers in the `pages/` directory (e.g., `_generate_and_save` in `banana_studio.py`).
If an A2A Executor calls the raw models directly, the generated assets will be orphaned and not saved to the library.

**The Solution:** We must introduce a **Services Layer** (`services/`) that acts as the single source of truth for business logic. Both the Mesop UI and the A2A Executor will call the Service Layer, which handles the Model execution, Analytics logging, and Firestore persistence uniformly.

## 3. Capability Mapping & Prioritization

We will group Creative Studios features into tiers of complexity.

### Tier 1: Core Generative Primitives
Single-turn, straightforward AI operations.
*   **Image Generation:** Input (Text + Images/PDFs) --> Output (Image URI).
*   **Video Generation:** Input (Text + Reference Image) --> Output (Video URI).
*   **Music Generation:** Input (Text/Audio) --> Output (Audio URI).
*   **Speech Generation:** Input (Text) --> Output (Audio URI).

### Tier 2: Pixie & Assistive Behaviors
The **Pixie** is not merely a utility; it is a primary conversational persona. 
*   **Pixie (The Directors Assistant):** Pixie must support transactional commands (concatenate A and B) as well as open-ended, stateful collaborations (How should I sync this audio to the climax?). This means Pixies A2A skill must be capable of processing multi-turn message history from the external Director agent before invoking the underlying FFmpeg/Veo rendering logic.
*   **Adherence & Quality (P2):** Consolidated critique rubrics (Brand Adherence, Guideline Analysis) exposed as a synchronous, deterministic feedback loop for external agents.
*   **Asset Management:** Allows agents to query the user library (Firestore) to retrieve historical assets or reference media (e.g., brand guideline documents, previous video generations) for context in subsequent generation tasks.

### Tier 3: Complex Multi-Step Workflows
*   **Interior Design Workflow:** Extracts rooms, generates 3D views, styles them, and creates walkthroughs, streaming status back to the caller.
*   **Motion Portraits Workflow:** Orchestrates TTS and Veo lip-sync.
