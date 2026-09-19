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

output "apis_ready" {
  description = "Dependency handle that is resolved once APIs are enabled and the eventual-consistency wait has elapsed. Downstream modules depend_on this to replace the former null_resource.sleep."
  value       = null_resource.sleep.id
}

output "project_id" {
  description = "Project ID passed through from the underlying project_services module."
  value       = module.project_services.project_id
}
