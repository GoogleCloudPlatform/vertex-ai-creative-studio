# environments/nonprod.tfvars — non-production (staging) configuration (Phase 5).
#
# This is a WORKED, PROVEN example: this exact var set was validated end-to-end
# by the staging stand-up (staging-standup-report.md), which applied cleanly
# against a SEPARATE non-prod project with the SAME hardcoded resource names
# as prod — 47 added, 0 changed, 0 destroyed. It demonstrates the separate-
# project model (design.md §3.6.1): because non-prod is a different project,
# every project-scoped name and both project-derived GCS bucket names are unique
# per project, so nothing collides with prod. No name needs an env suffix.
#
# There are NO secrets in this file (the config has none — secret_ids/secret_env
# stay dormant). The project_id/initial_user below are placeholders; set them to
# your own non-prod project and owner when reusing this template.
#
# Backend state for this environment (supplied at init, NOT in this file):
#   terraform init -reconfigure \
#     -backend-config="bucket=<NONPROD_TF_STATE_BUCKET>" \
#     -backend-config="prefix=creative-studio/staging"
# (The stand-up used a non-prod state bucket with prefix
#  creative-studio/staging — isolated from the prod state object.)

# --- Deployment-specific inputs ---
project_id   = "REPLACE_WITH_NONPROD_PROJECT_ID"       # separate non-prod project (proven stand-up)
initial_user = "REPLACE_WITH_NONPROD_USER@example.com" # effectively required; the non-prod project OWNER (stand-up)

# --- Behavior-defining settings for non-prod ---
region               = "us-central1"
environment          = "staging" # cost-allocation label
use_lb               = false     # no custom domain in non-prod: use the Cloud Run URL + native IAP
enable_data_deletion = false     # keep buckets protected even in non-prod (safe default)

# use_lb = false means `domain` is not required (no managed cert; API_BASE_URL "").
# All other inputs inherit their repo defaults from variables.tf (models, sizing,
# max_instance_count = 10, labels team/owner/cost_center, P4 secrets dormant).
