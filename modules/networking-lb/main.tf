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

# networking-lb module: the reserved global IP, the external HTTPS load balancer
# (lb-http/serverless_negs) with managed cert + IAP backend, and the serverless
# NEG pointing at the Cloud Run service. This whole module is count-gated by
# var.use_lb in the root (instantiated only when the LB topology is in use), so
# the per-resource use_lb gating that lived at the root collapses to "always on"
# here. Behavior-preserving; all attribute values preserved exactly.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.49"
    }
  }
}

# Reserved (static) global IP for the external load balancer. Managed by
# Terraform so the address is stable across load balancer recreation. When
# var.reserved_ip_address is set, that pre-existing address is used instead.
resource "google_compute_global_address" "lb_ipv4" {
  count      = var.reserved_ip_address == null ? 1 : 0
  name       = "creativestudio-lb-ip"
  ip_version = "IPV4"
}

module "lb-http" {
  source                          = "terraform-google-modules/lb-http/google//modules/serverless_negs"
  version                         = "~> 14.0"
  name                            = "creativestudio"
  project                         = var.project_id
  load_balancing_scheme           = "EXTERNAL_MANAGED"
  ssl                             = true
  managed_ssl_certificate_domains = [var.domain]
  https_redirect                  = true
  address                         = coalesce(var.reserved_ip_address, one(google_compute_global_address.lb_ipv4[*].address))
  create_address                  = false
  backends = {
    default = {
      description = "Creative Studio backend"
      protocol    = "HTTPS"
      enable_cdn  = false
      groups = [
        {
          group = google_compute_region_network_endpoint_group.cloudrun_neg.id
        }
      ]
      iap_config = {
        enable = var.enable_iap
      }
      log_config = {
        enable = true
      }
    }
  }
}

resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "cloudrun-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = var.service_name
  }
}

# IAP HTTPS access for the initial user. This whole module is count-gated by
# var.use_lb in the root, so the root's `use_lb && initial_user != null` gate
# collapses here to just the initial_user check. Behaviour preserved exactly.
resource "google_iap_web_iam_member" "initial_user_iap_access" {
  count  = var.initial_user != null ? 1 : 0
  role   = "roles/iap.httpsResourceAccessor"
  member = "user:${var.initial_user}"
}
