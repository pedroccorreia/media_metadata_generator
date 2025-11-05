################################################################################
# Google Cloud Project Services
################################################################################

# Enables all necessary Google Cloud APIs for the media processing pipeline.
resource "google_project_service" "apis" {
  for_each = toset([
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "cloudbuild.googleapis.com",           # Needed for Cloud Run deployments if using source builds
    "artifactregistry.googleapis.com",     # Recommended for storing Docker images
    "cloudscheduler.googleapis.com",       # For optional batch processing trigger
    "cloudresourcemanager.googleapis.com", # Implicit, but good to ensure
    "aiplatform.googleapis.com",           # For Vertex AI services
    "speech.googleapis.com",               # For Speech-to-Text API
    "discoveryengine.googleapis.com",       # For Vertex AI Search
    "bigquery.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false # Set to true if you want to disable APIs on `terraform destroy`
}

################################################################################
# Artifact Registry for Docker Images
################################################################################

# Creates a centralized repository to store the Docker images for all Cloud Run services.
resource "google_artifact_registry_repository" "docker_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repo
  description   = "Docker repository for media metadata pipeline images"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis["artifactregistry.googleapis.com"]]
}

# Grant the Cloud Build service account permission to push images to the Artifact Registry.
resource "google_artifact_registry_repository_iam_member" "cloudbuild_ar_writer" {
  project    = google_artifact_registry_repository.docker_repo.project
  location   = google_artifact_registry_repository.docker_repo.location
  repository = google_artifact_registry_repository.docker_repo.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
  depends_on = [google_project_service.apis["cloudbuild.googleapis.com"]]
}

################################################################################
# Google Cloud Storage (GCS)
################################################################################

# Creates the GCS buckets that will be used as inputs for the media pipeline.
resource "google_storage_bucket" "input_buckets" {
  for_each                    = toset(var.input_bucket_names)
  project                     = var.project_id
  name                        = each.key
  location                    = var.region
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.apis["storage.googleapis.com"]]
}

################################################################################
# Google Cloud Pub/Sub Topics
################################################################################

# Central Ingestion Topic
# This topic receives initial messages about new files. The batch-processor-dispatcher
# subscribes to this topic to kick off the entire workflow.
# Messages to this topic will now need to be published manually or by another system.
resource "google_pubsub_topic" "central_ingestion_topic" {
  project    = var.project_id
  name       = "central-ingestion-topic"
  depends_on = [google_project_service.apis["pubsub.googleapis.com"]]
}

# Task-Specific Topics
# These topics decouple the dispatcher from the individual metadata generators.
# Each service subscribes to its own topic (e.g., summaries-generator -> summaries-topic).
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

# Dead-Letter Topic
# This topic receives messages that fail processing after multiple retries from any of the main subscriptions.
resource "google_pubsub_topic" "dead_letter_topic" {
  project = var.project_id
  name    = "dead-letter-topic"
}

################################################################################
# Service Accounts (IAM)
################################################################################

# Separate Service Account for Batch Processor/Dispatcher
# This follows the principle of least privilege. The dispatcher only needs permissions
# to publish to Pub/Sub and write initial records to Firestore. It does not need
# access to GCS objects or AI/ML APIs.
resource "google_service_account" "batch_processor_sa" {
  project      = var.project_id
  account_id   = "batch-processor-sa"
  display_name = "Service Account for Batch Processor Cloud Run Service"
  depends_on   = [google_project_service.apis["iam.googleapis.com"]]
}

# Consolidated Service Account for all Metadata Generators
# All metadata generation services (summary, transcription, previews) share this
# service account. It has a broader set of permissions required for their tasks,
# including reading from GCS, writing to Firestore, and calling Vertex AI and
# Speech-to-Text APIs.
resource "google_service_account" "metadata_generator_sa" {
  project      = var.project_id
  account_id   = "metadata-generator-sa"
  display_name = "Consolidated SA for Metadata Generator Cloud Run Services"
  depends_on   = [google_project_service.apis["iam.googleapis.com"]]
}

################################################################################
# IAM Bindings for Service Accounts
################################################################################

# Permissions for Batch Processor SA
# Grants the dispatcher service account the ability to subscribe to the central
# ingestion topic, publish to the task-specific topics, and write to Firestore.
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
# Grants the metadata generator services the ability to subscribe to their respective
# task topics, read/write GCS objects, write to Firestore, and use AI/ML services.
resource "google_project_iam_member" "metadata_generator_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
}

resource "google_project_iam_member" "metadata_generator_gcs_admin" {
  project = var.project_id
  # Allows creating, reading, and deleting GCS objects (e.g., for transcription results).
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
}

resource "google_project_iam_member" "metadata_generator_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
}

resource "google_project_iam_member" "metadata_generator_aiplatform_user" {
  project    = var.project_id
  role       = "roles/aiplatform.user"
  member     = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
  depends_on = [google_project_service.apis["aiplatform.googleapis.com"]]
}

resource "google_project_iam_member" "metadata_generator_speech_client" {
  project = var.project_id
  # The 'Speech Admin' role is used to allow the transcription service to create
  # a recognizer on-the-fly if it doesn't already exist.
  role       = "roles/speech.admin"
  member     = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
  depends_on = [google_project_service.apis["speech.googleapis.com"]]
}

################################################################################
# IAM Bindings for Google-Managed Service Agents
################################################################################

# Grants the Google-managed Vertex AI Service Agent permission to read from GCS.
# This is a critical step. When a Cloud Run service passes a `gs://` URI to a
# Vertex AI model (like Gemini), it's the Vertex AI service itself that reads the
# file, not the Cloud Run service account. This permission allows that to happen.
resource "google_project_iam_member" "aiplatform_sa_gcs_reader" {
  project    = var.project_id
  role       = "roles/storage.objectViewer"
  member     = "serviceAccount:service-409545154269@gcp-sa-aiplatform.iam.gserviceaccount.com"
  depends_on = [google_project_service.apis["aiplatform.googleapis.com"]]
}

resource "google_project_iam_member" "pubsub_sa_log_writer" {
  project    = var.project_id
  role       = "roles/logging.logWriter"
  member     = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on = [google_project_service.apis["pubsub.googleapis.com"]]
}

################################################################################
# IAM Bindings for Authenticated Pub/Sub Push Subscriptions
################################################################################

# Allows the Google-managed Pub/Sub service account to create OIDC tokens for our
# custom service accounts. This is required for Pub/Sub to securely invoke a
# This is required for authenticated Cloud Run invocation from Pub/Sub.
resource "google_service_account_iam_member" "batch_processor_sa_token_creator" {
  service_account_id = google_service_account.batch_processor_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_service_account_iam_member" "metadata_generator_sa_token_creator" {
  service_account_id = google_service_account.metadata_generator_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Pub/Sub Service Account to Cloud Run Invoker role for push subscriptions
# These bindings grant the service accounts (impersonated by Pub/Sub) the
# `run.invoker` role, allowing them to trigger their respective Cloud Run services.
resource "google_cloud_run_service_iam_member" "batch_processor_pubsub_invoker" {
  service  = "batch-processor-dispatcher"
  project  = var.project_id
  location = var.region
  role     = "roles/run.invoker"
  # The member is the service account that Pub/Sub will impersonate to invoke the service.
  # This must match the service_account_email in the subscription's push_config.
  member     = "serviceAccount:${google_service_account.batch_processor_sa.email}"
  depends_on = [google_cloud_run_service.batch_processor]
}

resource "google_cloud_run_service_iam_member" "summaries_generator_pubsub_invoker" {
  service    = "summaries-generator"
  project    = var.project_id
  location   = var.region
  role       = "roles/run.invoker"
  member     = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
  depends_on = [google_cloud_run_service.summaries_generator]
}

resource "google_cloud_run_service_iam_member" "transcription_generator_pubsub_invoker" {
  service    = "transcription-generator"
  project    = var.project_id
  location   = var.region
  role       = "roles/run.invoker"
  member     = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
  depends_on = [google_cloud_run_service.transcription_generator]
}

resource "google_cloud_run_service_iam_member" "previews_generator_pubsub_invoker" {
  service    = "previews-generator"
  project    = var.project_id
  location   = var.region
  role       = "roles/run.invoker"
  member     = "serviceAccount:${google_service_account.metadata_generator_sa.email}"
  depends_on = [google_cloud_run_service.previews_generator]
}


# Data source to get project number for Pub/Sub service account
data "google_project" "project" {
  project_id = var.project_id
}

################################################################################
# Firestore Database
################################################################################

# Creates the Firestore Native mode database instance, which will act as the
# central metadata store for all processed assets.
resource "google_firestore_database" "default_firestore_database" {
  project     = var.project_id
  name        = "(default)"        # The default database instance
  location_id = var.region         # Use the same region as other resources
  type        = "FIRESTORE_NATIVE" # Or "DATASTORE_MODE"
  depends_on  = [google_project_service.apis["firestore.googleapis.com"]]
}

################################################################################
# Cloud Run Services
################################################################################

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
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
      }
      container_concurrency = var.batch_processor_concurrency
      timeout_seconds       = 300 # 5 minutes default
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  autogenerate_revision_name = true
  depends_on                 = [google_project_service.apis["run.googleapis.com"]]
}

# Summaries Generator Cloud Run Service
resource "google_cloud_run_service" "summaries_generator" {
  project  = var.project_id
  location = var.region
  name     = "summaries-generator"
  template {
    spec {
      service_account_name = google_service_account.metadata_generator_sa.email # Consolidated SA
        env {
          name  = "LLM_MODEL"
          value = var.summaries_generator_llm_model
        }
      container_concurrency = var.summaries_generator_concurrency
      timeout_seconds       = 600 # 10 minutes, can be adjusted for long tasks
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
        env {
          name  = "GCP_REGION"
          value = var.region
        }
        env {
          name  = "LLM_MODEL"
          value = "flash 2.5"
        }
        resources {
          limits = {
            cpu    = "8"
            memory = "32Gi"
          }
        }
      }
      container_concurrency = var.transcription_generator_concurrency
      timeout_seconds       = 1800 # 30 minutes, can be adjusted for long audio
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
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
        env {
          name  = "LLM_MODEL"
          value = "flash 2.5"
        }
        resources {
          limits = {
            cpu    = "8"
            memory = "32Gi"
          }
        }
      }
      container_concurrency = var.previews_generator_concurrency
      timeout_seconds       = 600 # 10 minutes
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  autogenerate_revision_name = true
}

################################################################################
# Cloud Pub/Sub Subscriptions
################################################################################

# Subscription for Batch Processor/Dispatcher to Central Ingestion Topic
# This subscription connects the central ingestion topic to the dispatcher service.
# It uses an authenticated push configuration with the dispatcher's specific service account.
resource "google_pubsub_subscription" "batch_processor_sub" {
  project              = var.project_id
  name                 = "batch-processor-dispatcher-sub"
  topic                = google_pubsub_topic.central_ingestion_topic.name
  ack_deadline_seconds = 600 # Up to 10 minutes

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter_topic.id
    max_delivery_attempts = 5
  }

  # Push configuration to Cloud Run service
  push_config {
    push_endpoint = google_cloud_run_service.batch_processor.status[0].url
    # Pub/Sub service account needs invoker role on the Cloud Run service
    oidc_token {
      service_account_email = google_service_account.batch_processor_sa.email # Using separate SA
    }
  }
}

# Subscriptions for Metadata Generators to Task-Specific Topics
# These subscriptions connect each task topic to its corresponding generator service.
# They all use the consolidated metadata generator service account for authentication.
resource "google_pubsub_subscription" "summaries_sub" {
  project              = var.project_id
  name                 = "summaries-generator-sub"
  topic                = google_pubsub_topic.summaries_topic.name
  ack_deadline_seconds = 600 # Adjust based on expected processing time

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter_topic.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = google_cloud_run_service.summaries_generator.status[0].url
    oidc_token {
      service_account_email = google_service_account.metadata_generator_sa.email # Consolidated SA
    }
  }
}

resource "google_pubsub_subscription" "transcription_sub" {
  project              = var.project_id
  name                 = "transcription-generator-sub"
  topic                = google_pubsub_topic.transcription_topic.name
  ack_deadline_seconds = 600 # Adjust for potentially long transcription times 

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter_topic.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = google_cloud_run_service.transcription_generator.status[0].url
    oidc_token {
      service_account_email = google_service_account.metadata_generator_sa.email # Consolidated SA
    }
  }
}

resource "google_pubsub_subscription" "previews_sub" {
  project              = var.project_id
  name                 = "previews-generator-sub"
  topic                = google_pubsub_topic.previews_topic.name
  ack_deadline_seconds = 600

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter_topic.id
    max_delivery_attempts = 5
  }

  push_config {

    push_endpoint = google_cloud_run_service.previews_generator.status[0].url

    oidc_token {

      service_account_email = google_service_account.metadata_generator_sa.email # Consolidated SA

    }

  }

}



################################################################################

# Vertex AI Search

################################################################################

resource "google_discovery_engine_data_store" "firestore_datastore" {

  project                     = var.project_id
  location                    = "global"
  data_store_id               = "nebula-foundry-data-store"
  display_name                = "nebula-foundry-datastore"
  industry_vertical           = "GENERIC"
  solution_types              = ["SOLUTION_TYPE_SEARCH"]
  content_config              = "NO_CONTENT"
  create_advanced_site_search = false
  
  depends_on = [
    google_firestore_database.default_firestore_database,
    google_project_service.apis["discoveryengine.googleapis.com"]
  ]
}

################################################################################
# BigQuery for Dead-letter Topic
################################################################################

resource "google_bigquery_dataset" "topics" {
  project    = var.project_id
  dataset_id = "topics"
  location   = var.region
}

resource "google_bigquery_table" "dead_letter_table" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.topics.dataset_id
  table_id   = "dead_letter"

  schema = <<EOF
[
  {
    "name": "data",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF
}

resource "google_project_iam_member" "pubsub_to_bigquery_writer" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription" "dead_letter_bq_sub" {
  project = var.project_id
  name    = "dead-letter-bq-subscription"
  topic   = google_pubsub_topic.dead_letter_topic.name

  bigquery_config {
    table = "${google_bigquery_table.dead_letter_table.project}:${google_bigquery_table.dead_letter_table.dataset_id}.${google_bigquery_table.dead_letter_table.table_id}"
  }

  depends_on = [
    google_project_iam_member.pubsub_to_bigquery_writer
  ]
}
resource "google_pubsub_topic_iam_member" "pubsub_sa_dead_letter_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.dead_letter_topic.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "pubsub_sa_dead_letter_subscriber" {
  project      = var.project_id
  subscription = google_pubsub_subscription.batch_processor_sub.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "pubsub_sa_dead_letter_subscriber_summaries" {
  project      = var.project_id
  subscription = google_pubsub_subscription.summaries_sub.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "pubsub_sa_dead_letter_subscriber_transcription" {
  project      = var.project_id
  subscription = google_pubsub_subscription.transcription_sub.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "pubsub_sa_dead_letter_subscriber_previews" {
  project      = var.project_id
  subscription = google_pubsub_subscription.previews_sub.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_project_iam_member" "compute_sa_gcs_reader" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:407607324339-compute@developer.gserviceaccount.com"
}
resource "google_project_iam_member" "compute_sa_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:407607324339-compute@developer.gserviceaccount.com"
}
resource "google_project_iam_member" "compute_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:407607324339-compute@developer.gserviceaccount.com"
}