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
  value       = module.gke_cluster.cluster_name
}

output "cluster_location" {
  description = "Location (region) of the regional cluster. Use with `gcloud container clusters get-credentials` for kubectl access."
  value       = module.gke_cluster.location
}

output "workload_identity_pool" {
  description = "Workload Identity pool (<project_id>.svc.id.goog) the KSA is bound to."
  value       = module.gke_cluster.workload_identity_pool
}

output "ingress_static_ip" {
  description = "Reserved global static IP for the ingress. Point the DNS A record for the domain at this address (empty when create_static_ip is false)."
  value       = module.gke_workload.ingress_ip
}

output "ingress_static_ip_name" {
  description = "Name of the reserved global static IP referenced by the ingress annotation."
  value       = module.gke_workload.static_ip_name
}

output "service_hostname" {
  description = "In-cluster DNS hostname of the NEG-backed Service."
  value       = module.gke_workload.service_hostname
}

output "neg_name" {
  description = "Name of the Service carrying the standalone NEG annotation (the NEG is created by GKE at apply)."
  value       = module.gke_workload.neg_name
}

output "assets_bucket" {
  description = "Name of the assets GCS bucket the workload reads/writes (read-only reference in this root)."
  value       = data.google_storage_bucket.assets.name
}

output "application_service_account" {
  description = "Email of the runtime service account the pods authenticate as via Workload Identity (read-only reference)."
  value       = data.google_service_account.runtime.email
}
