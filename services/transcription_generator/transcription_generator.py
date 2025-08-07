import os
import json
import logging
from flask import Flask, request

from common.media_asset_manager import MediaAssetManager
from common.logging_config import configure_logger

# Configure logger for the service
configure_logger()
logger = logging.getLogger(__name__)

# Initialize clients and Flask app
project_id = os.environ.get("GCP_PROJECT_ID")
asset_manager = MediaAssetManager(project_id=project_id)

# Initialize Flask app
app = Flask(__name__)

def generate_transcription(asset_id: str, file_location: str) -> dict:
    """
    Simulates generating a transcription for a media asset.
    In a real scenario, this would involve calling a speech-to-text API.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file.

    Returns:
        dict: A dictionary containing the transcription text and a list of words with timestamps.
              Returns an empty dict if generation fails.
    """
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
    logger.info(f"Simulating transcription generation for asset: {asset_id}", extra=log_extra)

    # --- Simulation Logic ---
    simulated_text = f"This is a simulated transcription for asset {asset_id}. The content discusses various aspects of media analysis and metadata generation."
    simulated_words = [
        {"word": "This", "start_time": "0s", "end_time": "0.5s"},
        {"word": "is", "start_time": "0.6s", "end_time": "0.7s"},
        {"word": "a", "start_time": "0.8s", "end_time": "0.85s"},
        {"word": "simulated", "start_time": "0.9s", "end_time": "1.5s"},
        {"word": "transcription", "start_time": "1.6s", "end_time": "2.4s"},
    ]

    return {
        "text": simulated_text,
        "words": simulated_words
    }

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
        message_data = json.loads(pubsub_message['data'].decode('utf-8'))
        asset_id = message_data.get("asset_id")
        file_location = message_data.get("file_location")

        if not all([asset_id, file_location]):
            logger.error("Message missing required data: asset_id or file_location.", extra={"extra_fields": {"message_data": message_data}})
            return "Bad Request: missing required data", 400
        
        log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
        logger.info(f"Processing transcription generation request for asset: {asset_id}", extra=log_extra)
        
        asset_manager.update_asset_metadata(asset_id, "transcription", {"status": "processing"})
        transcription_results = generate_transcription(asset_id, file_location)

        update_data = {"status": "completed", "text": transcription_results.get("text"), "words": transcription_results.get("words", []), "error_message": None}
        asset_manager.update_asset_metadata(asset_id, "transcription", update_data)
        logger.info(f"Successfully completed transcription generation for asset: {asset_id}", extra=log_extra)

        return '', 204
    except Exception as e:
        logger.critical("Unhandled exception during transcription generation.", exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
        if asset_id:
            asset_manager.update_asset_metadata(asset_id, "transcription", {"status": "failed", "error_message": f"Critical error in service: {str(e)}"})