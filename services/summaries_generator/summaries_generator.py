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
app = Flask(__name__)


def generate_summary(asset_id: str, file_location: str, prompt_config: dict) -> dict:
    """
    Simulates generating a summary and chapters for a media asset.
    In a real scenario, this would involve calling a GenAI model with the asset's
    transcription or content.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file.
        prompt_config (dict): Configuration for summary generation (e.g., length, format).

    Returns:
        dict: A dictionary containing the summary text and a list of chapters.
              Returns an empty dict if generation fails.
    """
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location, "prompt_config": prompt_config}}
    logger.info(f"Simulating summary generation for asset: {asset_id}", extra=log_extra)

    # --- Simulation Logic ---
    summary_length = prompt_config.get("length", "medium")
    num_chapters = prompt_config.get("chapters", 3)

    simulated_summary = f"This is a simulated summary of {summary_length} length for asset {asset_id}."
    
    simulated_chapters = []
    for i in range(num_chapters):
        simulated_chapters.append({
            "title": f"Chapter {i+1}: The Adventure Begins",
            "timestamp": f"00:{(i*5):02d}:00"
        })

    logger.info(f"Successfully simulated generation of summary for asset {asset_id}", extra={"extra_fields": {"asset_id": asset_id}})
    
    return {
        "text": simulated_summary,
        "chapters": simulated_chapters
    }

@app.route("/", methods=["POST"])
def handle_message():
    """
    Cloud Run entry point that processes Pub/Sub messages to generate summaries.
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
        prompt_config = message_data.get("prompt_config")

        if not all([asset_id, file_location, prompt_config]):
            logger.error("Message missing required data: asset_id, file_location, or prompt_config.", extra={"extra_fields": {"message_data": message_data}})
            return "Bad Request: missing required data", 400
        
        log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
        logger.info(f"Processing summary generation request for asset: {asset_id}", extra=log_extra)
        
        asset_manager.update_asset_metadata(asset_id, "summary", {"status": "processing"})
        summary_results = generate_summary(asset_id, file_location, prompt_config)

        update_data = {"status": "completed", "text": summary_results.get("text"), "chapters": summary_results.get("chapters", []), "error_message": None}
        asset_manager.update_asset_metadata(asset_id, "summary", update_data)
        logger.info(f"Successfully completed summary generation for asset: {asset_id}", extra=log_extra)

        return '', 204
    except Exception as e:
        logger.critical("Unhandled exception during summary generation.", exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
        if asset_id:
            asset_manager.update_asset_metadata(asset_id, "summary", {"status": "failed", "error_message": f"Critical error in service: {str(e)}"})
        return "Error processing message, but acknowledging to prevent retries.", 204
