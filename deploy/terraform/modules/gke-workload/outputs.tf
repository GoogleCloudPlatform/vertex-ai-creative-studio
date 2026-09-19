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

output "ingress_ip" {
  description = "Reserved global static IP for the ingress (empty when create_static_ip is false and an external address is used)."
  value       = var.create_static_ip ? google_compute_global_address.ingress_ip[0].address : null
}

output "service_hostname" {
  description = "In-cluster DNS hostname of the NEG-backed Service (<name>.<namespace>.svc.cluster.local)."
  value       = "${kubernetes_service_v1.workload.metadata[0].name}.${var.namespace}.svc.cluster.local"
}

output "neg_name" {
  description = "Name of the Service that carries the standalone NEG annotation (the NEG itself is created by GKE at apply from this Service)."
  value       = kubernetes_service_v1.workload.metadata[0].name
}

output "static_ip_name" {
  description = "Name of the reserved global static IP referenced by the ingress annotation."
  value       = var.static_ip_name
}
