# Managed Agents Architecture Proposal: Cloud-Sandboxed Showrunners & Secure SSE MCPs

This proposal outlines the technical architecture, security design, and execution strategy for migrating the **Story Generator (v1.3.0)** pipeline from local macOS execution to a secure, managed cloud-sandboxed environment powered by **Vertex AI Interactions API** and the `agentsapi` CLI.

---

## 1. Architectural Overview

Instead of running local python scripts that call cloud-hosted models, the **entire showrunner intelligence** is deployed inside a Google-managed, secure VM sandbox (`antigravity-preview-05-2026`). The skill files are mounted dynamically from Cloud Storage, and the sandbox interacts with your media generation tools via a secure, remote Model Context Protocol (MCP) gateway.

![Managed Agents Cloud Architecture](file:///Users/ghchinoy/dev/vertex-ai-creative-studio-public/experiments/mcp-genmedia/assets/managed_agents_flow.webp)

---

## 2. Sandboxed Dependency Verification: "Zero-External-PIP" Advantage

A primary friction point in managed agent execution is python dependency resolution inside a clean cloud sandbox. 

### 2.1 Standard Library Dominance
An analysis of the core story-generator scripts reveals a major engineering advantage:
*   [generate_scene.py](file:///Users/ghchinoy/dev/vertex-ai-creative-studio-public/experiments/mcp-genmedia/skills/story-generator/scripts/generate_scene.py) and [editors_quality_room.py](file:///Users/ghchinoy/dev/vertex-ai-creative-studio-public/experiments/mcp-genmedia/skills/story-generator/scripts/editors_quality_room.py) rely **strictly on standard Python library imports**:
    *   `import argparse`
    *   `import json`
    *   `import subprocess`
    *   `import os`
    *   `import re`
    *   `import glob`
*   **No external pip packages (like `requests`, `numpy`, or `fastapi`) are imported.**
*   *Result:* The scripts can execute out-of-the-box on any bare-bones Python 3 installation in the cloud sandbox without needing `pip install` or `uv run` setups.

### 2.2 Robust FFmpeg/FFprobe Sanitization & Mitigation
Our pipeline relies heavily on `ffmpeg` and `ffprobe` for audio/video duration checking, speed-fitting, and multi-track compositing. While standard Vertex AI sandboxes (like Waverunner) typically include `ffmpeg`, we can implement a **foolproof fallback strategy** to guarantee execution across any clean environment:

1.  **Static Binary Bundling**: Download standard static Linux-AMD64 builds of `ffmpeg` and `ffprobe` (e.g., from [John Van Sickle's builds](https://johnvansickle.com/ffmpeg/)).
2.  **GCS Packaging**: Place these static binaries inside the `story-generator` skill's `bin/` directory:
    ```
    story-generator/
    ├── bin/
    │   ├── ffmpeg      # Static Linux binary
    │   └── ffprobe     # Static Linux binary
    ```
3.  **Path Failover**: If the script's default global `ffprobe`/`ffmpeg` calls encounter a `command not found` error, it gracefully falls back to executing `./bin/ffmpeg` and `./bin/ffprobe` located in the mounted environment workspace.

---

## 3. Remote, Secure Hosting of GenMedia MCP Servers

An analysis of your local Go-based monorepo at `/Users/ghchinoy/dev/vertex-ai-creative-studio-public/experiments/mcp-genmedia/mcp-genmedia-go/` shows that **every single Go-based MCP server natively supports remote hosting** out-of-the-box:
*   `mcp-veo-go`, `mcp-lyria-go`, and `mcp-imagen-go` all include flags for `-transport sse` (Server-Sent Events) and `-transport http` with built-in CORS configurations.
*   They accept port overrides using the `PORT` environment variable or the `-p` CLI argument.

### 3.1 Serverless Deployment via Google Cloud Run
To host these Go servers remotely and cost-effectively, we can deploy them to **Google Cloud Run**. Cloud Run is highly suitable because it scales down to zero when idle (costing nothing) and exposes an automatic secure HTTPS endpoint.

#### Unified Multi-Stage Dockerfile for Cloud Run
We can containerize any of your Go MCP servers using a single standard Dockerfile template:
```dockerfile
# Stage 1: Build static Go binary
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o mcp-server .

# Stage 2: Final minimal runtime container
FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/mcp-server .

# Cloud Run injects the PORT env var; we pass it to the Go CLI
EXPOSE 8080
CMD ["./mcp-server", "-transport", "sse", "-p", "8080"]
```

### 3.2 Security Strategies for Remote MCP Gateways
Because these MCP servers manage highly powerful generative AI models (Veo, Lyria, Imagen), **they must be strictly secured** to prevent unauthenticated internet access.

#### Option A: IAM-Based Invoker Authentication (Highly Recommended)
1.  Deploy the Cloud Run service with `"Require authentication"` checked. This disables public internet invocation.
2.  Grant the Service Account assigned to the Vertex AI managed agent the **Cloud Run Invoker** (`roles/run.invoker`) permission on the services.
3.  When the user or orchestration server calls the Interactions API, it fetches an OIDC identity token for the Cloud Run audience:
    ```bash
    export MCP_TOKEN=$(gcloud auth print-identity-token --audience="https://your-mcp-service.a.run.app")
    ```
4.  Pass this token to the managed interaction using the `agentsapi` CLI header flag:
    ```bash
    --mcp-server-header "Authorization=Bearer ${MCP_TOKEN}"
    ```
    The Vertex AI gateway will pass this secure header directly to Cloud Run, which validates the token and permits the interaction.

#### Option B: Private Security Token Validation (Simple Headers)
If Cloud Run is kept public (but hidden behind randomized hashes), we can inject a custom API key into the Go server's environment (e.g. `MCP_SECURITY_KEY=super_secret_hash_123`) and validate it via custom Go HTTP middleware in `mcp-common`. The agent passes this key via the CLI:
```bash
--mcp-server-header "x-mcp-token=super_secret_hash_123"
```

---

## 4. GCS Bucket Mounting and IAM Service Account Orchestration

### 4.1 Binds and Environments
Vertex AI Interactions support mounting GCS objects. When creating or starting an interaction, the `RemoteEnvironment` config defines where GCS buckets should be cloned within the sandbox:
*   We can mount **multiple sources** into the environment:
    1.  `gs://genai-blackbelt-fishfooding-assets/story-generator` $\rightarrow$ Mounted to `./agent/story-generator` (Skill Code).
    2.  `gs://genai-blackbelt-fishfooding-assets/media_in` $\rightarrow$ Mounted to `./agent/media` (Media Repository).

### 4.2 IAM Service Account Requirements
To avoid interactive OAuth login prompts (which fail in automated sandboxes), the managed agent relies on a Google Cloud Service Account context.

1.  **Assign a Service Account to the Client**: When executing your local CLI or running an automated cron job, ensure the active environment uses a dedicated Service Account:
    ```bash
    gcloud auth activate-service-account showrunner-deployer@your-project.iam.gserviceaccount.com --key-file=secrets.json
    ```
2.  **Grant Bucket Permissions**: Ensure the Service Account is granted the following IAM roles:
    *   **Storage Object Admin** (`roles/storage.objectAdmin`) on the bucket `genai-blackbelt-fishfooding-assets`. This allows the python scripts running inside the sandbox to seamlessly run `gcloud storage cp` or standard SDK writes to save synthesized audio/image files back to GCS without authentication failures.
    *   **Vertex AI User** (`roles/vertexai.user`) to allow starting interactions.

---

## 5. Setup Guide for the Managed Agent Experiment

To run a live trial of this cloud-sandboxed showrunner flow, follow this step-by-step terminal execution plan:

### Step 5.1: Deploy the upgraded Story-Generator Skill to GCS
Upload the version `1.3.0` skill structure to your GCS bucket:
```bash
gcloud storage cp -r /Users/ghchinoy/dev/vertex-ai-creative-studio-public/experiments/mcp-genmedia/skills/story-generator gs://genai-blackbelt-fishfooding-assets/story-generator
```

### Step 5.2: Create the Persistent Agent Profile
Define the cloud agent using the `agents` CLI. We pass the system instructions and map the GCS source to `./agent/story-generator` so that the code is pre-cloned:
```bash
./bin/agents create \
  --id "cloud-showrunner" \
  --desc "Vertex-Sandboxed Multi-Scene Showrunner Agent" \
  --instructions "You are a professional generative media showrunner. You reside in a sandbox. You use python3 to execute generate_scene.py and assemble_story.py located in ./agent/story-generator/scripts/. Follow the Story Generator Skill (v1.3.0) and run double-engine compositing natively in this VM." \
  --env-source "gs://genai-blackbelt-fishfooding-assets/story-generator" \
  --env-target "./agent/story-generator"
```

### Step 5.3: Initiate the Cloud Interaction (BYOMCP)
Start a live streaming interaction with your new cloud showrunner, attaching your secure remote MCP gateway:
```bash
# Fetch an OIDC token if using IAM Cloud Run invoker mode, otherwise bypass
export MCP_TOKEN=$(gcloud auth print-identity-token --audience="https://mcp-gateway-service.run.app" 2>/dev/null || echo "bypass")

./bin/agents interact create \
  --agent "cloud-showrunner" \
  --mcp-server-url "https://mcp-gateway-service.run.app" \
  --mcp-server-name "genmedia-cloud" \
  --mcp-server-header "Authorization=Bearer ${MCP_TOKEN}" \
  --prompt "Let's co-create a beautiful, scientific 3-scene story about Newtonian mechanics, using Newton's Cosmic Pond as our focal story. Guide me step-by-step through the Writers Room."
```

---

## 6. Conclusion
The "Story Generator v1.3.0" pipeline is architecturally ready for cloud-sandboxed migration. Because our orchestration and quality auditing Python scripts have **zero external pip dependencies**, deployment is highly robust. By utilizing Cloud Run's native HTTP/SSE capabilities alongside IAM OIDC token authentication, we can establish a production-grade, highly secure showrunning assistant that operates fully in the cloud.
