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

# moved{} blocks: preserve state by telling Terraform these are address moves
# (module encapsulation), NOT destroy/create. Behavior-preserving refactor.

# --- project-services module ---
moved {
  from = module.project-services
  to   = module.apis.module.project_services
}

moved {
  from = null_resource.sleep
  to   = module.apis.null_resource.sleep
}

# --- data-stores module ---
moved {
  from = google_cloud_tasks_queue.thumbnail_queue
  to   = module.data.google_cloud_tasks_queue.thumbnail_queue
}

moved {
  from = google_storage_bucket.assets
  to   = module.data.google_storage_bucket.assets
}

moved {
  from = google_firestore_database.create_studio_asset_metadata
  to   = module.data.google_firestore_database.create_studio_asset_metadata
}

moved {
  from = google_firestore_index.genmedia_library_mime_type_timestamp
  to   = module.data.google_firestore_index.genmedia_library_mime_type_timestamp
}

moved {
  from = google_firestore_index.genmedia_chooser_media_type_timestamp
  to   = module.data.google_firestore_index.genmedia_chooser_media_type_timestamp
}

moved {
  from = google_firestore_index.genmedia_user_email_timestamp
  to   = module.data.google_firestore_index.genmedia_user_email_timestamp
}

moved {
  from = google_firestore_index.genmedia_user_email_mime_type_timestamp
  to   = module.data.google_firestore_index.genmedia_user_email_mime_type_timestamp
}

# --- artifact-registry module ---
moved {
  from = module.source_bucket
  to   = module.registry.module.source_bucket
}

moved {
  from = google_artifact_registry_repository.creative_studio
  to   = module.registry.google_artifact_registry_repository.creative_studio
}

moved {
  from = google_artifact_registry_repository_iam_member.readers
  to   = module.registry.google_artifact_registry_repository_iam_member.readers
}

moved {
  from = google_artifact_registry_repository_iam_member.writers
  to   = module.registry.google_artifact_registry_repository_iam_member.writers
}

# --- iam module ---
moved {
  from = google_service_account.creative_studio
  to   = module.iam.google_service_account.creative_studio
}

moved {
  from = google_service_account.cloudbuild
  to   = module.iam.google_service_account.cloudbuild
}

moved {
  from = google_project_iam_member.creative_studio_tasks_enqueuer
  to   = module.iam.google_project_iam_member.creative_studio_tasks_enqueuer
}

moved {
  from = google_project_service_identity.vertex_sa
  to   = module.iam.google_project_service_identity.vertex_sa
}

moved {
  from = google_project_iam_member.vertex_sa_access
  to   = module.iam.google_project_iam_member.vertex_sa_access
}

moved {
  from = google_storage_bucket_iam_member.admins
  to   = module.iam.google_storage_bucket_iam_member.admins
}

moved {
  from = google_storage_bucket_iam_member.creators
  to   = module.iam.google_storage_bucket_iam_member.creators
}

moved {
  from = google_storage_bucket_iam_member.viewers
  to   = module.iam.google_storage_bucket_iam_member.viewers
}

moved {
  from = google_storage_bucket_iam_member.sa_bucket_viewer
  to   = module.iam.google_storage_bucket_iam_member.sa_bucket_viewer
}

moved {
  from = google_storage_bucket_iam_member.sa_object_user
  to   = module.iam.google_storage_bucket_iam_member.sa_object_user
}

moved {
  from = google_project_iam_member.creative_studio_sa_token_creator
  to   = module.iam.google_project_iam_member.creative_studio_sa_token_creator
}

moved {
  from = google_project_iam_member.creative_studio_db_access
  to   = module.iam.google_project_iam_member.creative_studio_db_access
}

moved {
  from = google_project_iam_member.creative_studio_vertex_access
  to   = module.iam.google_project_iam_member.creative_studio_vertex_access
}

# --- networking-lb module (root count-gated by var.use_lb) ---
moved {
  from = google_compute_global_address.lb_ipv4[0]
  to   = module.networking-lb[0].google_compute_global_address.lb_ipv4[0]
}

moved {
  from = module.lb-http[0]
  to   = module.networking-lb[0].module.lb-http
}

moved {
  from = google_compute_region_network_endpoint_group.cloudrun_neg[0]
  to   = module.networking-lb[0].google_compute_region_network_endpoint_group.cloudrun_neg
}

# initial_user_iap_access relocated from root into networking-lb (Group C). The
# root gate was `use_lb && initial_user != null`; the module is itself count-gated
# by use_lb, so the surviving instance address only exists when use_lb is true.
moved {
  from = google_iap_web_iam_member.initial_user_iap_access[0]
  to   = module.networking-lb[0].google_iap_web_iam_member.initial_user_iap_access[0]
}

# --- cloud-run-service module (Group C) ---
moved {
  from = google_cloud_run_v2_service.creative_studio
  to   = module.cloud-run-service.google_cloud_run_v2_service.creative_studio
}

moved {
  from = google_project_service_identity.iap_sa
  to   = module.cloud-run-service.google_project_service_identity.iap_sa
}

moved {
  from = google_cloud_run_service_iam_member.iap_cloudrun_access
  to   = module.cloud-run-service.google_cloud_run_service_iam_member.iap_cloudrun_access
}

moved {
  from = google_service_account_iam_member.build_act_as_creative_studio
  to   = module.cloud-run-service.google_service_account_iam_member.build_act_as_creative_studio
}

moved {
  from = google_project_iam_member.build_logs_writer
  to   = module.cloud-run-service.google_project_iam_member.build_logs_writer
}

moved {
  from = google_cloud_run_service_iam_member.build_service
  to   = module.cloud-run-service.google_cloud_run_service_iam_member.build_service
}
