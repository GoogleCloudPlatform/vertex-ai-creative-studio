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

# data-stores module: platform-agnostic persistence layer — assets GCS bucket,
# Firestore Native DB + composite indexes (AS-IS; index changes are Phase 2),
# and the Cloud Tasks queue. All attribute values preserved exactly.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.49"
    }
  }
}

resource "google_cloud_tasks_queue" "thumbnail_queue" {
  name     = "thumbnail-extraction"
  location = var.region
  project  = var.project_id
}

resource "google_storage_bucket" "assets" {
  name                        = var.bucket_name
  project                     = var.project_id
  location                    = var.region
  force_destroy               = var.enable_data_deletion
  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true
  default_event_based_hold    = false
  autoclass {
    enabled = false
  }
  cors {
    origin          = var.cors_domains
    method          = ["GET"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }
  dynamic "lifecycle_rule" {
    for_each = var.asset_lifecycle_age_days > 0 ? [1] : []
    content {
      condition {
        age = var.asset_lifecycle_age_days
      }
      action {
        type = "Delete"
      }
    }
  }
}

resource "google_firestore_database" "create_studio_asset_metadata" {
  name                              = "create-studio-asset-metadata"
  location_id                       = var.region
  type                              = "FIRESTORE_NATIVE"
  concurrency_mode                  = "OPTIMISTIC"
  app_engine_integration_mode       = "DISABLED"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"
  delete_protection_state           = var.enable_data_deletion ? "DELETE_PROTECTION_DISABLED" : "DELETE_PROTECTION_ENABLED"
  # Terraform docs / testing showed that deletion_policy is needed for db to be delete when using terraform destroy
  # See https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/firestore_database#delete_protection_state-1
  deletion_policy = var.enable_data_deletion ? "DELETE" : "ABANDON"
}

resource "google_firestore_index" "genmedia_library_mime_type_timestamp" {
  collection  = "genmedia"
  database    = google_firestore_database.create_studio_asset_metadata.name
  query_scope = "COLLECTION"

  fields {
    field_path = "mime_type"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "genmedia_chooser_media_type_timestamp" {
  collection  = "genmedia"
  database    = google_firestore_database.create_studio_asset_metadata.name
  query_scope = "COLLECTION"

  fields {
    field_path = "media_type"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "genmedia_user_email_timestamp" {
  collection  = "genmedia"
  database    = google_firestore_database.create_studio_asset_metadata.name
  query_scope = "COLLECTION"

  fields {
    field_path = "user_email"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "genmedia_user_email_mime_type_timestamp" {
  collection  = "genmedia"
  database    = google_firestore_database.create_studio_asset_metadata.name
  query_scope = "COLLECTION"

  fields {
    field_path = "user_email"
    order      = "ASCENDING"
  }

  fields {
    field_path = "mime_type"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
}
