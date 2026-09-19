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

output "secret_ids" {
  description = "List of created secret IDs (empty when the module is dormant)."
  value       = [for s in google_secret_manager_secret.secrets : s.secret_id]
}

output "secret_version_refs" {
  description = "Map of secret ID => fully-qualified secret resource ID (projects/PROJECT/secrets/NAME). Use as the `secret` in a Cloud Run secret_key_ref; the `version` is chosen by the consumer (e.g. \"latest\"). Empty when dormant. No versions are created by Terraform."
  value       = { for k, s in google_secret_manager_secret.secrets : k => s.id }
}
