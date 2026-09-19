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
# Firestore Native DB + composite indexes, and the Cloud Tasks queue.
#
# The composite indexes are rendered from the `firestore_indexes` locals list
# (Phase 2) so the single authoritative definition lives in Terraform. The set is
# behavior-identical to the previous explicit resources; addresses moved from
# individually-named resources to for_each keys are preserved via moved.tf.

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

# Composite indexes for the `genmedia` collection. Each entry maps a query shape
# used by the app (see common/metadata.py) to its covering index. Keys match the
# previous resource names so state addresses migrate cleanly via moved.tf.
locals {
  firestore_indexes = {
    # get_media_for_chooser query2 (legacy mime_type) + optimized mime range
    genmedia_library_mime_type_timestamp = {
      fields = [
        { field_path = "mime_type", order = "ASCENDING" },
        { field_path = "timestamp", order = "DESCENDING" },
      ]
    }
    # get_media_for_chooser query1: where("media_type" ==) + order_by timestamp
    genmedia_chooser_media_type_timestamp = {
      fields = [
        { field_path = "media_type", order = "ASCENDING" },
        { field_path = "timestamp", order = "DESCENDING" },
      ]
    }
    # get_media_for_page_optimized: where("user_email" ==) + order_by timestamp
    genmedia_user_email_timestamp = {
      fields = [
        { field_path = "user_email", order = "ASCENDING" },
        { field_path = "timestamp", order = "DESCENDING" },
      ]
    }
    # get_media_for_page_optimized: user_email + mime_type range + order_by timestamp
    genmedia_user_email_mime_type_timestamp = {
      fields = [
        { field_path = "user_email", order = "ASCENDING" },
        { field_path = "mime_type", order = "ASCENDING" },
        { field_path = "timestamp", order = "DESCENDING" },
      ]
    }
  }
}

resource "google_firestore_index" "genmedia" {
  for_each = local.firestore_indexes

  collection  = "genmedia"
  database    = google_firestore_database.create_studio_asset_metadata.name
  query_scope = "COLLECTION"

  dynamic "fields" {
    for_each = each.value.fields
    content {
      field_path = fields.value.field_path
      order      = fields.value.order
    }
  }
}
