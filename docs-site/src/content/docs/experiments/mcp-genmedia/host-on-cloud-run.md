---
title: "Hosting MCP Servers on Cloud Run"
description: "Learn how to deploy Go MCP servers to Cloud Run and integrate them with Gemini Enterprise or Agent Registry."
---

This guide explains how to containerize and host the Go implementations of Model Context Protocol (MCP) servers on Google Cloud Run using the **Streamable HTTP** transport. 

It also covers how to test these servers locally, automate deployment with helper scripts, configure permissions, and connect them directly to **Gemini Enterprise** or **Agent Registry**.

---

## 1. Why Streamable HTTP on Cloud Run?

Standard MCP servers typically use the `stdio` transport, which communicates via standard input and output. This works well for local execution, but cannot be easily hosted on serverless platforms.

Cloud Run supports hosting MCP servers via the **Streamable HTTP** transport (aligned with the 2025-03-26 MCP specification). For detailed product features, refer to the official [Cloud Run MCP Servers Documentation](https://docs.cloud.google.com/run/docs/host-mcp-servers). Under this protocol:
*   The MCP client initiates a session and communicates with the server via standard HTTP `POST` requests carrying JSON-RPC payloads.
*   The server responds with `Content-Type: text/event-stream` and streams notifications or updates back to the client.
*   Cloud Run handles the secure HTTPS endpoints, scaling, and IAM-based access control automatically.

Every Go MCP server in this repository has built-in support for both `stdio` and `http` (Streamable HTTP) transports.

---

## 2. Local Testing of Streamable HTTP

Before deploying to the cloud, you can test the streamable HTTP transport locally.

### Step 1: Build the Server Binary
Navigate to the root directory of the Go workspace (`experiments/mcp-genmedia/mcp-genmedia-go/`) and build the binary for the server you want to test (e.g., `mcp-nanobanana-go`):

```bash
cd experiments/mcp-genmedia/mcp-genmedia-go/mcp-nanobanana-go
go build -o mcp-nanobanana-go
```

### Step 2: Run the Server in HTTP Mode
Run the server by setting the `-transport` (or `-t`) flag to `http` and specifying a port with `-port` (or `-p`):

```bash
export GOOGLE_CLOUD_PROJECT="your-google-cloud-project-id"
./mcp-nanobanana-go -transport http -port 9090
```

### Step 3: Perform a Handshake
An MCP Streamable HTTP client first sends an `initialize` request to the server:

```bash
curl -i -X POST http://localhost:9090/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'
```

The response will return:
1. Status `200 OK`
2. A header named `Mcp-Session-Id` (e.g. `mcp-session-xxxx-xxxx-...`)
3. A JSON-RPC body declaring the server's capabilities and details.

For subsequent requests, you must pass the `Mcp-Session-Id` header:

```bash
curl -i -X POST http://localhost:9090/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: your-session-id-here" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

---

## 3. Containerizing the Servers

To host a Go MCP server on Cloud Run, we package it into a container image. A generic `Dockerfile` is provided at `experiments/mcp-genmedia/mcp-genmedia-go/Dockerfile`. 

This Dockerfile uses multi-stage builds to produce light-weight production images and uses a build argument (`SERVER_NAME`) to specify which MCP server module to compile.

### Dockerfile Optimizations:
*   **Workspace Bypassing**: Compiles using `GOWORK=off` inside the Docker image. This allows compiling individual submodules in isolation without copying other server directories.
*   **Conditional Build Stages**: Uses a shell conditional statement to install heavy packages (like `ffmpeg` for `mcp-avtool-go`) only if compiling the target server, saving ~100MB of image size for other lightweight servers.

---

## 4. Deploying to Cloud Run

### Option A: Using the Automated Deployment Script (Preferred / Convenience Method)

For the quickest and most convenient deployment experience, use the interactive helper script. This automates the entire flow—verifying/creating the registry repository, executing the container build, deploying to Cloud Run, injecting required project environment variables, and configuring the necessary Google Cloud AI and GCS IAM role bindings in one command.

Run the script from the root of the Go MCP workspace (`experiments/mcp-genmedia/mcp-genmedia-go/`) and follow the prompts:
```bash
./deploy-cloudrun.sh
```

---

### Option B: Manual Step-by-Step Deployment

If you prefer to run the deployment commands manually, perform the following steps:

##### Step 1: Create a Private Artifact Registry Repository
Create a Docker repository in your own Google Cloud project to store the compiled images:

```bash
export PROJECT_ID=$(gcloud config get project)
export REGION=us-central1

gcloud artifacts repositories create mcp-servers \
  --repository-format=docker \
  --location=${REGION} \
  --description="Repository for hosted MCP servers"
```

##### Step 2: Build the Container Image in the Cloud
Run the following command from the Go workspace root directory (`experiments/mcp-genmedia/mcp-genmedia-go/`) to build the container image using Google Cloud Build (which invokes `cloudbuild.yaml` to pass the required `SERVER_NAME` compilation argument):

```bash
export PROJECT_ID=$(gcloud config get project)
export REGION=us-central1
export SERVER_NAME=mcp-nanobanana-go

# Submit the build using substitutions
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --substitutions=_IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/mcp-servers/${SERVER_NAME}:latest,_SERVER_NAME=${SERVER_NAME}
```

##### Step 3: Deploy the Custom Image to Cloud Run
Deploy the newly built container image to a Cloud Run service. You **must** set the `GOOGLE_CLOUD_PROJECT` environment variable on the container so it can locate Google Cloud AI resources:

```bash
gcloud run deploy ${SERVER_NAME} \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/mcp-servers/${SERVER_NAME}:latest \
  --region=${REGION} \
  --port=8080 \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID},LOCATION=${REGION}
```

##### Step 4: Configure IAM Permissions
Ensure that the Cloud Run service account has the necessary permissions to access Google Cloud services:
1. **Vertex AI User** (`roles/aiplatform.user`): Required for image, video, text, and music generation models.
2. **Storage Object Admin** (`roles/storage.objectAdmin`): Required if the server needs to read/write outputs to a Google Cloud Storage bucket.

```bash
# Get the Cloud Run service account
export SERVICE_ACCOUNT=$(gcloud run services describe ${SERVER_NAME} --region=${REGION} --format="value(spec.template.spec.serviceAccountName)")

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user"
```

---

## 5. Authenticating and Connecting Local Clients

Because we deployed the Cloud Run service as **unauthenticated disabled** (`--no-allow-unauthenticated`), standard HTTP requests without credentials will be rejected with a `403 Forbidden` error.

The most secure and convenient way to authenticate a local client (like Claude Desktop or another tool) to the private Cloud Run service is to run the **Cloud Run services proxy** on your local machine.

### Step 1: Start the Cloud Run Proxy
Run the proxy command in your terminal. This creates a secure, authenticated local tunnel on port `3000` that automatically forwards requests to the remote Cloud Run service while injecting your `gcloud` credentials:

```bash
gcloud run services proxy ${SERVER_NAME} \
  --region=${REGION} \
  --port=3000
```
Keep this terminal window open.

### Step 2: Configure the MCP Client
Configure your local MCP client (such as Claude Desktop) to connect to the local proxy URL.

Open your client config file (e.g., `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "mcp-nanobanana-cloudrun": {
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

Restart your MCP client. It will connect to `http://localhost:3000/mcp` which forwards securely to your hosted Cloud Run MCP server.

---

## 6. Connecting to Gemini Enterprise (Custom Connectors)

Gemini Enterprise allows organizations to bind external MCP servers directly into the Google Cloud Console or Gemini Workspace assistant using **Custom Connectors**. For more details and configuration prerequisites, refer to the official [Gemini Enterprise Custom Connector Documentation](https://docs.cloud.google.com/gemini/enterprise/docs/connectors/custom-mcp-server/set-up-custom-mcp-server).

Because Gemini Enterprise acts as a managed client on behalf of users, it requires **OAuth 2.0 User Authentication** to access private Cloud Run services.

### Pathway: Private Cloud Run Service with Google Identity (OAuth)

1. **Deploy your service** to Cloud Run as private (`--no-allow-unauthenticated`).
2. **Register Gemini Enterprise as an OAuth client** in your Google Cloud Project:
   * Navigate to **APIs & Services > Credentials**.
   * Create an **OAuth Client ID** for a **Web application**.
   * Set the Authorized redirect URI to:
     `https://vertexaisearch.cloud.google.com/oauth-redirect`
   * Save the generated **Client ID** and **Client Secret**.
3. **Register the Custom MCP Server in Gemini Enterprise**:
   * Navigate to **Gemini Enterprise > Data stores** in the GCP Console.
   * Click **Create data store** and select **Custom MCP Server (Preview)**.
   * Fill in the settings:
     * **MCP Server URL**: `https://<your-mcp-service-xxxx>.run.app/mcp`
     * **Authorization URL**: `https://accounts.google.com/o/oauth2/v2/auth`
     * **Authorization URL Parameters**: `&audience=https://<your-mcp-service-xxxx>.run.app` *(Crucial: This generates a token valid for Cloud Run)*
     * **Token URL**: `https://oauth2.googleapis.com/token`
     * **Client ID & Client Secret**: *(The Web OAuth client credentials from Step 2)*
     * **Scopes**: `openid email profile`
4. **Enable Actions**: Once the data store is `Active`, go to **Actions > Reload custom actions**, select the tools you want to make active, and click **Enable actions**.

---

## 7. Cataloging in Vertex AI Agent Registry

**Agent Registry** acts as a centralized catalog inside Google Cloud for MCP server endpoints and tools. Instead of hardcoding URLs, AI orchestrators (using the Google ADK) can dynamically discover and invoke tools from Agent Registry. For details on registering servers, refer to the official [Agent Registry MCP Documentation](https://docs.cloud.google.com/agent-registry/register-mcp-servers).

### Step 1: Generate `toolspec.json`
Agent Registry requires a tool specification file (max 10 KB). You can generate this directly from your Go MCP binary:

```bash
# Query the tools/list JSON-RPC method from the local binary
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ./mcp-nanobanana-go | jq '.result' > toolspec.json
```

### Step 2: Register the Server in Agent Registry
Run the following `gcloud` command to register your service:

```bash
gcloud alpha agent-registry services create mcp-nanobanana-go \
  --project=$(gcloud config get project) \
  --location=us-central1 \
  --display-name="Nanobanana Image Generator" \
  --mcp-server-spec-type=tool-spec \
  --mcp-server-spec-content=toolspec.json \
  --interfaces=url=https://mcp-nanobanana-go-xxxx.run.app/mcp,protocolBinding=JSONRPC
```

### Step 3: Resolve the Toolset in Code
Using the **Agent Development Kit (`google-adk`)**, you can fetch and call tools from the registry dynamically:

```python
from google.adk.agents.llm_agent import LlmAgent
from google.adk.integrations.agent_registry import AgentRegistry

# Initialize registry client
registry = AgentRegistry(project_id="my-project", location="us-central1")

# Retrieve the registered MCP toolset dynamically
my_mcp_toolset = registry.get_mcp_toolset("mcpServers/mcp-nanobanana-go")

# Compose the agent
agent = LlmAgent(
    name="banana_artist",
    model="gemini-1.5-flash",
    tools=[my_mcp_toolset],
    instruction="Generate images using the provided tool when requested."
)
```
