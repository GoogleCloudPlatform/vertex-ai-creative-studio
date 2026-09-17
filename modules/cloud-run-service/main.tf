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

# cloud-run-service module: the canonical compute surface — the Creative Studio
# google_cloud_run_v2_service plus the IAM bindings that reference it directly
# (the build service-account bindings the Cloud Run resource is ordered after,
# the build-service run.developer grant, and the IAP service identity + its
# run.invoker grant). Relocating these here — now that Group C dissolved the
# use_lb / env-var / CORS couplers — keeps the Cloud Run resource and everything
# that points at it inside one module without the module-level cycle that blocked
# Group B (build bindings in iam <-> root Cloud Run). Behaviour-preserving; every
# attribute value is preserved exactly. The use_lb-derived fields arrive as
# explicit inputs (ingress_mode + auth fields); env vars arrive as an explicit
# map assembled in the root.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.49"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.49"
    }
  }
}

/* There are times when IAP service account is not automatically provisioned, creating explicitly to be sure */
resource "google_project_service_identity" "iap_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "iap.googleapis.com"
}

resource "google_cloud_run_v2_service" "creative_studio" {
  provider             = google-beta
  name                 = "creative-studio"
  location             = var.region
  project              = var.project_id
  ingress              = var.ingress_mode
  default_uri_disabled = var.default_uri_disabled
  deletion_protection  = false
  iap_enabled          = var.iap_enabled
  invoker_iam_disabled = var.invoker_iam_disabled
  launch_stage         = var.launch_stage

  template {
    timeout                          = var.timeout
    max_instance_request_concurrency = var.concurrency
    containers {
      name  = "creative-studio"
      image = var.image
      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }
      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
    }
    service_account = var.runtime_sa_email
    scaling {
      max_instance_count = var.max_instance_count
    }
  }
  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }
  depends_on = [
    google_service_account_iam_member.build_act_as_creative_studio,
    google_project_iam_member.build_logs_writer,
  ]
}

resource "google_cloud_run_service_iam_member" "iap_cloudrun_access" {
  location = google_cloud_run_v2_service.creative_studio.location
  service  = google_cloud_run_v2_service.creative_studio.name
  role     = "roles/run.invoker"
  member   = google_project_service_identity.iap_sa.member
}

/********************************************
*  Build time bindings that reference Cloud Run
*********************************************/

# These build-SA bindings live alongside the Cloud Run resource: the service
# depends_on the first two directly, and build_service references the service.
# They consume the SA identities from the iam module (passed in as inputs).
resource "google_service_account_iam_member" "build_act_as_creative_studio" {
  service_account_id = var.runtime_sa_name
  role               = "roles/iam.serviceAccountUser"
  member             = var.build_sa_member
}

resource "google_project_iam_member" "build_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = var.build_sa_member
}

resource "google_cloud_run_service_iam_member" "build_service" {
  location = google_cloud_run_v2_service.creative_studio.location
  service  = google_cloud_run_v2_service.creative_studio.name
  role     = "roles/run.developer"
  member   = var.build_sa_member
}
