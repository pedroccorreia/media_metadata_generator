import os
import json
import base64
import logging

import vertexai
from flask import Flask, request
from vertexai.generative_models import GenerativeModel, Part

from common.media_asset_manager import MediaAssetManager
from common.logging_config import configure_logger

# Configure logger for the service
configure_logger()
logger = logging.getLogger(__name__)

# Initialize clients and Flask app
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
# A location must be specified for Vertex AI
location = os.environ.get("GCP_REGION", "us-central1")
asset_manager = MediaAssetManager(project_id=project_id)
app = Flask(__name__)

# Initialize Vertex AI
try:
    vertexai.init(project=project_id, location=location)
except Exception as e:
    logger.critical(f"Could not initialize Vertex AI: {e}", exc_info=True)
    # The application might not be able to function, but we let it start
    # to potentially handle other routes or configurations.


def generate_summary(asset_id: str, file_location: str, prompt_config: dict) -> dict:
    """
    Generates a summary and chapters for a media asset using GenAI models.
    It makes separate calls to the model for summary text and chapters,
    then combines the results.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file.
        prompt_config (dict): Configuration for summary generation.

    Returns:
        dict: A dictionary containing the summary text and a list of chapters,
              or an error dictionary if generation fails.
    """
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location, "prompt_config": prompt_config}}
    logger.info(f"Generating summary and chapters for asset: {asset_id}", extra=log_extra)

    try:
        # --- Get configurations ---
        summary_model_name = prompt_config.get("model")
        summary_prompt = prompt_config.get("prompt")

        chapters_config = prompt_config.get("chapters", {})
        chapters_prompt = chapters_config.get("prompt")
        chapters_model_name = chapters_config.get("model", summary_model_name)

        if not summary_prompt:
            raise ValueError("Prompt configuration is missing 'prompt' for summary.")

        video_file = Part.from_uri(file_location, mime_type="video/mp4")
        final_result = {}

        # --- Generate Summary Text ---
        summary_model = GenerativeModel(summary_model_name)
        logger.info(f"Calling Gemini for summary text using model {summary_model_name} for asset: {asset_id}", extra=log_extra)
        summary_response = summary_model.generate_content(
            [video_file, summary_prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        summary_data = json.loads(summary_response.text)
        logger.info(f"Successfully generated summary text for asset {asset_id}", extra=log_extra)
        final_result.update(summary_data)

        # --- Generate Chapters (if configured) ---
        if chapters_prompt:
            chapters_model = GenerativeModel(chapters_model_name)
            logger.info(f"Calling Gemini for chapters using model {chapters_model_name} for asset: {asset_id}", extra=log_extra)
            chapters_response = chapters_model.generate_content(
                [video_file, chapters_prompt],
                generation_config={"response_mime_type": "application/json"}
            )
            chapters_data = json.loads(chapters_response.text)
            logger.info(f"Successfully generated chapters for asset {asset_id}", extra=log_extra)
            final_result.update(chapters_data)
        else:
            logger.info("No chapter prompt configured, skipping chapter generation.", extra=log_extra)

        # --- Combine results ---
        logger.info(f"Successfully generated summary and chapters for asset {asset_id}", extra=log_extra)
        return final_result

    except Exception as e:
        logger.error(f"Failed to generate summary/chapters for asset {asset_id}", exc_info=True, extra=log_extra)
        return {"error": f"Failed to process with Gemini: {str(e)}"}

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
        message_data = json.loads(base64.b64decode(pubsub_message['data']).decode('utf-8'))
        asset_id = message_data.get("asset_id")
        file_location = message_data.get("file_location")
        prompt_config = message_data.get("prompt_config")

        if not all([asset_id, file_location, prompt_config]):
            logger.error("Message missing required data: asset_id, file_location, or prompt_config.", extra={"extra_fields": {"message_data": message_data}})
            return "Bad Request: missing required data", 400
        
        log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
        logger.info(f"Processing summary generation request for asset: {asset_id}", extra=log_extra)
        
        asset_manager.update_asset_metadata(asset_id, "summary", {"status": "processing"})
        results = generate_summary(asset_id, file_location, prompt_config)

        if "error" in results:
            update_data = {"status": "failed", "error_message": results["error"]}
            asset_manager.update_asset_metadata(asset_id, "summary", update_data)
            logger.error(f"Summary generation failed for asset: {asset_id}", extra=log_extra)
        else:
            update_data = {"status": "completed", "text": results.get("text"), "chapters": results.get("chapters", []), "error_message": None}
            asset_manager.update_asset_metadata(asset_id, "summary", update_data)
            logger.info(f"Successfully completed summary generation for asset: {asset_id}", extra=log_extra)

        return '', 204
    except Exception as e:
        logger.critical("Unhandled exception during summary generation.", exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
        if asset_id:
            asset_manager.update_asset_metadata(asset_id, "summary", {"status": "failed", "error_message": f"Critical error in service: {str(e)}"})
        return "Error processing message, but acknowledging to prevent retries.", 204
