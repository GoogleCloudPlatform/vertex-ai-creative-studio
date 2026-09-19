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

# secret-manager module: creates one Secret Manager *secret container* per
# migrated variable (via for_each over var.secret_ids) and, optionally, a
# per-secret secretAccessor IAM binding for the runtime service account.
#
# DORMANT by default: secret_ids defaults to [] in the root, so with defaults
# this module creates ZERO secrets and ZERO bindings. It NEVER creates secret
# *versions* or authors secret *values* — Terraform owns the container, an
# operator loads the payload out-of-band (gcloud/console) after apply. Secret
# values are never committed to Terraform or code.

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

# One secret *container* per migrated variable. No secret version / value is
# created here — the value is loaded out-of-band once the container exists.
resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(var.secret_ids)
  project   = var.project_id
  secret_id = each.value

  replication {
    auto {}
  }
}

# Optional per-secret accessor binding for the runtime SA, scoped to each
# individual secret (least privilege). Rendered only when there is at least one
# secret AND an accessor SA email was supplied; otherwise no binding is created.
resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each  = var.accessor_sa_email == "" ? toset([]) : toset(var.secret_ids)
  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.value].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.accessor_sa_email}"
}
