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
  description = "GCP project ID in which to create the Secret Manager secret containers."
  type        = string
}

variable "secret_ids" {
  description = "List of secret IDs to create as Secret Manager *containers* (one google_secret_manager_secret each). Defaults to [] so the module is dormant: with no IDs it creates zero secrets and zero bindings. Values/versions are loaded out-of-band by an operator; never authored in Terraform."
  type        = list(string)
  default     = []
}

variable "accessor_sa_email" {
  description = "Email of the runtime service account granted roles/secretmanager.secretAccessor per secret. When empty (\"\"), no accessor binding is created even if secret_ids is non-empty."
  type        = string
  default     = ""
}
