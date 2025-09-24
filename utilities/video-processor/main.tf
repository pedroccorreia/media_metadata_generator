# This Terraform file now assumes GCS buckets are managed elsewhere.
# It focuses only on deploying the Cloud Run service and its specific permissions.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.40.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Variables ---
variable "project_id" {
  description = "The GCP project ID where resources will be deployed."
  type        = string
}

variable "region" {
  description = "The GCP region for resources (e.g., 'us-central1')."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "The base name for the Cloud Run service."
  type        = string
  default     = "video-processor-service"
}

variable "service_account_name" {
  description = "The name for the dedicated service account."
  type        = string
  default     = "video-processor-sa"
}

variable "invoker_principal" {
  description = "The principal allowed to invoke this service (e.g., 'user:you@example.com')."
  type        = string
}

# --- Resource Creation ---

# 1. Enable necessary APIs.
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# 2. Create the dedicated service account for the Cloud Run service.
resource "google_service_account" "processor_sa" {
  project      = var.project_id
  account_id   = var.service_account_name
  display_name = "Video Processor Service Account"
}

# 3. Assign the necessary IAM roles to the service account.
resource "google_project_iam_member" "processor_sa_roles" {
  for_each = toset([
    "roles/datastore.user", # For Firestore access
    "roles/storage.admin",  # For GCS bucket read/write access
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.processor_sa.email}"
}

# 4. Create the Artifact Registry repository for the Docker image.
resource "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "${var.service_name}-repo"
  format        = "DOCKER"
}

# 5. Define and deploy the Cloud Run service.
resource "google_cloud_run_v2_service" "video_processor" {
  project  = var.project_id
  name     = var.service_name
  location = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.processor_sa.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/${var.service_name}:latest"
      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
    }
    timeout = "3600s" # 1 hour
  }
}

# 6. Restrict access to the specific principal you define.
resource "google_cloud_run_v2_service_iam_member" "allow_specific_invoker" {
  project  = google_cloud_run_v2_service.video_processor.project
  location = google_cloud_run_v2_service.video_processor.location
  name     = google_cloud_run_v2_service.video_processor.name
  role     = "roles/run.invoker"
  member   = var.invoker_principal
}

# --- Outputs ---
output "service_url" {
  description = "The URL of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.video_processor.uri
}

