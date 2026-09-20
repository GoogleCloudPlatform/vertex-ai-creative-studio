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

variable "firestore_db_id" {
  description = "Fully-qualified Firestore database resource ID, used to scope the runtime SA's datastore.user IAM condition."
  type        = string
}

variable "assets_bucket_name" {
  description = "Name of the assets GCS bucket that the runtime SA and initial user are granted access to."
  type        = string
}

variable "initial_user" {
  description = "Email address of the initial user granted objectAdmin on the assets bucket."
  type        = string
  nullable    = true
  default     = null
}

variable "deployer_members" {
  description = <<-EOT
    IAM member(s) for the DEPLOYER principal that submits Cloud Builds during a
    deploy (e.g. the environment's deploy service account or a human operator).
    Each entry MUST be a fully-qualified, member-formatted string
    (e.g. "serviceAccount:deploy@PROJECT.iam.gserviceaccount.com" or
    "user:someone@example.com") — never a bare email. Each member receives an
    additive project-scoped roles/cloudbuild.builds.editor binding so the
    deployer can run `gcloud builds submit`. Codifies the previously-manual
    staging grant (IAM drift) as Terraform-managed. Defaults to [] (dormant: no
    binding created), so a default apply is unchanged; set it per environment to
    reconcile the grant.
  EOT
  type        = list(string)
  default     = []
}
