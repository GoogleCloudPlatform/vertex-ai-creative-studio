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

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Location for the Artifact Registry repo and Cloud Build staging bucket."
  type        = string
}

variable "initial_user" {
  description = "Email address of the initial user granted admin on the staging bucket."
  type        = string
  nullable    = true
  default     = null
}

variable "enable_data_deletion" {
  description = "Whether to allow force destroy on the staging bucket. Should be false in production."
  type        = bool
  default     = false
}

variable "build_sa_member" {
  description = "IAM member string for the Cloud Build service account (e.g. serviceAccount:...); granted reader/writer on the repo and creator/viewer on the staging bucket."
  type        = string
}

variable "deployer_members" {
  description = <<-EOT
    IAM member(s) for the DEPLOYER principal that runs `deploy.sh list-versions`
    and deploy-by-tag/digest. Each entry MUST be a fully-qualified, member-formatted
    string (e.g. "serviceAccount:deploy@PROJECT.iam.gserviceaccount.com" or
    "user:someone@example.com") — never a bare email. Each member receives an
    additive roles/artifactregistry.reader binding on the repo (needed to run
    `artifacts docker images list` and resolve digests). Defaults to [] (dormant:
    no binding created), so a default apply is unchanged; set it per environment
    (same list as the iam module's deployer_members) to codify the grant.
  EOT
  type        = list(string)
  default     = []
}

variable "cleanup_policy_dry_run" {
  description = "When true (default), Artifact Registry cleanup policies only LOG what they WOULD delete and delete nothing. The owner reviews the dry-run output, then flips to false on a later apply to enable real deletion."
  type        = bool
  default     = true
}

variable "cleanup_keep_count" {
  description = "Number of most-recent image versions the KEEP cleanup policy retains (tagged releases + their digests)."
  type        = number
  default     = 20
}

variable "cleanup_untagged_older_than" {
  description = "Age threshold (Go duration seconds string, e.g. \"2592000s\" = 30 days) above which UNTAGGED artifacts are eligible for deletion by the cleanup policy."
  type        = string
  default     = "2592000s"
}
