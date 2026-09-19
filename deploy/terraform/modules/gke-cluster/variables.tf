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

variable "project_id" {
  description = "GCP project ID in which to create the GKE cluster."
  type        = string
}

variable "region" {
  description = "Region for the regional Autopilot cluster (cluster location)."
  type        = string
}

variable "cluster_name" {
  description = "Name of the GKE Autopilot cluster."
  type        = string
  default     = "creative-studio"
}

# Network strategy: default to the project's `default` VPC/subnet to keep the
# minimal/testing cluster simple. Point network/subnetwork at a dedicated VPC by
# overriding these inputs. Autopilot requires VPC-native networking; the empty
# ip_allocation_policy in main.tf lets GKE auto-provision secondary ranges on the
# chosen subnet.
variable "network" {
  description = "Name (or self_link) of the VPC network for the cluster. Defaults to the project's default network."
  type        = string
  default     = "default"
}

variable "subnetwork" {
  description = "Name (or self_link) of the subnetwork for the cluster. Defaults to the project's default subnet."
  type        = string
  default     = "default"
}

variable "release_channel" {
  description = "GKE release channel (RAPID, REGULAR, STABLE, or UNSPECIFIED)."
  type        = string
  default     = "REGULAR"
}

variable "deletion_protection" {
  description = "deletion_protection on the CLUSTER resource only. Default false so a non-prod cluster can be torn down cleanly. Never applied to a data-bearing resource."
  type        = bool
  default     = false
}

variable "apis_ready_dependency" {
  description = "Opaque dependency handle (e.g. the project-services module's apis_ready output) the cluster depends_on, so it is created only after container.googleapis.com is enabled. Defaults to null (no explicit ordering)."
  type        = any
  default     = null
}
