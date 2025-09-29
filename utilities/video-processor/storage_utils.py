import logging
import os
from google.cloud import storage
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_gcs_client():
    """Initializes and returns a Google Cloud Storage client."""
    try:
   
        project_id = "Your Project id here"  # Make sure this is your correct project ID
        storage_client = storage.Client(project=project_id)
       
        return storage_client
    except Exception as e:
        logging.error(f"Failed to create GCS client: {e}", exc_info=True)
        return None

def parse_gcs_uri(uri: str) -> (str, str):
    """Parses a GCS URI and returns the bucket name and object name."""
    try:
        parsed_uri = urlparse(uri)
        if parsed_uri.scheme != 'gs':
            raise ValueError("Invalid GCS URI scheme. Must be 'gs'.")
        bucket_name = parsed_uri.netloc
        object_name = parsed_uri.path.lstrip('/')
        if not bucket_name or not object_name:
             raise ValueError("GCS URI must include both bucket and object name.")
        return bucket_name, object_name
    except ValueError as e:
        logging.error(f"Could not parse GCS URI '{uri}': {e}")
        return None, None


def download_from_gcs(gcs_uri: str, temp_dir: str) -> str:
    """Downloads a file from a GCS URI to a temp directory and returns its local path."""
    if not gcs_uri:
        raise ValueError("A valid GCS URI must be provided.")
    try:
        storage_client = get_gcs_client()
        if not storage_client:
            raise ConnectionError("Could not connect to Google Cloud Storage.")

        bucket_name, blob_name = parse_gcs_uri(gcs_uri)
        if not bucket_name:
            raise ValueError(f"Could not parse bucket name from URI: {gcs_uri}")

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        local_path = os.path.join(temp_dir, os.path.basename(blob_name))

        logging.info(f"Downloading {gcs_uri} to {local_path}...")
        blob.download_to_filename(local_path)
        logging.info(f"Successfully downloaded {os.path.basename(blob_name)}.")
        return local_path
    except Exception as e:
        logging.error(f"Failed to download from GCS URI '{gcs_uri}': {e}", exc_info=True)
        raise


def upload_blob(bucket_name: str, source_file_name: str, destination_blob_name: str):
    """Uploads a file to the bucket."""
    try:
        storage_client = get_gcs_client()
        if not storage_client:
            raise ConnectionError("Could not connect to Google Cloud Storage.")
            
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)

        logging.info(f"File {source_file_name} uploaded to {destination_blob_name} in bucket {bucket_name}.")
    except Exception as e:
        logging.error(f"Failed to upload {source_file_name} to {destination_blob_name}: {e}", exc_info=True)