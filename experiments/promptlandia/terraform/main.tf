terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "promptlandia_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for Promptlandia"
  description  = "Used by the Promptlandia Cloud Run service"
}

resource "google_project_iam_member" "vertex_user_binding" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.promptlandia_sa.member
}

resource "google_project_iam_member" "run_invoker_binding" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = google_service_account.promptlandia_sa.member
}

resource "google_cloud_run_v2_service" "promptlandia_service" {
  name     = var.service_name
  location = var.region

  template {
    service_account = google_service_account.promptlandia_sa.email

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello" # This will be replaced by the source build
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "MODEL_ID"
        value = var.model_id
      }
      env {
        name  = "LOCATION"
        value = var.region
      }
    }
  }
}

resource "google_iap_web_iam_member" "iap_access" {
  project = google_cloud_run_v2_service.promptlandia_service.project
  role    = "roles/iap.httpsResourceAccessor"
  for_each = toset(var.iap_members)
  member   = each.value
}
