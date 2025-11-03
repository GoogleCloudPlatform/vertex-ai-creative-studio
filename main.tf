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

terraform {
  required_providers {
    google = {
      version = "~> 6.49"
    }
    google-beta = {
      version = "~> 6.49"
    }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
  default_labels = {
    app = "genmedia-studio"
  }
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  default_labels = {
    app = "genmedia-studio"
  }
}

data "google_project" "project" {
  project_id = var.project_id
}

module "project-services" {
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "~>18.0"
  project_id                  = var.project_id
  disable_services_on_destroy = false
  activate_apis = [
    "iap.googleapis.com",
    "compute.googleapis.com",
    "certificatemanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "containerscanning.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "firestore.googleapis.com",
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "null_resource" "sleep" {
  depends_on = [module.project-services.project_id]
  provisioner "local-exec" {
    command = "sleep ${var.sleep_time}"
  }
}

/********************************************
*  Network Infra Resources Section
*********************************************/

/* There are times when IAP service account is not automatically provisioned, creating explicitly to be sure */
resource "google_project_service_identity" "iap_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "iap.googleapis.com"
}

resource "google_iap_web_iam_member" "initial_user_iap_access" {
  count      = var.use_lb && var.initial_user != null ? 1 : 0
  role       = "roles/iap.httpsResourceAccessor"
  member     = "user:${var.initial_user}"
  depends_on = [null_resource.sleep]
}

resource "google_cloud_run_service_iam_member" "iap_cloudrun_access" {
  location = google_cloud_run_v2_service.creative_studio.location
  service  = google_cloud_run_v2_service.creative_studio.name
  role     = "roles/run.invoker"
  member   = google_project_service_identity.iap_sa.member
}

module "lb-http" {
  count                           = var.use_lb ? 1 : 0
  source                          = "terraform-google-modules/lb-http/google//modules/serverless_negs"
  version                         = "~>13.0"
  name                            = "creativestudio"
  project                         = var.project_id
  load_balancing_scheme           = "EXTERNAL_MANAGED"
  ssl                             = var.use_lb
  managed_ssl_certificate_domains = [var.domain]
  https_redirect                  = var.use_lb
  backends = {
    default = {
      description = "Creative Studio backend"
      enable_cdn  = false
      groups = [
        {
          group = google_compute_region_network_endpoint_group.cloudrun_neg[0].id
        }
      ]
      iap_config = {
        enable = true
      }
      log_config = {
        enable = true
      }
    }
  }
  depends_on = [null_resource.sleep]
}

resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  count                 = var.use_lb ? 1 : 0
  name                  = "cloudrun-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.creative_studio.name
  }
  depends_on = [null_resource.sleep]
}

/********************************************
*  Runtime Resources Section
*********************************************/

resource "google_service_account" "creative_studio" {
  account_id = "service-creative-studio"
}

# Centralizing environment variables here and using for each in service declaration for simplicity
locals {
  asset_bucket_name = "creative-studio-${var.project_id}-assets"
  creative_studio_env_vars = {
    PROJECT_ID            = var.project_id
    LOCATION              = var.region
    MODEL_ID              = var.model_id
    VEO_MODEL_ID          = var.veo_model_id
    VEO_EXP_MODEL_ID      = var.veo_exp_model_id
    LYRIA_MODEL_VERSION   = var.lyria_model_id
    LYRIA_PROJECT_ID      = var.project_id
    GENMEDIA_BUCKET       = local.asset_bucket_name
    VIDEO_BUCKET          = local.asset_bucket_name
    MEDIA_BUCKET          = local.asset_bucket_name
    IMAGE_BUCKET          = local.asset_bucket_name
    GCS_ASSETS_BUCKET     = local.asset_bucket_name
    GENMEDIA_FIREBASE_DB  = google_firestore_database.create_studio_asset_metadata.name
    SERVICE_ACCOUNT_EMAIL = google_service_account.creative_studio.email
    EDIT_IMAGES_ENABLED   = var.edit_images_enabled
  }

  deployed_domain = var.use_lb ? ["https://${var.domain}"] : google_cloud_run_v2_service.creative_studio.urls
  cors_domains    = concat(local.deployed_domain, var.allow_local_domain_cors_requests ? ["http://localhost:8080", "http://0.0.0.0:8080"] : [])
}

resource "google_cloud_run_v2_service" "creative_studio" {
  provider             = google-beta
  name                 = "creative-studio"
  location             = var.region
  project              = var.project_id
  ingress              = var.use_lb ? "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" : "INGRESS_TRAFFIC_ALL"
  default_uri_disabled = var.use_lb
  deletion_protection  = false
  iap_enabled          = !var.use_lb
  invoker_iam_disabled = !var.use_lb
  launch_stage         = var.use_lb ? "GA" : "BETA"

  template {
    containers {
      name  = "creative-studio"
      image = var.initial_container_image
      resources {
        limits = {
          cpu    = "1000m"
          memory = "1024Mi"
        }
      }
      dynamic "env" {
        for_each = local.creative_studio_env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
    }
    service_account = google_service_account.creative_studio.email
    scaling {
      max_instance_count = 1
    }
  }
  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }
  depends_on = [
    google_service_account_iam_member.build_act_as_creative_studio,
    google_project_iam_member.build_logs_writer,
    null_resource.sleep
  ]
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

resource "google_storage_bucket" "assets" {
  name                        = local.asset_bucket_name
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
    origin          = local.cors_domains
    method          = ["GET"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }
}

resource "google_storage_bucket_iam_member" "admins" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectAdmin"
  member = "user:${var.initial_user}"
}

resource "google_storage_bucket_iam_member" "creators" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectCreator"
  member = google_service_account.creative_studio.member
}

resource "google_storage_bucket_iam_member" "viewers" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.creative_studio.member
}

resource "google_storage_bucket_iam_member" "sa_bucket_viewer" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.bucketViewer"
  member = google_service_account.creative_studio.member
}

resource "google_storage_bucket_iam_member" "sa_object_user" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectUser"
  member = google_service_account.creative_studio.member
}

resource "google_project_iam_member" "creative_studio_sa_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = google_service_account.creative_studio.member
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
  depends_on      = [null_resource.sleep]
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

resource "google_project_iam_member" "creative_studio_db_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.creative_studio.member
  condition {
    title      = "Access to Create Studio Asset Metadata DB"
    expression = "resource.name==\"${google_firestore_database.create_studio_asset_metadata.id}\""
  }
}

resource "google_project_iam_member" "creative_studio_vertex_access" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.creative_studio.member
}

/********************************************
*  Build time Resources Section
*********************************************/

resource "google_service_account" "cloudbuild" {
  account_id = "builds-creative-studio"
}

resource "google_service_account_iam_member" "build_act_as_creative_studio" {
  service_account_id = google_service_account.creative_studio.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.cloudbuild.member
}

resource "google_project_iam_member" "build_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.cloudbuild.member
}

module "source_bucket" {
  source     = "terraform-google-modules/cloud-storage/google"
  version    = "~>11.0"
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
  creators                 = [google_service_account.cloudbuild.member]
  set_viewer_roles         = true
  bucket_viewers           = {}
  viewers                  = [google_service_account.cloudbuild.member]
  public_access_prevention = "enforced"
  depends_on               = [null_resource.sleep]
}

resource "google_artifact_registry_repository" "creative_studio" {
  repository_id = "creative-studio"
  description   = "Docker repository for GenMedia Creative Studio related images"
  format        = "DOCKER"
  vulnerability_scanning_config {
    enablement_config = "INHERITED"
  }
  depends_on = [null_resource.sleep]
}

resource "google_artifact_registry_repository_iam_member" "readers" {
  repository = google_artifact_registry_repository.creative_studio.name
  role       = "roles/artifactregistry.reader"
  member     = google_service_account.cloudbuild.member
}

resource "google_artifact_registry_repository_iam_member" "writers" {
  repository = google_artifact_registry_repository.creative_studio.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.cloudbuild.member
}

resource "google_cloud_run_service_iam_member" "build_service" {
  location = google_cloud_run_v2_service.creative_studio.location
  service  = google_cloud_run_v2_service.creative_studio.name
  role     = "roles/run.developer"
  member   = google_service_account.cloudbuild.member
}
