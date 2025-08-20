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

provider "google" {
  project = var.project_id
  region = var.region
  default_labels = {
    app="genmedia-studio"
  }
}

provider "google-beta" {
  project = var.project_id
  region = var.region
  default_labels = {
    app="genmedia-studio"
  }
}

module "project-services" {
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  project_id                  = var.project_id
  disable_services_on_destroy = false
  activate_apis = [
    "iap.googleapis.com",
    "compute.googleapis.com",
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

data "google_client_openid_userinfo" "current_user" {
}

resource "google_service_account" "creative_studio" {
  account_id = "service-creative-studio"
}

resource "google_service_account" "cloudbuild" {
  account_id = "builds-creative-studio"
}

resource "google_project_iam_member" "build_act_as" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = google_service_account.cloudbuild.member
}

resource "google_project_iam_member" "build_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.cloudbuild.member
}

resource "google_iap_web_iam_member" "current_user_iap_access" {
  role = "roles/iap.httpsResourceAccessor"
  member = "user:${data.google_client_openid_userinfo.current_user.email}"
}

module "source_bucket" {
  source                   = "terraform-google-modules/cloud-storage/google"
  project_id               = var.project_id
  names                    = [ "run-resources-${var.project_id}-${var.region}" ]
  location                 = var.region
  force_destroy             = {
    "run-resources-${var.project_id}-${var.region}" = true
  }
  set_admin_roles          = true
  bucket_admins            = {}
  admins                   = [ "user:${data.google_client_openid_userinfo.current_user.email}" ]
  set_creator_roles        = true
  bucket_creators          = {}
  creators                 = [ google_service_account.cloudbuild.member ]
  set_viewer_roles         = true
  bucket_viewers           = {}
  viewers                  = [ google_service_account.cloudbuild.member ]
  public_access_prevention = "enforced"
  depends_on = [ module.project-services ]
}

resource "google_artifact_registry_repository" "creative_studio" {
  repository_id = "creative-studio"
  description   = "Docker repository for GenMedia Creative Studio related images"
  format        = "DOCKER"
  vulnerability_scanning_config {
    enablement_config = "INHERITED"
  }
  depends_on = [ module.project-services ]
}

resource "google_artifact_registry_repository_iam_member" "readers" {
  repository = google_artifact_registry_repository.creative_studio.name
  role   = "roles/artifactregistry.reader"
  member = google_service_account.cloudbuild.member
}

resource "google_artifact_registry_repository_iam_member" "writers" {
  repository = google_artifact_registry_repository.creative_studio.name
  role   = "roles/artifactregistry.writer"
  member = google_service_account.cloudbuild.member
}

resource "google_cloud_run_v2_service" "creative_studio" {
  provider              = google-beta
  name                  = "creative-studio"
  location              = var.region
  project               = var.project_id
  ingress               = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  default_uri_disabled  = true
  deletion_protection   = false

  template {
    containers {
        name = "creative-studio"
        image = var.initial_container_image
        resources {
          limits = {
            cpu = "1000m"
            memory = "1024Mi"
          }
        }
        env {
            name = "PROJECT_ID"
            value = var.project_id
        }
        env {
            name = "LOCATION"
            value = var.region
        }
        env {
            name = "MODEL_ID"
            value = var.model_id
        }
        env {
            name = "VEO_MODEL_ID"
            value = var.veo_model_id
        }
        env {
            name = "VEO_EXP_MODEL_ID"
            value = var.veo_exp_model_id
        }
        env {
            name = "LYRIA_MODEL_VERSION"
            value = var.lyria_model_id
        }
        env {
            name = "LYRIA_PROJECT_ID"
            value = var.project_id
        }
        env {
            name = "GENMEDIA_BUCKET"
            value = module.creative_studio_asset_bucket.bucket.name
        }
        env {
            name = "VIDEO_BUCKET"
            value = module.creative_studio_asset_bucket.bucket.name
        }
        env {
            name = "MEDIA_BUCKET"
            value = module.creative_studio_asset_bucket.bucket.name
        }
        env {
            name = "IMAGE_BUCKET"
            value = module.creative_studio_asset_bucket.bucket.name
        }
        env {
            name = "GCS_ASSETS_BUCKET"
            value = module.creative_studio_asset_bucket.bucket.name
        }
        env {
          name = "GENMEDIA_FIREBASE_DB"
          value = google_firestore_database.create_studio_asset_metadata.name
        }
        env {
            name = "EDIT_IMAGES_ENABLED"
            value = var.edit_images_enabled
        }
    }
    service_account = google_service_account.creative_studio.email
    scaling {
      max_instance_count = 1
    }
  }
  depends_on = [
    google_project_iam_member.build_act_as,
    google_project_iam_member.build_logs_writer,
    module.project-services
  ]
}

/* There are times when IAP service account is not automatically provisioned, creating explicitly to be sure */
resource "google_project_service_identity" "iap_sa" {
  provider = google-beta
  project = var.project_id
  service = "iap.googleapis.com"
}

resource "google_cloud_run_service_iam_member" "iap_cloudrun_access" {
  location = google_cloud_run_v2_service.creative_studio.location
  service  = google_cloud_run_v2_service.creative_studio.name
  role = "roles/run.invoker"
  member = google_project_service_identity.iap_sa.member
}

/* There are times when IAP service account is not automatically provisioned, creating explicitly to be sure */
resource "google_project_service_identity" "vertex_sa" {
  provider = google-beta
  project = var.project_id
  service = "aiplatform.googleapis.com"
}

resource "google_project_iam_member" "vertex_sa_access" {
  project = var.project_id
  role    = "roles/aiplatform.serviceAgent"
  member = google_project_service_identity.vertex_sa.member
}

resource "google_cloud_run_service_iam_member" "build_service" {
  location = google_cloud_run_v2_service.creative_studio.location
  service  = google_cloud_run_v2_service.creative_studio.name
  role = "roles/run.developer"
  member = google_service_account.cloudbuild.member
}

module "creative_studio_asset_bucket" {
  source                    = "terraform-google-modules/cloud-storage/google"
  project_id                = var.project_id
  names                     = [ "creative-studio-${var.project_id}-assets" ]
  location                  = var.region
  force_destroy             = {
    "creative-studio-${var.project_id}-assets" = true
  }
  set_admin_roles           = true
  bucket_admins             = {}
  admins                    = [ "user:${data.google_client_openid_userinfo.current_user.email}" ]
  set_creator_roles         = true
  bucket_creators           = {}
  creators                  = [ google_service_account.creative_studio.member ]
  set_viewer_roles          = true
  bucket_viewers            = {}
  viewers                   = [ google_service_account.creative_studio.member ]
  public_access_prevention  = "enforced"
  depends_on = [ module.project-services ]
}

resource "google_storage_bucket_iam_member" "sa_object_viewer" {
  bucket = module.creative_studio_asset_bucket.bucket.name
  role = "roles/storage.objectViewer"
  member = google_service_account.creative_studio.member
}

resource "google_storage_bucket_iam_member" "sa_bucket_viewer" {
  bucket = module.creative_studio_asset_bucket.bucket.name
  role = "roles/storage.bucketViewer"
  member = google_service_account.creative_studio.member
}

resource "google_firestore_database" "create_studio_asset_metadata" {
  name                              = "create-studio-asset-metadata"
  location_id                       = var.region
  type                              = "FIRESTORE_NATIVE"
  concurrency_mode                  = "OPTIMISTIC"
  app_engine_integration_mode       = "DISABLED"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"
  delete_protection_state           = "DELETE_PROTECTION_DISABLED"
  deletion_policy                   = "DELETE"
  depends_on = [ module.project-services ]
}

resource "google_project_iam_member" "creative_studio_db_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.creative_studio.member
  condition {
    title = "Access to Create Studio Asset Metadata DB"
    expression = "resource.name==\"${google_firestore_database.create_studio_asset_metadata.id}\""
  }
}

resource "google_project_iam_member" "creative_studio_vertex_access" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.creative_studio.member
}

module "lb-http" {
  source                          = "terraform-google-modules/lb-http/google//modules/serverless_negs"
  name                            = "creativestudio"
  project                         = var.project_id
  ssl                             = var.ssl
  managed_ssl_certificate_domains = [var.domain]
  https_redirect                  = var.ssl
  backends = {
    default = {
      description = "Creative Studio backend"
      enable_cdn = false
      groups = [
        {
          group = google_compute_region_network_endpoint_group.cloudrun_neg.id
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
  depends_on = [ module.project-services ]
}

resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "cloudrun-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.creative_studio.name
  }
  depends_on = [ module.project-services ]
}
