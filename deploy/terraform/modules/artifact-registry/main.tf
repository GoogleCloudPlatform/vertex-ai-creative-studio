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

# artifact-registry module: the Docker Artifact Registry repository, the Cloud
# Build staging (source) bucket, and the build-SA IAM (reader/writer on the
# repo). Behavior-preserving; all attribute values preserved exactly.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.49"
    }
  }
}

module "source_bucket" {
  source     = "terraform-google-modules/cloud-storage/google"
  version    = "~> 12.0"
  project_id = var.project_id
  names      = ["run-resources-${var.project_id}-${var.region}"]
  location   = var.region
  force_destroy = {
    "run-resources-${var.project_id}-${var.region}" = var.enable_data_deletion
  }
  set_admin_roles          = true
  bucket_admins            = {}
  admins                   = ["user:${var.initial_user}"]
  set_creator_roles        = true
  bucket_creators          = {}
  creators                 = [var.build_sa_member]
  set_viewer_roles         = true
  bucket_viewers           = {}
  viewers                  = [var.build_sa_member]
  public_access_prevention = "enforced"
}

resource "google_artifact_registry_repository" "creative_studio" {
  repository_id = "creative-studio"
  description   = "Docker repository for GenMedia Creative Studio related images"
  format        = "DOCKER"
  vulnerability_scanning_config {
    enablement_config = "INHERITED"
  }
}

resource "google_artifact_registry_repository_iam_member" "readers" {
  repository = google_artifact_registry_repository.creative_studio.name
  role       = "roles/artifactregistry.reader"
  member     = var.build_sa_member
}

resource "google_artifact_registry_repository_iam_member" "writers" {
  repository = google_artifact_registry_repository.creative_studio.name
  role       = "roles/artifactregistry.writer"
  member     = var.build_sa_member
}
