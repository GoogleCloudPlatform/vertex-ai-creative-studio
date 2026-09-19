/**
* Copyright 2025 Google LLC
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

output "cluster_name" {
  description = "Name of the GKE Autopilot cluster."
  value       = google_container_cluster.creative_studio.name
}

output "endpoint" {
  description = "IP address of the cluster's Kubernetes API server. Consumed by the root to configure the kubernetes/kubectl providers."
  value       = google_container_cluster.creative_studio.endpoint
}

output "ca_certificate" {
  description = "Base64-encoded public cluster CA certificate. Consumed by the root to configure the kubernetes/kubectl providers."
  value       = google_container_cluster.creative_studio.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "location" {
  description = "Location (region) of the regional cluster."
  value       = google_container_cluster.creative_studio.location
}

output "workload_identity_pool" {
  description = "Workload Identity pool identifier (<project_id>.svc.id.goog) used to bind Kubernetes service accounts to Google service accounts."
  value       = "${var.project_id}.svc.id.goog"
}
