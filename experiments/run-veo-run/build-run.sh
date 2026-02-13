#!/bin/bash
# Local Build & Run for Run, Veo, Run
set -e

# Load .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Ensure public dir exists
mkdir -p frontend/public

# Copy Changelog if it exists
if [ -f CHANGELOG.md ]; then
    cp CHANGELOG.md frontend/public/
fi

echo "🏗️  Building Frontend..."
cd frontend && npm run build

echo "🚀 Starting Server..."
cd ../server && PORT=8080 go run .
