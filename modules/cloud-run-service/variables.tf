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

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Location for the Cloud Run service."
  type        = string
}

variable "image" {
  description = "Container image for the Creative Studio Cloud Run service."
  type        = string
}

variable "env_vars" {
  description = "Explicit environment variable map rendered into the Cloud Run container. Assembled in the root from data-stores + iam outputs (replaces the old global locals coupler)."
  type        = map(string)
}

variable "runtime_sa_email" {
  description = "Email of the runtime (application) service account the Cloud Run service runs as."
  type        = string
}

variable "runtime_sa_name" {
  description = "Fully-qualified resource name of the runtime service account (projects/.../serviceAccounts/...), used by the build service-account act-as binding."
  type        = string
}

variable "build_sa_member" {
  description = "IAM member string for the Cloud Build service account (serviceAccount:...)."
  type        = string
}

variable "cpu" {
  description = "CPU limit for the Cloud Run service container."
  type        = string
}

variable "memory" {
  description = "Memory limit for the Cloud Run service container."
  type        = string
}

variable "timeout" {
  description = "Maximum request timeout for the Cloud Run service."
  type        = string
}

variable "concurrency" {
  description = "Maximum number of concurrent requests handled by a single Cloud Run instance."
  type        = number
}

variable "max_instance_count" {
  description = "Maximum number of Cloud Run instances (scaling.max_instance_count)."
  type        = number
}

# --- use_lb decomposition: explicit ingress + auth fields ---
# These replace the root's `use_lb`-derived ternaries so this module carries no
# knowledge of the load-balancer topology. The root computes each value and
# passes it in explicitly, preserving the exact previous behaviour.

variable "ingress_mode" {
  description = "Cloud Run ingress setting (e.g. INGRESS_TRAFFIC_ALL or INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER)."
  type        = string
}

variable "default_uri_disabled" {
  description = "Whether the default run.app URI is disabled."
  type        = bool
}

variable "iap_enabled" {
  description = "Whether IAP is enabled directly on the Cloud Run service."
  type        = bool
}

variable "invoker_iam_disabled" {
  description = "Whether invoker IAM checks are disabled on the Cloud Run service."
  type        = bool
}

variable "launch_stage" {
  description = "Cloud Run launch stage (e.g. GA or BETA)."
  type        = string
}

# --- Cloud Run health probes (Phase 3a) ---
# Wired to the application's real, auth-exempt health endpoints:
#   /readyz  (main.py:148-150) — used by the startup probe, which gates traffic
#            until the container reports ready (Cloud Run v2 has no separate
#            readiness probe; the startup probe fills that role).
#   /healthz (main.py:143-145) — used by the liveness probe.
# Both are exempt from auth via PUBLIC_PATH_PREFIXES (main.py:130) and return
# {"status":"ok"}. The probe port defaults to 8080, the container's serving port
# (PORT env default, main.py:399; no explicit ports block => Cloud Run default).
# Each probe is configurable via these object inputs; set a probe to null to
# disable it entirely (e.g. for a placeholder image that does not yet serve the
# endpoints). Defaults are conservative so a slow cold start is not killed.

variable "startup_probe" {
  description = "Cloud Run startup probe config. Gates traffic until the container is ready; targets the app's /readyz endpoint by default. Set to null to disable."
  type = object({
    path                  = optional(string, "/readyz")
    port                  = optional(number, 8080)
    initial_delay_seconds = optional(number, 0)
    period_seconds        = optional(number, 10)
    timeout_seconds       = optional(number, 3)
    failure_threshold     = optional(number, 20)
  })
  default  = {}
  nullable = true
}

variable "liveness_probe" {
  description = "Cloud Run liveness probe config. Restarts the container if it stops responding; targets the app's /healthz endpoint by default. Set to null to disable."
  type = object({
    path                  = optional(string, "/healthz")
    port                  = optional(number, 8080)
    initial_delay_seconds = optional(number, 0)
    period_seconds        = optional(number, 30)
    timeout_seconds       = optional(number, 5)
    failure_threshold     = optional(number, 3)
  })
  default  = {}
  nullable = true
}

# --- Phase 1 no-op input (present but null; wired in a later phase) ---
# Kept in the interface so the compute contract is stable across the Cloud Run
# and future GKE paths. Not referenced yet: declaring it is behaviour-neutral.

variable "secret_env" {
  description = "Optional map of environment variables sourced from Secret Manager. Phase 1 no-op (null)."
  type        = any
  default     = null
}
