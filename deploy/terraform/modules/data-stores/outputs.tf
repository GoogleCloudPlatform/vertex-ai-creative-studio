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

output "assets_bucket_name" {
  description = "Name of the GCS bucket where assets are stored."
  value       = google_storage_bucket.assets.name
}

output "firestore_db_id" {
  description = "Fully-qualified Firestore database resource ID (used for IAM condition scoping)."
  value       = google_firestore_database.create_studio_asset_metadata.id
}

output "firestore_db_name" {
  description = "Firestore database name (used as the GENMEDIA_FIREBASE_DB env var)."
  value       = google_firestore_database.create_studio_asset_metadata.name
}

output "tasks_queue_name" {
  description = "Cloud Tasks queue name (used as the THUMBNAIL_QUEUE_ID env var)."
  value       = google_cloud_tasks_queue.thumbnail_queue.name
}

output "tasks_queue_id" {
  description = "Fully-qualified Cloud Tasks queue resource ID."
  value       = google_cloud_tasks_queue.thumbnail_queue.id
}
