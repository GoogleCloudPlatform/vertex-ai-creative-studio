#!/usr/bin/env bash
# build.sh — build + push the Creative Studio image via Cloud Build, then deploy
# it to Cloud Run as the CALLER.
#
# FU-5: cloudbuild.yaml now builds + pushes only (the embedded `gcloud run deploy`
# step was removed for least privilege). The deploy is therefore performed here,
# after the build, using the caller's own identity — mirroring how
# deploy/scripts/deploy.sh splits build (do_build) from deploy (do_deploy). This
# preserves build.sh's documented "builds and deploys" behavior without the Cloud
# Build service account needing roles/run.developer or act-as on the runtime SA.
#
# Expects PROJECT_ID and REGION to be set in the environment (see deploy.md).
set -euo pipefail

# 1. Build + push the image (Cloud Build runs cloudbuild.yaml as the
#    builds-creative-studio service account).
gcloud builds submit . --project="$PROJECT_ID" --gcs-source-staging-dir="gs://run-resources-$PROJECT_ID-$REGION/services/creative-studio" --region="$REGION" --service-account="projects/$PROJECT_ID/serviceAccounts/builds-creative-studio@$PROJECT_ID.iam.gserviceaccount.com"

# 2. Deploy the freshly-pushed image to Cloud Run as the caller.
gcloud run deploy creative-studio --project="$PROJECT_ID" --region="$REGION" --image="$REGION-docker.pkg.dev/$PROJECT_ID/creative-studio/creative-studio:latest" --timeout=3600
