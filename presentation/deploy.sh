#!/bin/bash

# Get the project ID from the gcloud config.
PROJECT_ID=$(gcloud config get-value project)

# Get the URL of the deployed ui-backend service.
BACKEND_URL=$(gcloud run services describe ui-backend --platform managed --region us-central1 --format 'value(status.url)')

# If the backend URL is not available, deploy the backend first.
if [ -z "$BACKEND_URL" ]; then
  echo "Deploying backend..."
  gcloud builds submit . --config cloudbuild.yaml --substitutions=_BACKEND_URL="" \ 
  BACKEND_URL=$(gcloud run services describe ui-backend --platform managed --region us-central1 --format 'value(status.url)')
else
  echo "Backend already deployed."
fi

# Deploy the UI.
 echo "Deploying UI..."
 gcloud builds submit . --config cloudbuild.yaml --substitutions=_BACKEND_URL=$BACKEND_URL
