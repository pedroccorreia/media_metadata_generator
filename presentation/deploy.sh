#!/bin/bash

# Get the project ID from the gcloud config.
PROJECT_ID=$(gcloud config get-value project)

# Deploy the backend service.
echo "Deploying backend..."
gcloud run deploy nebula-foundry-ui-backend \
  --source ./ui-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=us-central1

# Get the URL of the deployed ui-backend service.
BACKEND_URL=$(gcloud run services describe nebula-foundry-ui-backend --platform managed --region us-central1 --format 'value(status.url)')

# If the backend URL is not available, exit.
if [ -z "$BACKEND_URL" ]; then
  echo "Backend deployment failed. Exiting."
  exit 1
fi

# Deploy the UI.
echo "Deploying UI with backend URL: $BACKEND_URL"
gcloud builds submit . --config cloudbuild.yaml --substitutions=_BACKEND_URL=$BACKEND_URL
