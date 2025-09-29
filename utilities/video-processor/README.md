Media Highlights Processor
A fully automated, cloud-native service designed for media organizations and news outlets. This utility ingests video metadata from a production pipeline to automatically clip, brand, and prepare video highlights for distribution.

This service is built to be a scalable, serverless component in a larger media processing workflow. It's triggered by new metadata, processes video in the background, and places the final assets in a specified cloud storage bucket, ready for the next step. The current video processing involves clipping the primary video asset such as hourly news asset into multiple sections using the metadata generation pipeline and processes the videos by adding logos in the end. The demo and utility is primarily useful for news corporations who want a fully automated process of pushing the key news highlights as soon as possible after the broadcast in their social channels such as youtube. 

Overview
The core workflow is designed for automation. The service is built to be triggered by an event, such as a new metadata document being added to a Firestore collection.

Trigger: The service is triggered by an HTTP POST request, which contains the ID of a Firestore document. (This is designed to be integrated with a Pub/Sub topic or Eventarc trigger in the future).

Fetch Metadata: The service reads the specified Firestore document to get the source video path, logo path, and a list of timestamps (sections).

Process: It downloads the main video and logo from Google Cloud Storage (GCS).

Clip & Brand: For each entry in the sections array, the service uses moviepy to:

Trim the video to the specified start_time and end_time.

Create a 3-second (customizable) end-card with the company logo composited on a white background.

Concatenate the trimmed clip with the logo end-card.

Store: The final, processed .mp4 file is uploaded to the designated output GCS bucket.

Architecture
This service is designed to run on Google Cloud Run, managed by Terraform.

(Metadata in Firestore) -> (HTTP POST Trigger) -> [Cloud Run: Media Highlights Processor] -> (Downloads video/logo from GCS) -> (Processes with Moviepy) -> (Uploads final clips to GCS)

Tech Stack
Application: Python 3.12

Web Server: Flask & Gunicorn

Video Processing: moviepy

Cloud Infrastructure:

Google Cloud Run (for serverless execution)

Google Cloud Storage (for file storage)

Google Firestore (for metadata)

Google Artifact Registry (for Docker image hosting)

Infrastructure as Code: Terraform

Project Structure
/
├── main.py                  # Flask server entry point for Cloud Run
├── video_processor.py       # Core video clipping and branding logic
├── firestore_util.py        # Utility for connecting to Firestore
├── storage_util.py          # Utility for GCS download/upload
├── main.tf                  # Terraform script for all infrastructure
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker configuration for the service
└── README.md                # This file

Deployment
This service is fully managed by Terraform. The following steps will build the container, create the necessary infrastructure, and deploy the service.

Prerequisites
Google Cloud SDK (gcloud) installed and authenticated.

Terraform installed.

Docker installed and running.

A .gitignore file created in the root to exclude venv, .terraform, and *.tfvars files.

Step-by-Step Deployment
1. Set Environment Variables
These are used by the Docker and Terraform commands.

# Set your project ID
export PROJECT_ID=$(gcloud config get-value project)

# Set the email of the user or service account that will invoke this service
export YOUR_EMAIL=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")

# Set standard names for the service
export REGION="us-central1"
export SERVICE_NAME="video-processor-service"
export REPO_ID="${SERVICE_NAME}-repo"

2. Initialize Terraform
This only needs to be run once.

terraform init

3. Create the Artifact Registry
We must create the repository before we can push our image to it.

terraform apply -var="project_id=${PROJECT_ID}" -target=google_artifact_registry_repository.repo

(Type yes to approve.)

4. Build and Push the Docker Image
This builds the application container and uploads it to the repository you just created.

# Configure Docker to authenticate with Google Cloud
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build the image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_ID}/${SERVICE_NAME}:latest .

# Push the image
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_ID}/${SERVICE_NAME}:latest

5. Deploy the Cloud Run Service
Run terraform apply again. This time, it will deploy the Cloud Run service, which can now find the image you just pushed.

terraform apply \
  -var="project_id=${PROJECT_ID}" \
  -var="invoker_principal=user:${YOUR_EMAIL}"

(Type yes to approve the rest of the infrastructure.)

How to Test
After deployment, Terraform will output a service_url. You can use curl to send a test POST request, simulating a trigger.

Get the URL and your auth token:

export SERVICE_URL=$(terraform output -raw service_url)
export TOKEN=$(gcloud auth print-identity-token)

Send the test request:
This command triggers the service to process the document specified in the JSON payload.

curl -X POST "${SERVICE_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
        "doc_id": "ENTER YOUR FIRESTORE DOCUMENT ID HERE",
        "collection_name": "ENTER YOUR FIRESTORE COLLECTION NAME HERE"
      }'

You can monitor the processing progress in the Cloud Run -> Logs tab in the Google Cloud Console.

Future Roadmap
[ ] Full Pub/Sub Integration: Create a Pub/Sub topic based trigger to automatically invoke this service whenever a document is written to the Firestore collection.

[ ] Social Media Distribution: Add modules to automatically upload the processed clips to platforms like YouTube, Twitter, and Facebook.

[ ] Error Handling & Retries: Implement a dead-letter queue for failed processing jobs.