# GCP Metadata Pipeline Architecture

This document outlines a serverless, scalable, and resilient pipeline for ingesting media files, generating various types of metadata using the Gemini API, and storing the results in a flexible format for consumption by APIs and frontend applications.

## Architecture Diagram

The following diagram illustrates the flow of data through the pipeline's various layers and services.

## Pipeline Components

The architecture is broken down into several logical layers, each with specific responsibilities.

### 1. Ingestion Layer

* **Cloud Pub/Sub (Ingestion Topic):** The primary intake point. New media file information (audio, video, etc.) is submitted to this topic, acting as the event source for the entire pipeline.
* **Cloud Pub/Sub Submission:** Submission to the ingestion topic initiates the pipeline.
* **Cloud Pub/Sub (Ingestion Topic):** Decouples the file upload event from the processing logic. This provides resilience by queuing events, allowing for retries and preventing data loss if downstream services are temporarily unavailable.

### 2. Orchestration Layer

* **Cloud Run Service (Orchestrator/Dispatcher):** This service is the brain of the pipeline's initial phase. It subscribes to the Ingestion Topic. Upon receiving a message, it:
    1.  Creates an initial document in Firestore for the new asset, noting its file path and setting a `processing` status.
    2.  Publishes separate messages to dedicated task-specific topics for each type of metadata to be generated (e.g., summary, transcription, preview clips).
* **Cloud Pub/Sub (Task-Specific Topics):** Enables parallel and independent processing of different metadata types. Separate topics exist for each task (e.g., `summaries-generation-topic`, `transcription-generation-topic`).

### 3. Metadata Generation Layer

This layer consists of multiple independent Cloud Run services that perform the actual metadata extraction using Gemini models.

* **Summaries-Generator-Service:** Subscribes to the summaries topic. It calls the Gemini API with multiple prompts to generate a comprehensive analysis, including a main summary, itemized points, subject topics, and key sections/clips with timestamps. It then combines these results and updates the asset's document in Firestore.
* **Transcription-Generator-Service:** Subscribes to the transcription topic, calls the Gemini API for audio transcription, and updates the Firestore document.
* **Previews-Generator-Service:** Subscribes to the previews topic, calls the Gemini API to identify suitable segments for previews or short clips, and updates the Firestore document.

### 4. Storage Layer

* **Firestore (NoSQL Document Database):** The central, scalable repository for all generated metadata. Its flexible, document-based schema is ideal for storing semi-structured metadata and allows for independent, atomic updates to different parts of an asset's record.

#### Example Firestore Document Structure

The data for each media asset is stored in the `media_assets` collection.

```
/artifacts/{appId}/public/data/media_assets/{asset_id}
{
  "file_path": "gs://your-bucket/path/to/file.mp4",
  "upload_time": "2025-08-05T10:00:00Z",
  "overall_status": "processing",
  "summary": {
    "status": "completed",
    "summary": "A medium length summary of the video content...",
    "itemized_summary": [
      {"item": "First key point from the video."},
      {"item": "Second key point from the video."}
    ],
    "subject_topics": [
      {"topic": "Media Analysis"},
      {"topic": "Generative AI"}
    ],
    "sections": [
      {
        "type": "highlight",
        "start_time": "00:32",
        "end_time": "01:15",
        "reason": "This section contains the main argument."
      }
    ],
    "error_message": null,
    "last_updated": "2025-08-05T10:05:00Z"
  },
  "transcription": {
    "text": "...",
    "language": "en",
    "status": "pending",
    "last_updated": null
  },
  "previews": {
    "clips": [{"start_time": 10, "end_time": 20}],
    "status": "failed",
    "error": "Model failed to identify clips.",
    "last_updated": "2025-08-05T10:10:00Z"
  }
}
```

### 5. API & Consumption Layer

* **Cloud Run Service (Metadata API Gateway):** Provides a clean, RESTful interface (e.g., `/api/v1/assets/{asset_id}/metadata`) for applications to consume the generated metadata from Firestore.
* **Frontend Application:** The user-facing application that calls the API Gateway to retrieve and display metadata. It is designed to gracefully handle partial or missing data by checking the `status` fields within the Firestore document.

## Key Implementation Considerations

* **Error Handling & Retries:** Implement robust error handling with retry mechanisms at each step, such as Pub/Sub message re-delivery and exponential backoff for API calls.
* **Security:** Use IAM roles and service accounts to grant least-privilege access between services.
* **Cost Monitoring:** Monitor costs associated with Gemini API usage and Cloud Run instances.
* **Observability:** Use Cloud Logging, Monitoring, and Trace to track pipeline performance and troubleshoot issues.
* **Version Control:** Manage all service code in a Git repository and use a CI/CD pipeline (e.g., Cloud Build) for automated deployments.
<!-- Push your Docker images to Artifact registry
cd services
sh artifact_publish.sh

cd terraform
terraform init
terraform plan -->
