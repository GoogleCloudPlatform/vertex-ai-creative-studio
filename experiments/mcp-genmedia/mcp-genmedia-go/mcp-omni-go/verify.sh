#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "building mcp-omni-go..."
go build -o mcp-omni-go .

echo "verifying mcp-omni-go with mcptools..."
mcptools tools ./mcp-omni-go

echo "SUCCESS: mcp-omni-go verified"
