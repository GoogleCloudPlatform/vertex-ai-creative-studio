# GenMedia Creative Studio: A2A Integration Plan

## Phase 0: The Services Layer Refactor (Prerequisite)
**Goal:** Decouple business logic, persistence, and analytics from the Mesop UI to ensure parity between human and agent invocations.
1.  **MediaItem Schema Update:** Add `agent_id` to `common/metadata.py` to track agent-generated assets.
2.  **Image Service:** Extract `_generate_and_save` from `banana_studio.py` and `gemini_image_generation.py` into `services/image_service.py`.
3.  **Video Service:** Extract Veo orchestration from UI into `services/video_service.py`.
4.  **Eval Service (P2):** Consolidate critique, brand adherence, and guideline analysis into a unified `services/eval_service.py`.

## Phase 1: Foundation & Identity
**Goal:** Expose the A2A Protocol and handle Token-to-Human authentication.
1.  **Dependencies:** Add `a2a-sdk` (v1.0).
2.  **API Keys:** Update the Firestore `users` collection to store generated `A2A_AGENT_TOKEN`s.
3.  **Server Module (`a2a_server/`):**
    *   `auth.py`: Validate Bearer Tokens against Firestore and inject the resolved `user_email` and `agent_id` into the A2A request context.
    *   `executor.py`: Route tasks to the new Services Layer.
4.  **FastAPI Wiring:** Mount `/a2a/rest` and `/.well-known/agent-card.json`.

## Phase 2: Tier 1 Skills (The Primitives)
**Goal:** Map foundational models to A2A skills.
1.  Expose `generate_image`, `generate_video`, `generate_music`, and `generate_speech` through the `AgentCard`.
2.  Route these skills to their respective Services, utilizing the SDKs `TaskUpdater` for streaming status updates back to the orchestrator.

## Phase 3: Tier 2 Pixie Persona & Evaluations
**Goal:** Expose complex assistive behaviors and conversational editing.
1.  **Pixie Conversational Skill:** Expose `pixie_editor` skill. Implement logic in the Executor to process the full multi-turn `Task` message history, allowing Pixie to reason about the Directors open-ended requests before triggering actual compositing.
2.  **Asset Evaluator:** Expose `evaluate_asset` via the consolidated `eval_service.py`, allowing external agents to programmatically validate their outputs.

## Phase 4: Tier 3 Workflows
**Goal:** Package multi-step routines into single A2A invocations.
1.  Map the `interior_design` and `motion_portraits` skills, leveraging `TaskUpdater.new_agent_message()` to stream human-readable progress updates over the A2A channel.

## Proposed Agent Card
```json
{
  "name": "GenMedia Creative Studio Agent",
  "description": "A multimodal creative assistant capable of generating, compositing, and evaluating video, audio, and images.",
  "provider": { "organization": "Google Cloud", "url": "..." },
  "version": "1.0.0",
  "capabilities": { "streaming": true },
  "default_input_modes": ["text", "image", "video", "audio"],
  "skills": [
    {
      "id": "generate_media",
      "name": "Generate Media",
      "description": "Generates images, video, or audio.",
      "input_modes": ["text", "image", "audio"]
    },
    {
      "id": "pixie",
      "name": "Pixie",
      "description": "Conversational video/audio editor. Can answer composition queries or execute direct concatenations/overlays.",
      "input_modes": ["text", "video", "audio"]
    },
    {
      "id": "adherence_and_quality",
      "name": "Adherence and Quality",
      "description": "Evaluates media against brand or critique guidelines.",
      "input_modes": ["image", "video", "text"]
    },
    {
      "id": "asset_management",
      "name": "Asset Management",
      "description": "Search, retrieve, and manage media assets from the user library.",
      "input_modes": ["text"]
    }
  ]
}
```
