---
name: story-generator
description: Expert in generating full multi-scene multimedia storybooks (image, video, voice, and music) using direct, native MCP tool calls and parallel subagent orchestration, and packaging them into premium Material 3 interactive making-of reports.
metadata:
  version: "1.1.0"
  design_system: "Material 3 Tonal (Emerald-Meadow & Cosmic-Science)"
---

# Story Generator Skill

This skill allows an agent to design, generate, and composite a multi-scene storybook video combining text-to-speech narration, background music, AI image generation, and image-to-video animation using native MCP tools. It includes automated scripts and premium visual stylesheets to compile professional "making-of" interactive reports and standalone zip packages.

## Directory Structure
Conforming to the [Agent Skills Specification](https://agentskills.io/specification.md):
```
story-generator/
├── SKILL.md            # Main metadata & execution instructions
├── scripts/            # Executable orchestration & compilation utilities
│   ├── generate_scene.py
│   ├── generate_report.py
│   └── package_report.py
└── assets/             # Reusable design tokens & static assets
    ├── index.css       # Premium Material 3 stylesheet (Emerald/Cosmic)
    └── fonts/          # Font files (GoogleSansFlex.ttf)
```

---

## 1. Interrogation Phase (Grilling the User)

Before generating any media, you MUST interrogate the user to determine the scope and style of the story. Use the `/grill-me` or `/grill-with-beads` command if available to sharpen the scope.

Ask the user for the following details:
1.  **Main Character(s):** What is their name, species, appearance, and any defining characteristics (e.g., "Barnaby the Bunny, a fluffy white Angora mix with safety goggles").
2.  **Story Premise/Genre:** What is the core plot or genre? (e.g., "A sci-fi discovery adventure in a meadow lab").
3.  **Number of Scenes:** How long should the story be? (Standard is 5-10 scenes).
4.  **Narrator Voice:** What style of voice should narrate the story? (Callirrhoe is preferred for storybooks).
5.  **Musical Tone:** What is the overarching musical theme? (e.g., "whimsical, adventurous, sleepy").

Do NOT proceed to generation until you have a shared understanding of these points.

---

## 2. Scripting Phase

Based on the user's answers, write a script. For each scene (1 to N), define:
-   **Scene Title:** Concise name (e.g., "Barnaby Awakens").
-   **Narrator Text:** The exact words the narrator will speak (keep under 800 characters for Gemini TTS limits).
-   **Music Prompt:** The prompt for Lyria (e.g., "Gentle, whimsical acoustic guitar, cozy vibe").
-   **Image Prompt:** The prompt for Nano Banana. Specify subject, action, context, and a consistent style (e.g., "3D claymation style, aspect ratio 16:9").
-   **Video Motion Prompt:** The prompt for Veo 3.1. Describe the movement of elements in the frame based on the image (keep duration to 6 seconds; do not use 5 seconds due to model limitations).

Present this script to the user for approval. 

---

## 3. High-Performance Parallel Generation (Orchestrating Subagents)

To generate the storybook efficiently, do **not** run the generation sequentially. Instead, delegate the work to parallel subagents using your native subagent and MCP capabilities!

### Step A: Define the Specialized Subagent
Define a `SceneGenerator` subagent using the `define_subagent` tool. **CRITICAL:** You must set `"enable_mcp_tools": true` in the definition so that each spawned subagent inherits direct access to the MCP tools.

### Step B: Invoke Scene Generators Concurrently
Spawn N concurrent subagents (one for each scene in your script) using `invoke_subagent`. Give each subagent a precise prompt containing:
1.  The specific Scene ID (e.g., "Scene 1")
2.  The Narrator Text, Music Prompt, Image Prompt, and Video Motion Prompt.
3.  Instructions to use **direct MCP tools only** (no Python or bash wrappers).
4.  The output directory: `/Users/ghchinoy/genmedia/bunny_science_story/mcp_direct_test` (or a project-specific directory).

### Step C: Direct MCP stdio Subprocess Execution (Bypass Model)
If system-level LLM tool routing errors are encountered, run the Go-based MCP server binaries directly as local subprocesses using JSON-RPC stdio. 
Each scene worker spawns:
- `mcp-nanobanana-go` for base frame images (GCS Bucket: `genai-blackbelt-fishfooding-assets`)
- `mcp-lyria-go` for background music
- `mcp-gemini-go` for high-fidelity text-to-speech
- `mcp-veo-go` for image-to-video animation (duration must be strictly `[4, 6, 8]` seconds; request `6` seconds).

---

## 4. Compositing Phase (Main Agent)

Once all subagents report back with their finished, mixed video files (e.g., `scene_1_mixed.mp4`, `scene_2_mixed.mp4`):

1.  Create a text file named `concat_list.txt` containing the ordered list of video files in the format `file 'path/to/video.mp4'`.
2.  Stitch them together into the final storybook using standard `ffmpeg`:
    ```bash
    ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy final_story.mp4
    ```

---

## 5. Premium HTML Report Generation & Packaging

To showcase the work, compile a gorgeous Material 3 interactive report using the pre-styled assets.

### Step A: Prepare `scenes.json`
Write a `scenes.json` file containing metadata for each scene in the following format:
```json
[
  {
    "id": 1,
    "title": "Barnaby Awakens",
    "image": "scene_1/base_frame.png",
    "narrator": "Barnaby the bunny woke up in his warm burrow to a perfectly ordinary morning...",
    "image_prompt": "3D claymation style, cute cartoon bunny wearing science safety goggles...",
    "motion_prompt": "The bunny stretches lazily and hops out of his bed, ears twitching.",
    "music_prompt": "Gentle, sleepy acoustic guitar, waking up vibe, whimsical cartoon feel."
  }
]
```

### Step B: Compile Report
Execute the generation script. It will automatically read your project structure, pull `index.css` and font assets from the skill's `assets/` folder, and write a styled report to `{project_dir}/report/index.html`:
```bash
python3 story-generator/scripts/generate_report.py \
  --project_dir /Users/ghchinoy/genmedia/bunny_science_story/mcp_direct_test \
  --title "Barnaby's Magic Meadow" \
  --logline "A 5-scene 3D Claymation multimedia storybook generated by executing Go MCP server binaries directly." \
  --character_details "Barnaby the bunny, a fluffy white Angora mix with safety goggles..." \
  --character_image "scene_1/gemini_20260523110050_3.png" \
  --scenes_json mcp_direct_test/scenes.json
```

### Step C: Create Standalone Package
To package everything up into an offline-browsable zip file (rewriting paths relative to the root), execute:
```bash
python3 story-generator/scripts/package_report.py \
  --project_dir /Users/ghchinoy/genmedia/bunny_science_story/mcp_direct_test \
  --zip_name "storybook_making_of.zip"
```
The resulting archive will bundle the `index.html`, `index.css`, `fonts/`, `final_story.mp4`, and all standalone mixed videos and frames into a portable, standalone package.
