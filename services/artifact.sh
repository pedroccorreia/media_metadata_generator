#!/bin/bash

# A robust script to build and push a Docker image for a specific service
# to a Google Artifact Registry repository.
#
# This script now relies on environment variables for configuration,
# which can be sourced from a .env file or set in a CI/CD pipeline.
#
# Required Environment Variables:
#   - GCP_PROJECT_ID: Your Google Cloud project ID.
#   - GCP_REGION: The region for the Artifact Registry (e.g., us-central1).
#   - AR_REPO_NAME: The name of the Artifact Registry repository.
#
# Usage:
#   ./artifact_publish.sh <service_name>

set -e # Exit immediately if a command exits with a non-zero status.

SERVICE_NAME=$1

if [ -z "$SERVICE_NAME" ]; then
    echo "Error: Service name not provided."
    echo "Usage: $0 <service_name>"
    exit 1
fi

if [ -z "$GCP_PROJECT_ID" ] || [ -z "$GCP_REGION" ] || [ -z "$AR_REPO_NAME" ]; then
    echo "Error: Required environment variables (GCP_PROJECT_ID, GCP_REGION, AR_REPO_NAME) are not set."
    exit 1
fi

# echo "Authenticating Docker with Google Artifact Registry..."
# # This command configures the Docker client to use gcloud credentials
# # to authenticate with Artifact Registry for the specified region.
# gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev --quiet

IMAGE_TAG="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO_NAME}/${SERVICE_NAME}:latest"
DOCKERFILE_PATH="Dockerfile.${SERVICE_NAME}"

# echo "Building Docker image for ${SERVICE_NAME} from ${DOCKERFILE_PATH}..."
# # Use '.' as the build context to allow access to the 'common' directory.
# # The -f flag specifies the path to the Dockerfile.
# # The --push flag builds and pushes the image in a single step.
# docker buildx build --platform linux/amd64 --push -t  -f "${DOCKERFILE_PATH}" .

echo "Building Docker image for ${SERVICE_NAME} via Cloud Build..."

gcloud builds submit . --config=cloudbuild.yaml \
  --substitutions=_IMAGE_TAG=${IMAGE_TAG},_DOCKERFILE_PATH=${DOCKERFILE_PATH}

echo "Successfully published ${SERVICE_NAME}."