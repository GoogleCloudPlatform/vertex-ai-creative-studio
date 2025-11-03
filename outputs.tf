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

output "load-balancer-ip" {
  value       = var.use_lb ? module.lb-http[0].external_ip : ""
  description = "IP Address that should be used for DNS A record for the domain provided."
}

output "assets-bucket" {
  value       = google_storage_bucket.assets.name
  description = "Name of the GCS bucket where assets are stored."
}

output "cloud-run-app-url" {
  value       = !var.use_lb ? "https://${google_cloud_run_v2_service.creative_studio.name}-${data.google_project.project.number}.${google_cloud_run_v2_service.creative_studio.location}.run.app" : ""
  description = "The Cloud Run URL where the website can be reached."
}

output "builds-service-account" {
  value       = google_service_account.cloudbuild.email
  description = "Service Account used for Cloud Build"
}

output "application-service-account" {
  value       = google_service_account.creative_studio.email
  description = "Service Account used by the Creative Studio web application"
}
