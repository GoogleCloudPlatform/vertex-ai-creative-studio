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
  description = "Location for the data-store resources (bucket, Firestore, Cloud Tasks queue)."
  type        = string
}

variable "bucket_name" {
  description = "Name of the assets GCS bucket."
  type        = string
}

variable "cors_domains" {
  description = "List of CORS origins allowed on the assets bucket."
  type        = list(string)
}

variable "enable_data_deletion" {
  description = "Whether to allow force destroy on the bucket and disable Firestore delete protection. Should be false in production."
  type        = bool
  default     = false
}

variable "asset_lifecycle_age_days" {
  description = "Age in days after which objects in the assets bucket are deleted by a lifecycle rule. Set to 0 to disable the lifecycle rule."
  type        = number
  default     = 90
}
