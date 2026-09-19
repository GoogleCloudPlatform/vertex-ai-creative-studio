/**
* Copyright 2025 Google LLC
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
  description = "GCP project ID (used for the Workload Identity member string and IAP IAM bindings)."
  type        = string
}

variable "name" {
  description = "Base name for the workload's Kubernetes objects (Deployment, Service, Ingress, etc.)."
  type        = string
  default     = "creative-studio"
}

variable "namespace" {
  description = "Kubernetes namespace the workload runs in. Assumed to already exist (the module does not create it)."
  type        = string
  default     = "default"
}

variable "image" {
  description = "Container image to run (same image contract as the Cloud Run path). Passed in by the root; the Deployment ignores in-place changes to this field to preserve the out-of-band image/deploy contract."
  type        = string
}

# --- Runtime identity / Workload Identity ---

variable "ksa_name" {
  description = "Name of the Kubernetes ServiceAccount the pods run as. Annotated to the existing runtime Google service account for Workload Identity."
  type        = string
  default     = "creative-studio"
}

variable "runtime_sa_email" {
  description = "Email of the EXISTING runtime Google service account (from the shared iam module). The KSA is annotated to this SA; the module does NOT create it."
  type        = string
}

variable "runtime_sa_id" {
  description = "Fully-qualified resource name of the existing runtime Google service account (projects/<p>/serviceAccounts/<email>). Used for the roles/iam.workloadIdentityUser binding."
  type        = string
}

# --- Resources (parity with Cloud Run: requests == limits) ---

variable "cpu" {
  description = "CPU for the container. Set as BOTH requests and limits (parity with the Cloud Run limits)."
  type        = string
  default     = "2000m"
}

variable "memory" {
  description = "Memory for the container. Set as BOTH requests and limits (parity with the Cloud Run limits)."
  type        = string
  default     = "4Gi"
}

variable "container_port" {
  description = "Port the container serves on (the app serves on 8080)."
  type        = number
  default     = 8080
}

# --- Config & secrets (parity with Cloud Run Phase 4, dormant by default) ---

variable "env_vars" {
  description = "Plaintext environment variables rendered into a ConfigMap and injected via envFrom (1:1 with the Cloud Run plaintext env map, assembled in the root)."
  type        = map(string)
  default     = {}
}

variable "secret_env" {
  description = "Map of ENV_VAR_NAME => value for secret-backed environment variables. DORMANT by default ({} => no Secret and no secret env is rendered). When non-empty, values are supplied out-of-band by the root from Secret Manager (NEVER authored in committed Terraform); they are stored in a Kubernetes Secret and injected via valueFrom.secretKeyRef."
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "secret_name" {
  description = "Name of the Kubernetes Secret created to hold secret_env values (only created when secret_env is non-empty)."
  type        = string
  default     = "creative-studio-secrets"
}

# --- Autoscaling ---

variable "replicas_min" {
  description = "Minimum replica count for the HPA (no scale-to-zero on GKE; documented difference from Cloud Run)."
  type        = number
  default     = 1
}

variable "replicas_max" {
  description = "Maximum replica count for the HPA (kept small for the minimal/testing profile)."
  type        = number
  default     = 3
}

variable "cpu_target_utilization" {
  description = "Target average CPU utilization percentage that drives HPA scaling."
  type        = number
  default     = 60
}

# --- Ingress / TLS / IAP ---

variable "domain" {
  description = "Domain that fronts the external HTTPS ingress (used for the managed certificate). Placeholder in tfvars until provided."
  type        = string
}

variable "static_ip_name" {
  description = "Name of the reserved global static IP for the ingress. When create_static_ip is true this module reserves it under this name; otherwise it must already exist."
  type        = string
  default     = "creative-studio-gke-ip"
}

variable "create_static_ip" {
  description = "When true, reserve the global static IP (google_compute_global_address) under static_ip_name. Set false to reference a pre-existing address."
  type        = bool
  default     = true
}

variable "enable_iap" {
  description = "When true, enable IAP on the ingress backend service via BackendConfig.spec.iap (auth parity with the Cloud Run IAP path)."
  type        = bool
  default     = true
}

variable "iap_oauth_secret_name" {
  description = "Name of the Kubernetes Secret holding the IAP OAuth client credentials (keys client_id / client_secret), referenced by BackendConfig.spec.iap.oauthclientCredentials.secretName."
  type        = string
  default     = "creative-studio-iap-oauth"
}

variable "create_iap_oauth_secret" {
  description = "When true, create the IAP OAuth Kubernetes Secret from iap_oauth_client_id / iap_oauth_client_secret. Set false (default) when the secret is provisioned out-of-band. NEVER commit real client credentials."
  type        = bool
  default     = false
}

variable "iap_oauth_client_id" {
  description = "IAP OAuth 2.0 client ID. Supplied out-of-band; NEVER committed. Only used when create_iap_oauth_secret is true."
  type        = string
  default     = ""
  sensitive   = true
}

variable "iap_oauth_client_secret" {
  description = "IAP OAuth 2.0 client secret. Supplied out-of-band; NEVER committed. Only used when create_iap_oauth_secret is true."
  type        = string
  default     = ""
  sensitive   = true
}

variable "iap_backend_service_name" {
  description = "Name of the GCLB backend service GKE creates for the ingress, used for the roles/iap.httpsResourceAccessor binding. GKE derives this from the Service/BackendConfig; supply the resolved name (or leave null to skip the IAM binding until known)."
  type        = string
  default     = null
}

variable "initial_user" {
  description = "Email of the initial user granted roles/iap.httpsResourceAccessor on the ingress backend service (analogue of the Cloud Run IAP web IAM member). Null skips the binding."
  type        = string
  default     = null
}
