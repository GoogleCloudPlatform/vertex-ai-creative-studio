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
