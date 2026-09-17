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

# iam module: the runtime (application) service account, the Cloud Build service
# account, and all of their platform-agnostic IAM bindings. The Vertex AI service
# agent identity + binding live here as well. Behavior-preserving; every attribute
# value is preserved exactly. Bindings that reference the Cloud Run service
# (build_service, iap_cloudrun_access) remain in the root for now to avoid a
# module-level dependency cycle with the root's Cloud Run resource.

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

/********************************************
*  Runtime service account + bindings
*********************************************/

resource "google_service_account" "creative_studio" {
  account_id = "service-creative-studio"
}

resource "google_project_iam_member" "creative_studio_tasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = google_service_account.creative_studio.member
}

/* There are times when Vertex service account is not automatically provisioned, creating explicitly to be sure */
resource "google_project_service_identity" "vertex_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "aiplatform.googleapis.com"
}

resource "google_project_iam_member" "vertex_sa_access" {
  project = var.project_id
  role    = "roles/aiplatform.serviceAgent"
  member  = google_project_service_identity.vertex_sa.member
}

resource "google_storage_bucket_iam_member" "admins" {
  bucket = var.assets_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "user:${var.initial_user}"
}

resource "google_storage_bucket_iam_member" "creators" {
  bucket = var.assets_bucket_name
  role   = "roles/storage.objectCreator"
  member = google_service_account.creative_studio.member
}

resource "google_storage_bucket_iam_member" "viewers" {
  bucket = var.assets_bucket_name
  role   = "roles/storage.objectViewer"
  member = google_service_account.creative_studio.member
}

resource "google_storage_bucket_iam_member" "sa_bucket_viewer" {
  bucket = var.assets_bucket_name
  role   = "roles/storage.bucketViewer"
  member = google_service_account.creative_studio.member
}

resource "google_storage_bucket_iam_member" "sa_object_user" {
  bucket = var.assets_bucket_name
  role   = "roles/storage.objectUser"
  member = google_service_account.creative_studio.member
}

resource "google_project_iam_member" "creative_studio_sa_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = google_service_account.creative_studio.member
}

resource "google_project_iam_member" "creative_studio_db_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.creative_studio.member
  condition {
    title      = "Access to Create Studio Asset Metadata DB"
    expression = "resource.name==\"${var.firestore_db_id}\""
  }
}

resource "google_project_iam_member" "creative_studio_vertex_access" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.creative_studio.member
}

/********************************************
*  Build service account
*********************************************/

# NOTE: the build-SA IAM bindings that reference the Cloud Run service or that
# the Cloud Run resource must be ordered after (build_act_as_creative_studio,
# build_logs_writer, build_service) remain in the root. Encapsulating them here
# would force the root Cloud Run resource to depend on the whole iam module,
# creating a module-level dependency cycle with the data-stores/CORS coupler.
# Group C dissolves that coupler and can relocate these alongside cloud-run.

resource "google_service_account" "cloudbuild" {
  account_id = "builds-creative-studio"
}
