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

output "repo_name" {
  description = "Name of the Artifact Registry Docker repository."
  value       = google_artifact_registry_repository.creative_studio.name
}

output "repo_id" {
  description = "Fully-qualified Artifact Registry repository resource ID."
  value       = google_artifact_registry_repository.creative_studio.id
}

output "staging_bucket_name" {
  description = "Name of the Cloud Build staging (source) bucket."
  value       = "run-resources-${var.project_id}-${var.region}"
}
