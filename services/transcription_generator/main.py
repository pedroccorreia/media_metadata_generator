""" Worker node for transcription of the entire video. """

import os
import json
import base64
import logging
from flask import Flask, request
# Speech-to-Text imports
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.exceptions import NotFound
# Additional imports for GCS and ffmpeg
from google.cloud import storage
import ffmpeg

from common.media_asset_manager import MediaAssetManager
from common.logging_config import configure_logger

# Configure logger for the service
configure_logger()
logger = logging.getLogger(__name__)

# Initialize clients and Flask app
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GCP_REGION", "us-central1")
asset_manager = MediaAssetManager(project_id=project_id)
storage_client = storage.Client(project=project_id)

# Initialize Flask app
app = Flask(__name__)


def generate_transcription(asset_id: str, video_gcs_uri: str) -> dict:
    """
    Extracts audio from a video file in GCS, transcribes it using the
    Speech-to-Text API, and returns the result.

    Args:
        asset_id (str): The ID of the asset.
        video_gcs_uri (str): GCS URI of the video file.

    Returns:
        dict: A dictionary containing the transcription text and word timings,
              or an error dictionary if generation fails.
    """
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": video_gcs_uri}}
    logger.info("Starting transcription generation for asset: %s", asset_id, extra=log_extra)

    local_video_path = ""
    local_audio_path = ""

    try:
        # 1. Setup paths
        if not video_gcs_uri.startswith("gs://"):
            raise ValueError("Invalid GCS URI provided.")

        bucket_name, blob_name = video_gcs_uri.replace("gs://", "").split("/", 1)
        video_filename = os.path.basename(blob_name)

        local_video_path = f"/tmp/{asset_id}_{video_filename}"
        local_audio_path = f"/tmp/{asset_id}.flac"

        audio_gcs_path = f"{asset_id}/audio.flac"
        audio_gcs_uri = f"gs://{bucket_name}/{audio_gcs_path}"
        results_gcs_path = f"gs://{bucket_name}"

        # 2. Download video from GCS
        logger.info("Downloading video file: %s", video_gcs_uri, extra=log_extra)
        bucket = storage_client.bucket(bucket_name)
        video_blob = bucket.blob(blob_name)
        video_blob.download_to_filename(local_video_path)

        # 3. Extract audio using ffmpeg
        logger.info("Extracting audio from %s", local_video_path, extra=log_extra)
        try:
            ffmpeg.input(local_video_path).output(
                local_audio_path, acodec='flac', ar='16000', vn=None
            ).run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        except ffmpeg.Error as e:
            stderr = e.stderr.decode() if e.stderr else "No stderr"
            raise RuntimeError(f"ffmpeg failed: {stderr}")

        # 4. Upload extracted audio to GCS
        logger.info("Uploading extracted audio to %s", audio_gcs_uri, extra=log_extra)
        audio_blob = bucket.blob(audio_gcs_path)
        audio_blob.upload_from_filename(local_audio_path)

        # 5. Transcribe using Speech-to-Text API
        speech_client = SpeechClient(
            client_options=ClientOptions(api_endpoint=f"{location}-speech.googleapis.com")
        )

        language_code = "en-US"  # This could be made configurable
        recognizer_id = f"chirp-long-form-{language_code.lower()}"
        recognizer_name = f"projects/{project_id}/locations/{location}/recognizers/{recognizer_id}"

        try:
            recognizer = speech_client.get_recognizer(name=recognizer_name)
        except NotFound:
            logger.info("Recognizer '%s' not found, creating it.", recognizer_id, extra=log_extra)
            recognizer_request = cloud_speech.CreateRecognizerRequest(
                parent=f"projects/{project_id}/locations/{location}",
                recognizer_id=recognizer_id,
                recognizer=cloud_speech.Recognizer(language_codes=[language_code], model="chirp"),
            )
            recognizer = speech_client.create_recognizer(request=recognizer_request).result()

        config = cloud_speech.RecognitionConfig(
            features=cloud_speech.RecognitionFeatures(
                enable_automatic_punctuation=True, enable_word_time_offsets=True
            ),
            auto_decoding_config={},
        )

        batch_recognize_request = cloud_speech.BatchRecognizeRequest(
            recognizer=recognizer.name,
            recognition_output_config={"gcs_output_config": {"uri": results_gcs_path}},
            files=[{"config": config, "uri": audio_gcs_uri}],
        )

        operation = speech_client.batch_recognize(request=batch_recognize_request)
        logger.info("Waiting for transcription operation to complete...", extra=log_extra)
        response = operation.result()

        # 6. Process results from GCS
        result_uri = response.results[audio_gcs_uri].uri
        result_bucket_name, result_blob_name = result_uri.replace("gs://", "").split("/", 1)

        result_blob = storage_client.bucket(result_bucket_name).blob(result_blob_name)
        transcript_data = json.loads(result_blob.download_as_text())

        # 7. Format the output
        full_transcript = ""
        words = []
        for result in transcript_data.get("results", []):
            alternative = result.get("alternatives", [{}])[0]
            full_transcript += alternative.get("transcript", "") + " "
            for word_info in alternative.get("words", []):
                words.append({
                    "word": word_info.get("word"),
                    "start_time": word_info.get("startOffset"),
                    "end_time": word_info.get("endOffset"),
                })

        final_result = {
            "text": full_transcript.strip(),
            "words": words,
            "gcs_uri": result_uri
        }
        logger.info("Successfully generated transcription for asset %s", asset_id, extra=log_extra)
        return final_result

    except Exception as e:
        logger.error("Failed to generate transcription for asset %s", asset_id, exc_info=True, extra=log_extra)
        return {"error": f"Failed to process transcription: {str(e)}"}
    finally:
        # 8. Cleanup local files
        for path in [local_video_path, local_audio_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError as e:
                    logger.warning("Error cleaning up file %s: %s", path, e, extra=log_extra)

@app.route("/", methods=["POST"])
def handle_message():
    """
    Cloud Run entry point that processes Pub/Sub messages to generate transcriptions.
    """
    request_json = request.get_json(silent=True)
    if not request_json or 'message' not in request_json:
        logger.error("Invalid Pub/Sub message format: missing 'message' key.")
        return 'Bad Request: invalid Pub/Sub message format', 400

    pubsub_message = request_json['message']
    asset_id = None  # Initialize asset_id for error logging

    try:
        message_data = json.loads(base64.b64decode(pubsub_message['data']).decode('utf-8'))
        asset_id = message_data.get("asset_id")
        file_location = message_data.get("file_location")
        file_name = message_data.get("file_name")

        if not all([asset_id, file_location, file_name]):
            logger.error("Message missing required data: asset_id, file_location or file_name.", extra={"extra_fields": {"message_data": message_data}})
            return "Bad Request: missing required data", 400

        log_extra = {"extra_fields": {"asset_id": asset_id, "file_name": file_name, "file_location": file_location}}
        logger.info("Processing transcription generation request for asset: %s", asset_id, extra=log_extra)

        asset_manager.update_asset_metadata(asset_id, "transcription", {"status": "processing"})

        transcription_results = generate_transcription(asset_id, file_location)

        if "error" in transcription_results:
            error_msg = transcription_results["error"]
            update_data = {"status": "failed", "error_message": error_msg}
            asset_manager.update_asset_metadata(asset_id, "transcription", update_data)
            logger.error("Transcription generation failed for asset %s: %s", asset_id, error_msg, extra=log_extra)
        else:
            update_data = {
                "status": "completed", 
                "text": transcription_results.get("text"), 
                "words": transcription_results.get("words", []), 
                "gcs_uri": transcription_results.get("gcs_uri"),
                "error_message": None
            }
            asset_manager.update_asset_metadata(asset_id, "transcription", update_data)
            logger.info("Successfully completed transcription generation for asset: %s", asset_id, extra=log_extra)

        return '', 204
    except Exception as e:
        logger.critical("Unhandled exception during transcription generation.", exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
        if asset_id:
            asset_manager.update_asset_metadata(asset_id, "transcription", {"status": "failed", "error_message": f"Critical error in service: {str(e)}"})
        return "Error processing message, but acknowledging to prevent retries.", 204
