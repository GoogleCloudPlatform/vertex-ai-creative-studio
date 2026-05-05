---
title: "GenMedia MCP Servers for Antigravity"
---

This directory contains the configuration files and agent skills necessary to use the Google GenMedia MCP Servers directly within [Antigravity](https://antigravity.google/docs/).

## 1. Configure MCP Servers

Antigravity manages custom MCP servers via a raw `mcp_config.json` file.

1. Open Antigravity.
2. Open the **MCP Store** panel via the "..." dropdown at the top of the editor's side panel.
3. Click on **Manage MCP Servers**.
4. Click on **View raw config**.
5. Copy the contents of the `mcp_config.json` file in this directory and paste it into the editor.
6. Replace `YOUR_GOOGLE_CLOUD_PROJECT_ID` and `YOUR_GOOGLE_CLOUD_STORAGE_BUCKET` with your actual GCP Project ID and GenMedia GCS bucket URI (e.g., `gs://my-cool-bucket`).

## 2. Install expert Agent Skills

Antigravity features a powerful Agent Skills engine. We have uplifted our expert media workflows into a central `skills/` directory at the project root.

To install these skills for your Antigravity workspace, copy the desired skills into your `.agents/skills/` directory:

### Workspace Installation
This makes the skills available only within the current project.

```bash
mkdir -p .agents/skills
cp -r ../../skills/* .agents/skills/
```

### Global Installation
This makes the skills available across all your Antigravity workspaces.

```bash
mkdir -p ~/.gemini/antigravity/skills
cp -r ../../skills/* ~/.gemini/antigravity/skills/
```

### Available Skills
Once installed, the Antigravity agent will automatically discover the skills based on your request:

- `genmedia-producer`: The orchestrator for complex multi-step media workflows. Use when you want to "create a podcast" or "generate a storyboard".
- `genmedia-video-editor`: Expert in FFmpeg composition, overlays, and GIF generation.
- `genmedia-audio-engineer`: Specialist in TTS synthesis, music generation, and mixing.
- `genmedia-image-artist`: Expert in high-fidelity visual generation and prompt optimization.

The agent will seamlessly read the instructions and orchestrate the GenMedia tools like a pro!
