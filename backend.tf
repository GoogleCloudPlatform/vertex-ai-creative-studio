/**
* Copyright 2024 Google LLC
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

# Remote state backend (GCS).
#
# The state bucket is intentionally NOT hardcoded here so this configuration
# stays reusable across projects and no project-specific value is committed to
# version control. Supply the bucket at init time, e.g.:
#
#   terraform init -backend-config="bucket=YOUR_TF_STATE_BUCKET"
#
# The bucket must already exist and have versioning enabled. Create it once with:
#
#   gcloud storage buckets create gs://YOUR_TF_STATE_BUCKET \
#     --project=YOUR_PROJECT_ID --location=us-central1 --uniform-bucket-level-access
#   gcloud storage buckets update gs://YOUR_TF_STATE_BUCKET --versioning
#
# For multiple environments (non-prod + prod), select the state per environment
# by overriding the prefix at init and pairing it with a per-env variable file:
#
#   terraform init -reconfigure -backend-config="bucket=..." \
#       -backend-config="prefix=creative-studio/<env>"
#   terraform apply -var-file=environments/<env>.tfvars
#
# See environments/README.md. The default prefix below is the prod environment.
terraform {
  backend "gcs" {
    # bucket = "YOUR_TF_STATE_BUCKET"  # provide via -backend-config
    prefix = "creative-studio/prod"
  }
}
