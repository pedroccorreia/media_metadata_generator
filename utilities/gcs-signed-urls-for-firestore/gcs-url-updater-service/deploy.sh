#!/bin/bash

# --- Configuration ---
# Set your project and service details here.
PROJECT_ID="ENTER YOUR PROJECT ID HERE"
REGION="ENTER YOUR REGION HERE"
GCS_BUCKET="ENTER YOUR BUCKET NAME WITH FILES HERE"
FIRESTORE_COLLECTION="ENTER YOUR FIRESTORE COLLECTION NAME HERE"
SERVICE_NAME="gcs-url-updater"
APP_SERVICE_ACCOUNT_NAME="gcs-url-updater-sa"
# --- End of Configuration ---

# --- Internal Script Variables (Do not change) ---
APP_SERVICE_ACCOUNT_EMAIL="${APP_SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# --- Script Starts Here ---

echo "--- Step 1: Configuring gcloud to use project ${PROJECT_ID} ---"
gcloud config set project ${PROJECT_ID}

echo -e "\n--- Step 2: Enabling required Google Cloud APIs ---"
gcloud services enable run.googleapis.com iam.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com storage.googleapis.com

# --- Create the application's own service account ---
echo -e "\n--- Step 3: Creating a dedicated Service Account for the App ---"
if gcloud iam service-accounts describe ${APP_SERVICE_ACCOUNT_EMAIL} > /dev/null 2>&1; then
    echo "Service Account [${APP_SERVICE_ACCOUNT_NAME}] already exists. Skipping creation."
else
    echo "Creating Service Account [${APP_SERVICE_ACCOUNT_NAME}]."
    gcloud iam service-accounts create ${APP_SERVICE_ACCOUNT_NAME} --display-name="Service Account for GCS URL Updater"
    echo "Waiting for 10 seconds for IAM propagation..."
    sleep 10
fi

# --- Grant permissions to the application's service account ---
echo -e "\n--- Step 4: Granting permissions to the App's Service Account (so it can run correctly) ---"
gcloud projects add-iam-policy-binding ${PROJECT_ID} --member="serviceAccount:${APP_SERVICE_ACCOUNT_EMAIL}" --role="roles/storage.objectViewer" --condition=None >/dev/null
gcloud projects add-iam-policy-binding ${PROJECT_ID} --member="serviceAccount:${APP_SERVICE_ACCOUNT_EMAIL}" --role="roles/datastore.user" --condition=None >/dev/null
gcloud iam service-accounts add-iam-policy-binding ${APP_SERVICE_ACCOUNT_EMAIL} --member="serviceAccount:${APP_SERVICE_ACCOUNT_EMAIL}" --role="roles/iam.serviceAccountTokenCreator" >/dev/null

# --- Grant permissions to the Cloud Build service ---
echo -e "\n--- Step 5: Granting permissions to the Cloud Build Service (so it can deploy) ---"
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
CLOUD_BUILD_SERVICE_ACCOUNT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
gcloud projects add-iam-policy-binding ${PROJECT_ID} --member="serviceAccount:${CLOUD_BUILD_SERVICE_ACCOUNT}" --role="roles/run.admin" --condition=None >/dev/null
gcloud projects add-iam-policy-binding ${PROJECT_ID} --member="serviceAccount:${CLOUD_BUILD_SERVICE_ACCOUNT}" --role="roles/iam.serviceAccountUser" --condition=None >/dev/null
gcloud projects add-iam-policy-binding ${PROJECT_ID} --member="serviceAccount:${CLOUD_BUILD_SERVICE_ACCOUNT}" --role="roles/artifactregistry.writer" --condition=None >/dev/null
gcloud projects add-iam-policy-binding ${PROJECT_ID} --member="serviceAccount:${CLOUD_BUILD_SERVICE_ACCOUNT}" --role="roles/logging.logWriter" --condition=None >/dev/null
echo "Permissions check complete."


# --- Build and Deploy the service ---
echo -e "\n--- Step 6: Building and deploying the service to Cloud Run ---"
# This single command handles build and deploy. It is the most reliable method.
# It correctly passes all three environment variables to the service.
gcloud run deploy ${SERVICE_NAME} \
  --source . \
  --platform=managed \
  --region=${REGION} \
  --service-account=${APP_SERVICE_ACCOUNT_EMAIL} \
  --set-env-vars="GCS_BUCKET=${GCS_BUCKET},FIRESTORE_COLLECTION=${FIRESTORE_COLLECTION},SERVICE_ACCOUNT_EMAIL=${APP_SERVICE_ACCOUNT_EMAIL}" \
  --no-allow-unauthenticated

# --- Final Output ---
if [ $? -eq 0 ]; then
  echo -e "\n--- ✅ Deployment Complete! ---"
  SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform=managed --region=${REGION} --format="value(status.url)")
  echo "Service Name: ${SERVICE_NAME}"
  echo "Service URL: ${SERVICE_URL}"
else
    echo -e "\n--- ❌ Deployment Failed ---"
    echo "Please check the error messages above."
fi