variable "project_id" {
  description = "The Google Cloud project ID to deploy to."
  type        = string
}

variable "region" {
  description = "The Google Cloud region to deploy to."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "The name of the Cloud Run service."
  type        = string
  default     = "promptlandia"
}

variable "model_id" {
  description = "The ID of the Gemini model to use."
  type        = string
  default     = "gemini-3.1-pro-preview"
}

variable "iap_members" {
  description = "A list of members to grant IAP-secured Web App User role."
  type        = list(string)
  default     = [] # e.g., ["group:cloud-aaie@google.com"]
}
