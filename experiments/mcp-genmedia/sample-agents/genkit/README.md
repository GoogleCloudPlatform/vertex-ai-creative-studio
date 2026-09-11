# Genkit Genmedia MCP client

Example [Genkit](https://firebase.google.com/docs/genkit) AI application using Genmedia MCP servers.

This sample wires three genmedia MCP servers over stdio: **Nano Banana**
(`mcp-nanobanana-go`, text/image→image — the current image server that replaces
the retired `imagen` server), **Veo** (`mcp-veo-go`), and **Chirp 3**
(`mcp-chirp3-go`).

## Prerequisites

* NodeJs (You can use the [nvm](https://github.com/nvm-sh/nvm) node manager to install this)
* The genmedia MCP server binaries (`mcp-nanobanana-go`, `mcp-veo-go`,
  `mcp-chirp3-go`) built and available on your `PATH`. See
  `experiments/mcp-genmedia` for build/install instructions.
* A Google Cloud project with the required APIs enabled. Export it before
  running:

  ```bash
  export GOOGLE_CLOUD_PROJECT="$(gcloud config get project)"
  ```

Install Genkit client

```bash
npm install -D genkit-cli
```

## Run Genkit MCP client

Genkit js genmedia MCP client

```bash
cd genkit-agent-js
npm i
npm run start
```

Open Genkit dev tools at localhost:4000


![genkt devtools screenshot](./assets/genkit-devtools.png)
