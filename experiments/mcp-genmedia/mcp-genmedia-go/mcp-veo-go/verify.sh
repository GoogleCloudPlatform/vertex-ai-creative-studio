#!/bin/bash
#
# This script performs a basic verification of the mcp-veo-go server.
# It ensures that the server builds and is responsive to a basic MCP request.

set -e

echo "Building mcp-veo-go..."
go build

echo "Verifying mcp-veo-go server..."
mcptools tools ./mcp-veo-go

echo "Verification successful!"
