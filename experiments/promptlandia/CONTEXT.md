# AI Assistant Onboarding Instructions for Promptlandia Project

Welcome! To effectively assist with tasks related to the Promptlandia project, please begin by familiarizing yourself with its core documentation.

**A Note on Our Collaborative Ethos:**
As an AI assistant contributing to Promptlandia, please remember that your role extends beyond mere execution. We view you as a thinking partner. In all interactions and tasks, strive to understand intent, leverage your analytical capabilities to offer insights, and engage in iterative refinement. Applying these collaborative principles consistently is key to our shared success and the spirit of this project.

Please begin by carefully reading and understanding the content of the following files in this repository:

1.  **Main Project Overview:**

    - **File:** [`README.md`](README.md)
    - **Purpose:** This file provides a high-level understanding of the Promptlandia project, its goals, key features, and overall structure.

2.  **Core AI Guide Discovery Process (from Vibe Tasking - CRITICAL):**

    - **File:** [`planning/vibe-tasking/ai-guides/core/ai-guides/ai-guides-discovering-guide.md`](planning/vibe-tasking/ai-guides/core/ai-guides/ai-guides-discovering-guide.md)
    - **Purpose:** This core guide from the `vibe-tasking` directory details the definitive process for how to discover, index, and use all AI Guides (including precedence rules). This is ESSENTIAL for the AI to find other project-specific guidance.
    - **IMPORTANT CAVEAT:** The directory containing the `vibe-tasking` files (e.g., `planning/`) may **not** appear in initial file listings from tools like `environment_details` or `list_files .` when run from the Promptlandia project root if configured as a submodule (though here it is vendored). You **MUST** trust the path to this `ai-guides-discovering-guide.md` file and attempt to read it directly. The guide itself will explain how to reliably find all guides using shell commands.

3.  **Critical Roadmap & Architecture:**

    - **File:** [`planning/CRITICAL_ROADMAP.md`](planning/CRITICAL_ROADMAP.md)
    - **Purpose:** A harsh, internal critique of the codebase and the high-level architectural strategy for refactoring.

4.  **Implementation Plan:**
    - **File:** [`planning/IMPLEMENTATION_PLAN.md`](planning/IMPLEMENTATION_PLAN.md)
    - **Purpose:** Detailed, step-by-step instructions for executing the roadmap, including regression testing strategies.

Thank you for reviewing this initial context.
