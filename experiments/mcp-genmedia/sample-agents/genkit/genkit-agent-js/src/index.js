/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { genkit } from "genkit";
import { vertexAI, gemini20Flash } from "@genkit-ai/vertexai";
import { logger } from "genkit/logging";
import { mcpClient } from "genkitx-mcp";

logger.setLogLevel("debug");

// The genmedia MCP servers read their Google Cloud project from
// GOOGLE_CLOUD_PROJECT (LOCATION is optional; the servers default to
// us-central1). Set it before running, e.g. via `gcloud config get project`.
const projectId = process.env.GOOGLE_CLOUD_PROJECT;
const serverEnv = projectId ? { GOOGLE_CLOUD_PROJECT: projectId } : {};

// Nano Banana (Gemini image) is the current text/image->image server.
// It replaces the retired `imagen` server, which was shut down and removed.
const nanobananaClient = mcpClient({
  name: 'nanobanana',
  version: '1.0.0',
  serverProcess: {
    command: 'mcp-nanobanana-go',
    env: serverEnv,
  },
});

const veoClient = mcpClient({
  name: 'veo',
  version: '1.0.0',
  serverProcess: {
    command: 'mcp-veo-go',
    env: serverEnv,
  },
});

const chirp3Client = mcpClient({
  name: 'chirp3',
  version: '1.0.0',
  serverProcess: {
    command: 'mcp-chirp3-go',
    env: serverEnv,
  },
});

const ai = genkit({
  plugins: [vertexAI({ location: "us-central1" }),
    nanobananaClient,
    veoClient,
    chirp3Client
  ],
  model: gemini20Flash,
});
