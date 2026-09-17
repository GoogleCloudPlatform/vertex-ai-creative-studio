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

output "runtime_sa_email" {
  description = "Email of the runtime (application) service account."
  value       = google_service_account.creative_studio.email
}

output "runtime_sa_member" {
  description = "IAM member string for the runtime service account (serviceAccount:...)."
  value       = google_service_account.creative_studio.member
}

output "runtime_sa_name" {
  description = "Fully-qualified resource name of the runtime service account (projects/.../serviceAccounts/...)."
  value       = google_service_account.creative_studio.name
}

output "build_sa_email" {
  description = "Email of the Cloud Build service account."
  value       = google_service_account.cloudbuild.email
}

output "build_sa_member" {
  description = "IAM member string for the Cloud Build service account (serviceAccount:...)."
  value       = google_service_account.cloudbuild.member
}
