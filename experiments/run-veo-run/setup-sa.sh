#!/bin/bash
# Setup Service Account for Run, Veo, Run
set -e

PROJECT_ID=$(gcloud config get project)
SA_NAME="sa-run-veo-run"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
DISPLAY_NAME="Runtime SA for Run, Veo, Run"

echo "Configuring Service Account for project: $PROJECT_ID"

# 1. Create Service Account if it doesn't exist
if ! gcloud iam service-accounts describe "$SA_EMAIL" > /dev/null 2>&1; then
    echo "Creating service account $SA_NAME..."
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="$DISPLAY_NAME"
else
    echo "Service account $SA_NAME already exists."
fi

# 2. Assign Roles
# Required for Veo (Vertex AI) and Gemini
echo "Assigning roles..."

# Vertex AI User (for Veo/Gemini)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user" > /dev/null

# Storage Object User (for saving/reading generated videos)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectUser" > /dev/null

# Logging Log Writer (for Cloud Run logs)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/logging.logWriter" > /dev/null

# Service Account Token Creator (for signing URLs via IAM API)
# The SA needs this permission on ITSELF to sign bytes.
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountTokenCreator" > /dev/null

echo "✅ Service Account configured: $SA_EMAIL"
echo "You can now deploy using: export SERVICE_ACCOUNT_EMAIL=$SA_EMAIL && ./deploy.sh"
