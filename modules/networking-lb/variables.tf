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
  description = "Region for the serverless network endpoint group."
  type        = string
}

variable "domain" {
  description = "Domain name for the managed SSL certificate."
  type        = string
}

variable "reserved_ip_address" {
  description = "Reserved (static) global IP address for the load balancer. When null, a static IP is created and managed by Terraform (google_compute_global_address) so it survives load balancer recreation."
  type        = string
  nullable    = true
  default     = null
}

variable "service_name" {
  description = "Name of the Cloud Run service that the serverless NEG points at."
  type        = string
}

variable "enable_iap" {
  description = "Whether IAP is enabled on the load balancer backend."
  type        = bool
  default     = true
}

variable "initial_user" {
  description = "Email address of the initial user granted IAP HTTPS access. When null, no grant is created."
  type        = string
  nullable    = true
  default     = null
}
