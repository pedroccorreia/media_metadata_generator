import os
import datetime
from flask import Flask, request
import google.auth
import google.auth.transport.requests
from google.cloud import firestore
from google.cloud import storage

app = Flask(__name__)
db = firestore.Client()
storage_client = storage.Client()

GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET")
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION")
SERVICE_ACCOUNT_EMAIL = os.environ.get("SERVICE_ACCOUNT_EMAIL")

if not GCS_BUCKET_NAME or not FIRESTORE_COLLECTION or not SERVICE_ACCOUNT_EMAIL:
    raise RuntimeError("Configuration error: GCS_BUCKET, FIRESTORE_COLLECTION, and SERVICE_ACCOUNT_EMAIL environment variables must be set.")

@app.route("/", methods=["POST"])
def update_all_signed_urls_in_bucket():
    
    try:
        credentials, project = google.auth.default()

        # When running on Cloud Run, the default credentials do not have a private
        # key. To sign a URL, we must use the IAM signBlob API, which requires an
        # OAuth2 access token. We refresh the credentials to get a current token.
        auth_request = google.auth.transport.requests.Request()
        credentials.refresh(auth_request)

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        all_blobs = bucket.list_blobs()
        
        print("Building an index of Firestore documents by 'file_name'...")
        docs_by_filename = {}
        for doc in db.collection(FIRESTORE_COLLECTION).stream():
            doc_data = doc.to_dict()
            # Ensure the document has the 'file_name' field before adding to the map
            if 'file_name' in doc_data:
                docs_by_filename[doc_data['file_name']] = doc.reference
        print(f"Index built. Found {len(docs_by_filename)} documents with a 'file_name' field.")

        batch = db.batch()
        updated_count = 0
        skipped_count = 0
        
        expiration_delta = datetime.timedelta(days=7)

        for blob in all_blobs:
            object_name = blob.name
            try:
                # Use the in-memory map for a fast lookup
                if object_name not in docs_by_filename:
                    skipped_count += 1
                    continue

                doc_ref = docs_by_filename[object_name]
                
                expiration_datetime = datetime.datetime.now(datetime.timezone.utc) + expiration_delta
                
                # To sign a URL without a private key, we must delegate the signing
                # to the service account itself using the IAM API. This is done by
                # providing the service account's email and a valid access token.
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=expiration_datetime,
                    method="GET",
                    service_account_email=SERVICE_ACCOUNT_EMAIL,
                    access_token=credentials.token,
                )
                
                update_data = {
                    'signed_url': signed_url,
                    'url_expires_at': expiration_datetime,
                    'last_url_update': firestore.SERVER_TIMESTAMP
                }
                
                batch.set(doc_ref, update_data, merge=True)
                updated_count += 1

            except Exception as e:
                print(f"An error occurred while processing {object_name}: {e}")
                skipped_count += 1
        
        batch.commit()
        
        success_message = f"Process complete. Successfully updated {updated_count} documents. Skipped {skipped_count} objects."
        print(success_message)
        return success_message, 200

    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(error_msg)
        return error_msg, 500

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT, debug=True)
