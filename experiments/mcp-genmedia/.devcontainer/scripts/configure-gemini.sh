#!/usr/bin/env bash
set -euo pipefail

template_path="/usr/local/share/mcp-genmedia-devcontainer/templates/gemini-extension.json"
extension_dir="${HOME}/.gemini/extensions/google-genmedia-devcontainer"

project_id="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-}}"
if [[ -z "${project_id}" ]] && command -v gcloud >/dev/null 2>&1; then
  project_id="$(gcloud config get-value project 2>/dev/null || true)"
fi

location="${LOCATION:-us-central1}"
genmedia_bucket="${GENMEDIA_BUCKET:-}"
if [[ -z "${genmedia_bucket}" && -n "${project_id}" ]]; then
  genmedia_bucket="gs://${project_id}-mcp-genmedia"
fi

export PROJECT_ID="${project_id}"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-${project_id}}"
export LOCATION="${location}"
export GENMEDIA_BUCKET="${genmedia_bucket}"

mkdir -p "${extension_dir}"
envsubst '${PROJECT_ID} ${GOOGLE_CLOUD_PROJECT} ${LOCATION} ${GENMEDIA_BUCKET}' \
  < "${template_path}" \
  > "${extension_dir}/gemini-extension.json"

echo "Configured Gemini CLI extension at ${extension_dir}/gemini-extension.json"
echo "PROJECT_ID=${PROJECT_ID:-unset}"
echo "LOCATION=${LOCATION}"
echo "GENMEDIA_BUCKET=${GENMEDIA_BUCKET:-unset}"
