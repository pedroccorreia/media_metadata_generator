import os
import json
import base64
import logging
from flask import Flask, request

from common.media_asset_manager import MediaAssetManager
from common.logging_config import configure_logger

# Configure logger for the service
configure_logger()
logger = logging.getLogger(__name__)

# Initialize clients
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
asset_manager = MediaAssetManager(project_id=project_id)

# Initialize Flask app
app = Flask(__name__)

def generate_previews(asset_id: str, file_location: str, prompt_config: dict) -> dict:
    """
    Simulates generating previews for a media asset.
    In a real scenario, this would involve video processing libraries (e.g., FFmpeg)
    to extract frames or generate video clips.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file (e.g., gs://bucket/path/to/file.mp4).
        prompt_config (dict): Configuration for preview generation (e.g., type, count, format).

    Returns:
        dict: A dictionary containing preview information (e.g., list of GCS URIs for clips).
              Returns an empty dict if generation fails or is not applicable.
    """
    logger.info("Simulating preview generation for asset: %s", asset_id, extra={"extra_fields": {"asset_id": asset_id, "file_location": file_location, "prompt_config": prompt_config}})

    # Extract bucket and blob name from GCS URI
    if not file_location.startswith("gs://"):
        logger.error("Invalid GCS URI format: %s", file_location, extra={"extra_fields": {"asset_id": asset_id}})
        return {}

    path_parts = file_location[len("gs://"):].split('/', 1)
    if len(path_parts) < 2:
        logger.error("Invalid GCS URI format, no blob name: %s", file_location, extra={"extra_fields": {"asset_id": asset_id}})
        return {}
    
    bucket_name, blob_name = path_parts

    # --- Simulation Logic ---
    # In a real implementation, you would download the file, process it with a library
    # like FFmpeg, and upload the resulting clips back to GCS.
    num_previews = prompt_config.get("count", 3)
    preview_format = prompt_config.get("format", "jpeg")
    
    # Create a list of simulated preview clip URIs.
    previews = []
    for i in range(num_previews):
        # Example output path: gs://your-bucket/previews/asset_id/preview_1.jpeg
        preview_path = f"gs://{bucket_name}/previews/{asset_id}/preview_{i+1}.{preview_format}"
        previews.append(preview_path)
        
    logger.info("Successfully simulated generation of %s previews for asset %s", num_previews, asset_id, extra={"extra_fields": {"asset_id": asset_id}})
    
    return {"clips": previews}


@app.route("/", methods=["POST"])
def handle_message():
    """
    Cloud Run entry point that processes Pub/Sub messages to generate previews.
    """
    request_json = request.get_json(silent=True)
    if not request_json or 'message' not in request_json:
        logger.error("Invalid Pub/Sub message format: missing 'message' key.")
        return 'Bad Request: invalid Pub/Sub message format', 400

    pubsub_message = request_json['message']
    asset_id = None # Initialize asset_id to handle errors before it's parsed

    try:
        message_data = json.loads(base64.b64decode(pubsub_message['data']).decode('utf-8'))
        asset_id = message_data.get("asset_id")
        file_location = message_data.get("file_location")
        file_name = message_data.get("file_name")
        
        if not all([asset_id, file_location, file_name]):
            logger.error("Message missing required data: asset_id, file_location, or file_name", extra={"extra_fields": {"message_data": message_data}})
            return "Bad Request: missing required data", 400
        
        log_extra = {"extra_fields": {"asset_id": asset_id, "file_name": file_name, "file_location": file_location}}
        logger.info("Processing preview generation request for asset: %s", asset_id, extra=log_extra)
        
        asset_manager.update_asset_metadata(asset_id, "previews", {"status": "processing"})
        # TODO: no processing at this stage
        # preview_results = generate_previews(asset_id, file_location, prompt_config)

        # if preview_results and "clips" in preview_results:
        #     update_data = {"status": "completed", "clips": preview_results["clips"], "error_message": None}
        #     asset_manager.update_asset_metadata(asset_id, "previews", update_data)
        #     logger.info(f"Successfully completed preview generation for asset: {asset_id}", extra=log_extra)
        # else:
        #     update_data = {"status": "failed", "error_message": "Preview generation returned no results."}
        #     asset_manager.update_asset_metadata(asset_id, "previews", update_data)
        #     logger.error(f"Preview generation failed for asset: {asset_id}", extra=log_extra)
        logger.info("Successfully completed preview generation for asset: %s", asset_id, extra=log_extra)
        
        return '', 204
    except Exception as e:
        logger.critical("Unhandled exception during preview generation.", exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
        if asset_id:
            asset_manager.update_asset_metadata(asset_id, "previews", {"status": "failed", "error_message": f"Critical error in service: {str(e)}"})
        return "Error processing message, but acknowledging to prevent retries.", 204







    
