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

# FU-3: compute an immutable per-build version tag. Three cases, so the commit SHA
# is preserved for provenance whenever one exists:
#   - clean git checkout:  v<UTC-timestamp>-<gitShortSHA>       (e.g. v20260920t153012z-3eb17bf)
#   - dirty working tree:  v<UTC-timestamp>-<gitShortSHA>-dirty (keeps the SHA, marks it dirty)
#   - true non-git:        v<UTC-timestamp>-nogit               (no repo / no resolvable HEAD)
# A version tag is ALWAYS produced and never collides with a clean build. cloudbuild.yaml
# pushes this tag AND the moving :latest to the same digest; when _VERSION_TAG is empty
# only :latest is pushed.
_ts="$(date -u +%Y%m%dt%H%M%Sz)"
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1 &&
   _sha="$(git rev-parse --short=7 HEAD 2>/dev/null)" && [ -n "$_sha" ]; then
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    VERSION_TAG="v${_ts}-${_sha}-dirty"
  else
    VERSION_TAG="v${_ts}-${_sha}"
  fi
else
  VERSION_TAG="v${_ts}-nogit"
fi
echo "Build version tag: ${VERSION_TAG} (also updates :latest)"

# 1. Build + push the image (Cloud Build runs cloudbuild.yaml as the
#    builds-creative-studio service account).
gcloud builds submit . --project="$PROJECT_ID" --gcs-source-staging-dir="gs://run-resources-$PROJECT_ID-$REGION/services/creative-studio" --region="$REGION" --service-account="projects/$PROJECT_ID/serviceAccounts/builds-creative-studio@$PROJECT_ID.iam.gserviceaccount.com" --substitutions="_VERSION_TAG=$VERSION_TAG"

# 2. Deploy the freshly-pushed image to Cloud Run as the caller.
gcloud run deploy creative-studio --project="$PROJECT_ID" --region="$REGION" --image="$REGION-docker.pkg.dev/$PROJECT_ID/creative-studio/creative-studio:latest" --timeout=3600
