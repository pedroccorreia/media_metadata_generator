#!/bin/bash

# Function to deploy the backend
deploy_backend() {
  echo "Deploying backend..."
  PROJECT_ID=$(gcloud config get-value project)
  gcloud run deploy nebula-foundry-ui-backend \
    --source ./ui-backend \
    --platform managed \
    --region us-central1 \
    --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=us-central1,FIRESTORE_COLLECTION=media_assets
}

# Function to deploy the UI
deploy_ui() {
  echo "Deploying UI..."
  BACKEND_URL=$(gcloud run services describe nebula-foundry-ui-backend --platform managed --region us-central1 --format 'value(status.url)')
  if [ -z "$BACKEND_URL" ]; then
    echo "Backend URL is not available. Cannot deploy UI."
    exit 1
  fi
    echo "Deploying UI with backend URL: $BACKEND_URL"             
    (cd ui && gcloud builds submit . --config cloudbuild.yaml --substitutions=_BACKEND_URL=$BACKEND_URL --machine-type=e2-highcpu-32)}

# Main logic
case "$1" in
  ui)
    deploy_ui
    ;;
  backend)
    deploy_backend
    ;;
  all)
    deploy_backend
    deploy_ui
    ;;
  *)
    echo "Usage: $0 {ui|backend|all}"
    echo "No argument provided, deploying all."
    deploy_backend
    deploy_ui
    ;;
esac
