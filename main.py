# main.py
import os
import tempfile
import functions_framework

from google.cloud import firestore
from google.cloud import storage
from moviepy import VideoFileClip

# Initialize clients globally.
# In a Cloud Functions environment, this is a best practice as it allows
# for connection reuse across function invocations.
storage_client = storage.Client()
db = firestore.Client()
@functions_framework.cloud_event
def fetch_video_and_store_metadata(cloud_event):
    """
    Cloud Function triggered by a new object in a GCS bucket.
    Fetches an MP4 video, extracts its duration, and stores the
    metadata in a Firestore collection named 'video_metadata'.

    Args:
        event (dict): The GCS event dictionary containing 'bucket' and 'name'.
        context (google.cloud.functions.Context): Metadata for the event.
    """
    data = cloud_event.data
    file_name = data.get('name')
    bucket_name = data.get('bucket')
    #bucket_name = cloud_event['bucket']

    # We only want to process mp4 files.
    if not file_name.lower().endswith('.mp4'):
        print(f"File {file_name} is not an MP4 file. Skipping.")
        return

    print(f"Processing file: {file_name} from bucket: {bucket_name}.")

    # Create a temporary directory to download the video to.
    # Using a 'with' statement ensures the directory and its contents are
    # automatically cleaned up after the block is executed.
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a path for the temporary file.
        temp_video_path = os.path.join(temp_dir, os.path.basename(file_name))

        try:
            # 1. Download the video from GCS to the temporary path.
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(file_name)
            
            print(f"Downloading gs://{bucket_name}/{file_name} to {temp_video_path}...")
            blob.download_to_filename(temp_video_path)
            print("Download complete.")

            # 2. Extract metadata (duration) using moviepy.
            print("Extracting video duration...")
            with VideoFileClip(temp_video_path) as video_clip:
                duration_seconds = video_clip.duration
            print(f"Video duration: {duration_seconds:.2f} seconds.")

            # 3. Store metadata in Firestore.
            # We'll use the video's filename (without extension) as the document ID
            # to ensure uniqueness and easy lookups.
            doc_id = os.path.splitext(os.path.basename(file_name))[0]
            collection_name = "video_metadata"
            
            doc_ref = db.collection(collection_name).document(doc_id)

            metadata = {
                'gcs_bucket': bucket_name,
                'gcs_path': file_name,
                'gcs_uri': f"gs://{bucket_name}/{file_name}",
                'duration_seconds': duration_seconds,
                'processed_at': firestore.SERVER_TIMESTAMP, # Use server timestamp.
            }

            print(f"Storing metadata in Firestore collection '{collection_name}' with document ID '{doc_id}'...")
            doc_ref.set(metadata)
            print("Successfully stored metadata in Firestore.")

        except Exception as e:
            print(f"An error occurred: {e}")
            # Re-raising the exception will cause the function to fail, which
            # can be useful for monitoring and retries.
            raise

# --- Main block for local testing ---
if __name__ == "__main__":
    # To test this script locally:
    # 1. Make sure you have a video file in your GCS bucket.
    # 2. Set the TEST_BUCKET_NAME and TEST_FILE_NAME variables below.
    # 3. Authenticate with Google Cloud: `gcloud auth application-default login`
    # 4. Install dependencies: `pip install -r requirements.txt`
    # 5. Run the script: `python main.py`

    # --- Configuration for local testing ---
    TEST_BUCKET_NAME = "your-gcs-bucket-name"  # <--- CHANGE THIS
    TEST_FILE_NAME = "videos/sample-video.mp4" # <--- CHANGE THIS (e.g., path/to/your/video.mp4)
    # -----------------------------------------

    if TEST_BUCKET_NAME == "your-gcs-bucket-name" or not TEST_FILE_NAME:
        print("="*60)
        print("!!! PLEASE UPDATE `TEST_BUCKET_NAME` and `TEST_FILE_NAME` !!!")
        print("="*60)
    else:
        # Create a mock event dictionary to simulate a GCS trigger.
        mock_event = {
            'bucket': TEST_BUCKET_NAME,
            'name': TEST_FILE_NAME
        }
        # The context argument is not used in this function, so it can be None.
        mock_context = None

        print("--- Running local test ---")
        fetch_video_and_store_metadata(mock_event)
        print("--- Local test finished ---")
