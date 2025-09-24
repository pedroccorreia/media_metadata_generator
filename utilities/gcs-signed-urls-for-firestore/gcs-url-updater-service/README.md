GCS Signed URL Refresh Utility
Overview
This utility was created to demonstrate how archival media content can be surfaced securely for Agentspace agents and other users to reference, along with its corresponding metadata from Firestore.

It solves the problem of expiring Google Cloud Storage (GCS) signed URLs, which have a maximum lifespan of 7 days. This service provides a secure, on-demand, authenticated endpoint that, when triggered, will:

Scan all objects in a specified GCS bucket.

Query a specified Firestore collection to find documents where the file_name field matches the GCS object name.

Generate a new, 7-day signed URL for each matching object.

Update the corresponding Firestore document with the new signed_url, url_expires_at, and last_url_update fields.

How it Works
This utility follows a secure, serverless architecture that relies on a dedicated Service Account and the Google Cloud IAM API for authentication.

Authentication: Signing without a Key
This service does not use a static private key (key.json) file in production. It leverages the Cloud Run environment's attached service account and its IAM permissions.

When the service needs to sign a URL, it:

Loads its own service account credentials from the environment (google.auth.default()).

Refreshes these credentials to get a short-lived OAuth access_token.

Passes this access_token and the service_account_email to the generate_signed_url function.

This method securely delegates the cryptographic signing operation to the IAM API, which requires the service account to have the Service Account Token Creator role.

Workflow
An authorized user (e.g., an admin) sends an authenticated HTTP POST request to the service's URL.

Cloud Run activates the service, which runs as its dedicated Service Account (gcs-url-updater-sa).

The Python app starts. It first queries all documents in the Firestore collection and builds an in-memory map of {'file_name': doc_reference}. This is highly efficient and avoids querying Firestore inside a loop.

The service then lists all objects in the GCS bucket.

For each object, it looks up its name in the pre-built map.

If a match is found, it generates a new signed URL using the IAM delegation method described above.

It adds the update to a Firestore batch.

After iterating through all objects, it commits the batch, updating all documents in a single atomic transaction.

Configuration
Configuration is handled by setting the variables in the Configuration section at the top of the deploy.sh script.

The script will then pass these values as environment variables to the Cloud Run service, specifically:

GCS_BUCKET

FIRESTORE_COLLECTION

SERVICE_ACCOUNT_EMAIL

Deployment
The service is deployed using a single shell script that handles all aspects of setup and deployment.

Set Configuration: Edit the variables in the Configuration section at the top of deploy.sh (e.g., PROJECT_ID, GCS_BUCKET, FIRESTORE_COLLECTION).

Make Executable: Ensure the script is executable:

chmod +x deploy.sh

Run Deploy: Run the script from within its folder:

./deploy.sh

The script will automatically:

Enable all required Google Cloud APIs.

Create the dedicated service account (gcs-url-updater-sa).

Grant all necessary IAM permissions to the service account (storage.objectViewer, datastore.user, iam.serviceAccountTokenCreator).

Grant all necessary permissions to the Cloud Build service (run.admin, iam.serviceAccountUser, etc.).

Build the container image and deploy it to Cloud Run with the correct environment variables.

How to Refresh Signed URLs (Usage)
The service is triggered by sending an authenticated HTTP POST request to the service's main URL. No request body or JSON payload is required, as the service processes all objects in the bucket.

1. Get Your Service URL
You can find the URL in the output of the deployment script or by running this command:

gcloud run services describe gcs-url-updater --platform=managed --region=us-central1 --format="value(status.url)"

(Note: Replace us-central1 if you used a different region in your deploy.sh script.)

2. Run the curl Command
This command will automatically fetch your service's URL, get a valid authentication token for your gcloud user, and send the required POST request to trigger the refresh.

curl -X POST "$(gcloud run services describe gcs-url-updater --platform=managed --region=us-central1 --format="value(status.url)")" \
-H "Authorization: Bearer $(gcloud auth print-identity-token)"

3. Monitor the Update
The curl command will return a success message from the service, for example:
Process complete. Successfully updated 123 documents. Skipped 4 objects.

You can monitor the detailed, real-time progress by opening the Logs tab for the gcs-url-updater service in the Google Cloud Run console.