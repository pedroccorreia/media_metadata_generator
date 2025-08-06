# Enable necessary Google Cloud APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "cloudbuild.googleapis.com",      # Needed for Cloud Run deployments if using source builds
    "artifactregistry.googleapis.com", # Recommended for storing Docker images
    "cloudscheduler.googleapis.com",   # For optional batch processing trigger
    "cloudresourcemanager.googleapis.com" # Implicit, but good to ensure
  ])
  project = var.project_id
  service = each.key
  disable_on_destroy = false # Set to true if you want to disable APIs on `terraform destroy`
}

# --- GCS Buckets (Inputs) ---
# Note: These buckets still exist, but no automatic notification to Pub/Sub is configured.
resource "google_storage_bucket" "input_buckets" {
  for_each = toset(var.input_bucket_names)
  project  = var.project_id
  name     = each.key
  location = var.region
  uniform_bucket_level_access = true
  depends_on = [google_project_service.apis["storage.googleapis.com"]]
}

# --- Cloud Pub/Sub Topics ---

# Central Ingestion Topic
# Messages to this topic will now need to be published manually or by another system.
resource "google_pubsub_topic" "central_ingestion_topic" {
  project = var.project_id
  name    = "central-ingestion-topic"
  depends_on = [google_project_service.apis["pubsub.googleapis.com"]]
}

# Task-Specific Topics
resource "google_pubsub_topic" "summaries_topic" {
  project = var.project_id
  name    = "summaries-generation-topic"
}

resource "google_pubsub_topic" "transcription_topic" {
  project = var.project_id
  name    = "transcription-generation-topic"
}

resource "google_pubsub_topic" "previews_topic" {
  project = var.project_id
  name    = "previews-generation-topic"
}

# --- Cloud Run Service Accounts ---

# Separate Service Account for Batch Processor/Dispatcher
resource "google_service_account" "batch_processor_sa" {
  project      = var.project_id
  account_id   = "batch-processor-sa"
  display_name = "Service Account for Batch Processor Cloud Run Service"
  depends_on = [google_project_service.apis["iam.googleapis.com"]]
}

# Consolidated Service Account for all Metadata Generators
resource "google_service_account" "metadata_generator_sa" {
  project      = var.project_id
  account_id   = "metadata-generator-sa"
  display_name = "Consolidated SA for Metadata Generator Cloud Run Services"
  depends_on = [google_project_service.apis["iam.googleapis.com"]]
}

# --- IAM Bindings for Service Accounts ---

# Permissions for Batch Processor SA
resource "google_project_iam_member" "batch_processor_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.batch_processor_sa.email}"
}

resource "google_project_iam_member" "batch_processor_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.batch_processor_sa.email}"
}

resource "google_project_iam_member" "batch_processor_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user" # Firestore uses datastore roles for R/W
  member  = "serviceAccount:${google_service_account.batch_processor_sa.email}"
}

# Permissions for Consolidated Metadata Generator SA
resource "google_project_iam_member" "metadata_generator_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
}

resource "google_project_iam_member" "metadata_generator_gcs_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
}

resource "google_project_iam_member" "metadata_generator_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
}

# Pub/Sub Service Account to Cloud Run Invoker role for push subscriptions
# This allows Pub/Sub to invoke the Cloud Run service when a message arrives
resource "google_cloud_run_service_iam_member" "batch_processor_pubsub_invoker" {
  service  = "batch-processor-dispatcher"
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on = [google_cloud_run_service.batch_processor]
}

resource "google_cloud_run_service_iam_member" "summaries_generator_pubsub_invoker" {
  service  = "summaries-generator"
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on = [google_cloud_run_service.summaries_generator]
}

resource "google_cloud_run_service_iam_member" "transcription_generator_pubsub_invoker" {
  service  = "transcription-generator"
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on = [google_cloud_run_service.transcription_generator]
}

resource "google_cloud_run_service_iam_member" "previews_generator_pubsub_invoker" {
  service  = "previews-generator"
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on = [google_cloud_run_service.previews_generator]
}

# Data source to get project number for Pub/Sub service account
data "google_project" "project" {
  project_id = var.project_id
}

# --- Firestore Database Component ---
resource "google_firestore_database" "default_firestore_database" {
  project     = var.project_id
  name        = "(default)" # The default database instance
  location_id = var.region  # Use the same region as other resources
  type        = "FIRESTORE_NATIVE" # Or "DATASTORE_MODE"
  depends_on = [google_project_service.apis["firestore.googleapis.com"]]
}

# --- Cloud Run Services ---

# Batch Processor/Dispatcher Cloud Run Service
resource "google_cloud_run_service" "batch_processor" {
  project  = var.project_id
  location = var.region
  name     = "batch-processor-dispatcher"
  template {
    spec {
      service_account_name = google_service_account.batch_processor_sa.email # Using separate SA
      containers {
        image = var.batch_processor_image # Placeholder
        env {
          name  = "PUBSUB_TOPIC_SUMMARIES"
          value = google_pubsub_topic.summaries_topic.name
        }
        env {
          name  = "PUBSUB_TOPIC_TRANSCRIPTION"
          value = google_pubsub_topic.transcription_topic.name
        }
        env {
          name  = "PUBSUB_TOPIC_PREVIEWS"
          value = google_pubsub_topic.previews_topic.name
        }
      }
      container_concurrency = var.batch_processor_concurrency
      timeout_seconds = 300 # 5 minutes default
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  autogenerate_revision_name = true
  depends_on = [google_project_service.apis["run.googleapis.com"]]
}

# Summaries Generator Cloud Run Service
resource "google_cloud_run_service" "summaries_generator" {
  project  = var.project_id
  location = var.region
  name     = "summaries-generator"
  template {
    spec {
      service_account_name = google_service_account.metadata_generator_sa.email # Consolidated SA
      containers {
        image = var.summaries_generator_image # Placeholder
      }
      container_concurrency = var.summaries_generator_concurrency
      timeout_seconds = 600 # 10 minutes, can be adjusted for long tasks
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  autogenerate_revision_name = true
}

# Transcription Generator Cloud Run Service
resource "google_cloud_run_service" "transcription_generator" {
  project  = var.project_id
  location = var.region
  name     = "transcription-generator"
  template {
    spec {
      service_account_name = google_service_account.metadata_generator_sa.email # Consolidated SA
      containers {
        image = var.transcription_generator_image # Placeholder
      }
      container_concurrency = var.transcription_generator_concurrency
      timeout_seconds = 1800 # 30 minutes, can be adjusted for long audio
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  autogenerate_revision_name = true
}

# Previews Generator Cloud Run Service
resource "google_cloud_run_service" "previews_generator" {
  project  = var.project_id
  location = var.region
  name     = "previews-generator"
  template {
    spec {
      service_account_name = google_service_account.metadata_generator_sa.email # Consolidated SA
      containers {
        image = var.previews_generator_image # Placeholder
      }
      container_concurrency = var.previews_generator_concurrency
      timeout_seconds = 600 # 10 minutes
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  autogenerate_revision_name = true
}

# --- Cloud Pub/Sub Subscriptions ---

# Subscription for Batch Processor/Dispatcher to Central Ingestion Topic
resource "google_pubsub_subscription" "batch_processor_sub" {
  project = var.project_id
  name    = "batch-processor-dispatcher-sub"
  topic    = google_pubsub_topic.central_ingestion_topic.name
  ack_deadline_seconds = 600 # Up to 10 minutes

  # Push configuration to Cloud Run service
  push_config {
    push_endpoint = google_cloud_run_service.batch_processor.uri
    # Pub/Sub service account needs invoker role on the Cloud Run service
    oidc_token {
      service_account_email = google_service_account.batch_processor_sa.email # Using separate SA
    }
  }
}

# Subscriptions for Metadata Generators to Task-Specific Topics
resource "google_pubsub_subscription" "summaries_sub" {
  project = var.project_id
  name    = "summaries-generator-sub"
  topic   = google_pubsub_topic.summaries_topic.name
  ack_deadline_seconds = 600 # Adjust based on expected processing time

  push_config {
    push_endpoint = google_cloud_run_service.summaries_generator.uri
    oidc_token {
      service_account_email = google_service_account.metadata_generator_sa.email # Consolidated SA
    }
  }
}

resource "google_pubsub_subscription" "transcription_sub" {
  project = var.project_id
  name    = "transcription-generator-sub"
  topic   = google_pubsub_topic.transcription_topic.name
  ack_deadline_seconds = 1800 # Adjust for potentially long transcription times (up to 30 mins)

  push_config {
    push_endpoint = google_cloud_run_service.transcription_generator.uri
    oidc_token {
      service_account_email = google_service_account.metadata_generator_sa.email # Consolidated SA
    }
  }
}

resource "google_pubsub_subscription" "previews_sub" {
  project = var.project_id
  name    = "previews-generator-sub"
  topic   = google_pubsub_topic.previews_topic.name
  ack_deadline_seconds = 600

  push_config {
    push_endpoint = google_cloud_run_service.previews_generator.uri
    oidc_token {
      service_account_email = google_service_account.metadata_generator_sa.email # Consolidated SA
    }
  }
}
