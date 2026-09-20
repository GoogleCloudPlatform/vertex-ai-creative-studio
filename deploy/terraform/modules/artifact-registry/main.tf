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

  # FU-3 retention (dry-run first). NOTE: repo-wide immutable_tags is deliberately
  # NOT set — it would forbid re-pointing the moving `:latest` tag on every build.
  # Version-tag immutability (v<UTC-ts>-<shortSHA>) is a CONVENTION (we never
  # re-push a v… tag), not an enforced repo setting.
  #
  # cleanup_policy_dry_run = true means NOTHING is deleted: Artifact Registry only
  # LOGS what these policies WOULD delete. The owner reviews the dry-run output and
  # flips var.cleanup_policy_dry_run to false on a later apply to enable deletion.
  cleanup_policy_dry_run = var.cleanup_policy_dry_run

  # KEEP the N most-recent versions (tagged releases + their digests).
  cleanup_policies {
    id     = "keep-recent-releases"
    action = "KEEP"
    most_recent_versions {
      keep_count = var.cleanup_keep_count
    }
  }

  # DELETE untagged artifacts older than the configured age (garbage from
  # rebuilds/overwrites). Tagged versions (:latest, v…) are unaffected.
  cleanup_policies {
    id     = "gc-old-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = var.cleanup_untagged_older_than
    }
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

# FU-3: grant the DEPLOYER principal(s) read access on the repo so they can run
# `deploy.sh list-versions` (artifacts docker images list) and deploy by
# tag/digest. Today only the BUILD SA holds reader; the deployer principal does
# not. Mirrors FU-1: ADDITIVE google_artifact_registry_repository_iam_member,
# for_each over the SAME var.deployer_members list, default [] ⇒ dormant (no
# binding). Never authoritative (google_artifact_registry_repository_iam_binding),
# so it cannot clobber other readers.
resource "google_artifact_registry_repository_iam_member" "deployer_readers" {
  for_each   = toset(var.deployer_members)
  repository = google_artifact_registry_repository.creative_studio.name
  role       = "roles/artifactregistry.reader"
  member     = each.value
}
