import os
import re
from google.cloud import storage
import subprocess
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Google Cloud Storage client
storage_client = storage.Client()

# Initialize Firebase Admin SDK (will be initialized only once)
# This initialization defaults to using Application Default Credentials (ADC).
# ADC automatically looks for credentials in environments like Google Cloud Functions/Run
# or via the GOOGLE_APPLICATION_CREDENTIALS environment variable for local testing.
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

db = firestore.client()

def process_video_for_clips(document_id: str):
    """
    Fetches video information and time codes from a Firebase Firestore document
    based on an ID, processes the video, clips it, and uploads the clips to a
    'shorts/' subfolder in the origin bucket.

    Args:
        document_id (str): The ID of the document in the Firebase Firestore
                           collection that contains the video URI and time codes.
    """
    print(f"Received request for document ID: {document_id}")

    # 1. Fetch data from Firebase Firestore
    try:
        # Assuming your data is in a collection named 'video_metadata'.
        # Adjust 'video_metadata' to your actual collection name.
        doc_ref = db.collection('video_metadata').document(document_id)
        doc = doc_ref.get()

        if not doc.exists:
            print(f"Error: Document with ID '{document_id}' not found in Firestore.")
            return

        doc_data = doc.to_dict()
        print(f"Fetched document data: {json.dumps(doc_data, indent=2)}")

        # Extract gcs_uri (assuming it's at the top level of the document)
        gcs_uri = doc_data.get('gcs_uri')
        if not gcs_uri:
            print("Error: 'gcs_uri' not found in the Firestore document.")
            return

        # Extract time_codes_data from summary.section[]
        summary = doc_data.get('summary')
        if not summary:
            print("Error: 'summary' object not found in the Firestore document.")
            return

        time_codes_data = summary.get('section', [])
        if not isinstance(time_codes_data, list):
            print("Error: 'summary.section' is not a list. Expected a list of time codes.")
            return
        if not time_codes_data:
            print("Warning: No time codes found in 'summary.section[]'. No clips will be generated.")
            return

        print(f"Video URI from Firestore: {gcs_uri}")
        print(f"Time codes from Firestore: {json.dumps(time_codes_data, indent=2)}")

    except Exception as e:
        print(f"Error fetching data from Firebase: {e}")
        return

    # Parse GCS URI to get bucket name and blob name
    match = re.match(r'gs://([^/]+)/(.*)', gcs_uri)
    if not match:
        print(f"Error: Invalid GCS URI format: {gcs_uri}")
        return

    bucket_name = match.group(1)
    source_blob_name = match.group(2)
    local_source_path = f"/tmp/{os.path.basename(source_blob_name)}"

    try:
        # 2. Download the source video from GCS
        print(f"Downloading '{source_blob_name}' from bucket '{bucket_name}' to '{local_source_path}'...")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(local_source_path)
        print("Download complete.")

        # Determine output format (e.g., based on input video extension)
        _, ext = os.path.splitext(local_source_path)
        if not ext:
            ext = ".mp4" # Default to mp4 if no extension is found

        generated_clip_paths = []

        # 3. Process each time code entry to create clips using avtools
        for i, clip_info in enumerate(time_codes_data):
            start_time = clip_info.get("start_time")
            end_time = clip_info.get("end_time")
            description = clip_info.get("description", f"clip_{i+1}") # Use description for filename if available

            if not start_time or not end_time:
                print(f"Skipping clip {i+1} due to missing start_time or end_time.")
                continue

            # Sanitize description for filename
            safe_description = re.sub(r'[^a-zA-Z0-9_.-]', '_', description)
            output_filename = f"{os.path.splitext(os.path.basename(source_blob_name))[0]}_{safe_description}{ext}"
            local_output_path = f"/tmp/{output_filename}"

            print(f"Creating clip {i+1}: {description} from {start_time} to {end_time}")

            # --- Placeholder for avtools command execution ---
            # In a real scenario, you would replace this with the actual avtools command.
            # You would need to ensure `avtools` is installed in your environment (e.g., Dockerfile for Cloud Run).
            # Example avtools command structure (hypothetical, adjust as per actual avtools usage):
            # avtools cut --input <input_file> --start <start_time> --end <end_time> --output <output_file>

            avtools_command = [
                "avtools", # Assumes 'avtools' is in PATH. Or specify full path.
                "cut",
                "--input", local_source_path,
                "--start", start_time,
                "--end", end_time,
                "--output", local_output_path
            ]
            print(f"Executing avtools command: {' '.join(avtools_command)}")

            try:
                # Execute the avtools command
                # capture_output=True collects stdout/stderr, text=True decodes as text
                # check=True raises CalledProcessError on non-zero exit code
                result = subprocess.run(avtools_command, check=True, capture_output=True, text=True)
                print(f"avtools Stdout:\n{result.stdout}")
                if result.stderr:
                    print(f"avtools Stderr:\n{result.stderr}")
                print(f"Clip created at '{local_output_path}'")
                generated_clip_paths.append(local_output_path)
            except subprocess.CalledProcessError as e:
                print(f"Error running avtools for clip {description}: {e}")
                print(f"Stdout: {e.stdout}")
                print(f"Stderr: {e.stderr}")
            except FileNotFoundError:
                print("Error: 'avtools' command not found. Make sure avtools (and FFmpeg) is installed and in your PATH.")
                print("Skipping clip generation for this segment.")
            except Exception as e:
                print(f"An unexpected error occurred during avtools execution: {e}")

        # 4. Upload all generated clips to the 'shorts/' subfolder in the origin bucket
        if not generated_clip_paths:
            print("No clips were successfully generated to upload.")
            return

        print(f"Uploading {len(generated_clip_paths)} clips to 'shorts/' in bucket '{bucket_name}'...")
        for local_clip_path in generated_clip_paths:
            destination_blob_name = f"shorts/{os.path.basename(local_clip_path)}"
            print(f"Uploading '{local_clip_path}' to '{destination_blob_name}'...")
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(local_clip_path)
            print(f"Successfully uploaded '{destination_blob_name}'")

        print("All clips processed and uploaded successfully!")

    except Exception as e:
        print(f"An error occurred during video processing: {e}")
    finally:
        # Clean up local files
        print("Cleaning up temporary files...")
        if os.path.exists(local_source_path):
            os.remove(local_source_path)
            print(f"Removed '{local_source_path}'")
        for p in generated_clip_paths:
            if os.path.exists(p):
                os.remove(p)
                print(f"Removed '{p}'")
        print("Cleanup complete.")

# --- For Google Cloud Functions (HTTP Trigger Example) ---
# This function acts as the entry point when deployed as an HTTP Cloud Function.
# It expects a JSON payload with a 'document_id' key.
def handle_http_trigger(request):
    request_json = request.get_json(silent=True)
    if request_json and 'document_id' in request_json:
        document_id = request_json['document_id']
        process_video_for_clips(document_id)
        return f"Video clipping initiated for document ID: {document_id}", 200
    else:
        return "Please provide a 'document_id' in the request body.", 400

# --- Example Usage for local testing ---
if __name__ == "__main__":
    # IMPORTANT: For this example to run locally, you need:
    # 1. Google Cloud SDK installed and authenticated (`gcloud auth application-default login`)
    # 2. A GCS bucket with a video file accessible by your authenticated user.
    # 3. `avtools` (and its dependency `ffmpeg`) installed and in your system's PATH.
    #    For `avtools`, follow instructions from:
    #    https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/tree/main/experiments/mcp-genmedia
    # 4. Firebase Admin SDK setup:
    #    - Install Firebase Admin SDK: `pip install firebase-admin`
    #    - Ensure your service account has Firestore Data Viewer/Editor roles.
    #    - For local testing, ensure your `GOOGLE_APPLICATION_CREDENTIALS` environment variable
    #      points to a Firebase service account key file (downloadable from Firebase Console)
    #      OR authenticate via `gcloud auth application-default login`.

    # Replace with an actual document ID from your Firestore database
    example_document_id = "your_video_document_id" # <--- IMPORTANT: Change this!

    print("\n--- Starting Video Clipping Process (via Firebase) ---")
    process_video_for_clips(example_document_id)
    print("--- Video Clipping Process Finished ---\n")

    # Example Firestore document structure for 'video_metadata' collection:
    # Document ID: "your_video_document_id"
    # {
    #   "gcs_uri": "gs://your-gcs-bucket/your-video.mp4",
    #   "summary": {
    #     "section": [
    #       {"start_time": "00:00:05", "end_time": "00:00:15", "description": "Opening_Scene"},
    #       {"start_time": "00:00:20", "end_time": "00:00:30", "description": "Highlight_Moment_1"},
    #       {"start_time": "00:00:45", "end_time": "00:00:55", "description": "Conclusion_Summary"}
    #     ]
    #   }
    # }
