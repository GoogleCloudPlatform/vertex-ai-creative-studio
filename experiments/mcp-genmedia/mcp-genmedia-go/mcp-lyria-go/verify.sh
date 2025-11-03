#!/bin/bash
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


set -e

cd "$(dirname "$0")" # Change to the script's directory

if [[ -z "${PROJECT_ID}" ]]; then
  echo "PROJECT_ID environment variable must be set."
  exit 1
fi

# Build the server
go build -o mcp-lyria-go

# Run a basic liveness check by listing the tools
# If the server fails to start, this command will fail.
response=$(mcptools tools ./mcp-lyria-go)

# Check if the response contains the expected tool name
if [[ "$response" == *"lyria_generate_music"* ]]; then
  echo "Verification successful: 'lyria_generate_music' tool found."
else
  echo "Verification failed: Could not find 'lyria_generate_music' tool in the server's response."
  echo "Response was:"
  echo "$response"
  exit 1
fi
