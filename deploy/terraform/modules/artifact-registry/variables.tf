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
