#!/bin/bash
# Deploy Run, Veo, Run
set -e

# Load .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

export PROJECT_ID=$(gcloud config get project)

# Use env var or default to the project-specific SA
if [ -z "$SERVICE_ACCOUNT_EMAIL" ]; then
    export SERVICE_ACCOUNT_EMAIL="sa-run-veo-run@${PROJECT_ID}.iam.gserviceaccount.com"
fi

export SERVICE_NAME="run-veo-run"
export IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Deploying $SERVICE_NAME to $PROJECT_ID..."
echo "Using Identity: $SERVICE_ACCOUNT_EMAIL"

echo "Submitting to Cloud Build..."
gcloud builds submit --tag $IMAGE_TAG .

echo "Deploying to Cloud Run..."
gcloud beta run deploy $SERVICE_NAME \
  --image $IMAGE_TAG \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --region us-central1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},VEO_BUCKET=${VEO_BUCKET},GEMINI_MODEL=${GEMINI_MODEL},GEMINI_MODEL_LOCATION=${GEMINI_MODEL_LOCATION},VEO_MODEL=${VEO_MODEL} \
  --iap \
  --no-allow-unauthenticated 
