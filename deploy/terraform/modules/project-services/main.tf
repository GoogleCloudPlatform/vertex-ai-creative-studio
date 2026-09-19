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

# project-services module: enables the required GCP APIs and provides a single
# eventual-consistency wait handle (`apis_ready`) that downstream modules
# depend_on, replacing the previously scattered `null_resource.sleep` deps.

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

# The Secret Manager API is added to the activated set only when Secret Manager
# is actually adopted (secret_ids non-empty upstream => enable_secret_manager_api
# true). This keeps the P4 mechanism dormant: with defaults the API set is
# unchanged, so a default apply enables no new API.
locals {
  activate_apis = var.enable_secret_manager_api ? concat(var.activate_apis, ["secretmanager.googleapis.com"]) : var.activate_apis
}

module "project_services" {
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "~>18.0"
  project_id                  = var.project_id
  disable_services_on_destroy = false
  activate_apis               = local.activate_apis
}

resource "null_resource" "sleep" {
  depends_on = [module.project_services.project_id]
  provisioner "local-exec" {
    command = "sleep ${var.sleep_time}"
  }
}
