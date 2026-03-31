#!/bin/bash

set -e

# Ensure GOOGLE_CLOUD_PROJECT is set
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
  echo "Error: GOOGLE_CLOUD_PROJECT environment variable is not set." >&2
  exit 1
fi

# Step 1: Generate a base image and capture its GCS URI
echo "INFO: Generating base image for testing..."
GEN_RESULT=$(mcptools --json call imagen_t2i --params '{"prompt": "a golden retriever sitting on a green couch", "gcs_bucket_uri": "gs://genai-blackbelt-fishfooding-assets"}' ./mcp-imagen-go)
echo "$GEN_RESULT" > result.json
IMAGE_URI=$(echo "$GEN_RESULT" | jq -r '.structuredContent.gcsUris[0]')

if [ -z "$IMAGE_URI" ]; then
  echo "ERROR: Failed to generate base image or parse GCS URI." >&2
  echo "Full generation result: $GEN_RESULT" >&2
  exit 1
fi
echo "INFO: Base image created at: $IMAGE_URI"
echo "INFO: Verifying image existence in GCS with command: gcloud storage ls \"$IMAGE_URI\""
gcloud storage ls "$IMAGE_URI"
sleep 5

# Step 2: Call the editing tool to remove the dog
echo "INFO: Calling inpainting_remove to remove the dog..."
EDIT_PARAMS=$(printf '{"image_uri": "%s", "mask_mode": "MASK_MODE_SEMANTIC", "segmentation_classes": ["dog"]}' "$IMAGE_URI")
EDIT_RESULT=$(mcptools call imagen_edit_inpainting_remove --params "$EDIT_PARAMS" ./mcp-imagen-go)

# Step 3: Verify the edit was successful
if [ $? -eq 0 ]; then
  echo "SUCCESS: Inpainting remove tool executed successfully."
  echo "INFO: Edit result: $EDIT_RESULT"
  EDITED_IMAGE_URI=$(echo "$EDIT_RESULT" | grep -o 'gs://[^"]*' | head -n 1)
  echo "INFO: Edited image URI: $EDITED_IMAGE_URI"
else
  echo "ERROR: Inpainting remove tool failed." >&2
  exit 1
fi

# --- Additional test cases for other features will be added below --- #