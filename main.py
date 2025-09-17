import os
import tempfile
import moviepy as mp
from google.cloud import storage
from google.cloud import firestore

from firestore_utils import get_video_metadata
from final_highlight_gen_tg import analyze_video_overview, initialize_vertex_client,create_highlight_reel
# Set up clients for GCS and Firestore.
# The clients will use your environment's authentication credentials.
# For local development, ensure you are authenticated (e.g., `gcloud auth application-default login`).
storage_client = storage.Client()
firestore_client = firestore.Client()
model_id="gemini-2.5-pro"


def process_gcs_video_metadata(bucket_name, source_blob_name):
    """
    Downloads a video from a GCS bucket, extracts its duration,
    and stores the metadata in a Firestore document.

    Args:
        bucket_name (str): The name of the GCS bucket.
        source_blob_name (str): The full path to the video object in the bucket.
    """
    
    # 1. Download the video to a temporary local file.
    # We use a temporary file to avoid cluttering the system and
    # ensure it's deleted automatically.
    
    # Create a temporary file with a .mp4 extension for moviepy to recognize it.
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_file_path = temp_file.name
    temp_file.close()

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        #local_path = os.path.join(temp_dir, os.path.basename(blob_name))
        
        print(f"Downloading {source_blob_name} from bucket {bucket_name} to {temp_file_path}...")
        blob.download_to_filename(temp_file_path)
        print("Download complete.")

        # 2. Use moviepy to get the video metadata.
        # This is a much more efficient and reliable method for technical metadata
        # like duration, as opposed to a large language model.
        try:
            video_clip = mp.VideoFileClip(temp_file_path)
            duration_seconds = video_clip.duration
            print(f"Video duration: {duration_seconds} seconds")
            
            # Close the video clip to release the file handle
            video_clip.close()

        except Exception as e:
            print(f"Error processing video with moviepy: {e}")
            return

        # 3. Store the metadata in a Firestore document.
        # The document will be created in the 'video_metadata' collection.
        metadata = {
            'video_path': f"gs://{bucket_name}/{source_blob_name}",
            'duration_seconds': duration_seconds,
            'timestamp': firestore.SERVER_TIMESTAMP
        }

        doc_ref = firestore_client.collection('video_metadata').add(metadata)
        print(f"Metadata for {source_blob_name} stored in Firestore with ID: {doc_ref[1].id}")
        return doc_ref[1].id

    finally:
        # Clean up the temporary file, regardless of success or failure.
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"Cleaned up temporary file: {temp_file_path}")


# --- Example Usage ---
# To run this script, you will need to:
# 1. Have a GCP project with a GCS bucket and Firestore database.
# 2. Have a video file uploaded to your GCS bucket.
# 3. Install the required libraries:
#    pip install google-cloud-storage google-cloud-firestore moviepy
# 4. Authenticate your environment (e.g., using `gcloud auth application-default login`).
# 5. Uncomment the lines below and replace with your specific bucket and video file path.

if __name__ == "__main__":
     your_bucket_name = "fox-metadata-input"  # Replace with your GCS bucket name
     your_video_path = "ncis_los_angeles.mp4"
     collection_name = "video_metadata"
     
     doc_id=process_gcs_video_metadata(your_bucket_name, your_video_path)
     #print(f"Stored metadata in Firestore document ID: {doc_id}")
     Document_data=get_video_metadata(firestore_client, collection_name, doc_id)
     print(f"Fetched metadata from Firestore document ID: {doc_id}")
     print(f"Document data: {Document_data}")
     video_url=Document_data['video_path']
     duration=Document_data['duration_seconds']
     print(f"Video URL: {video_url}")
     print(f"Creating Highlight Reel...")
     create_highlight_reel(video_url,duration,model_id)




     #print(f"Analyzing Video Overview...")
     #analyze_video_overview(video_url,duration,model_id)




