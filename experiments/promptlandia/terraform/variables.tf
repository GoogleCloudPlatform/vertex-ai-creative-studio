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
  description = "The ID of the primary/strongest Gemini model to use."
  type        = string
  default     = "gemini-3.7-flash"
}

variable "alternative_model_id" {
  description = "A lighter/faster Gemini model used for secondary, classification-style steps."
  type        = string
  default     = "gemini-3.5-flash-lite"
}

variable "gemini_location" {
  description = "The location for Gemini model calls. Decoupled from the Cloud Run deployment region (var.region)."
  type        = string
  default     = "global"
}

variable "iap_members" {
  description = "A list of members to grant IAP-secured Web App User role."
  type        = list(string)
  default     = [] # e.g., ["group:cloud-aaie@google.com"]
}
