import os
import json
import base64
import logging
from common.logging_config import configure_logger
from flask import Flask, request
from batch_processor_dispatcher.config import FILE_TYPE_PROMPT_MAP
from google.cloud import pubsub_v1
from common.media_asset_manager import MediaAssetManager



#Logging setup
configure_logger()
# Get a logger instance for this specific module.
# It will inherit the configuration set by configure_logger()
logger = logging.getLogger(__name__) 

# Pub/Sub setup
project_id = os.environ.get("GCP_PROJECT_ID")
publisher = pubsub_v1.PublisherClient()

# MediaAssetManager setup
asset_manager = MediaAssetManager(project_id=project_id)
# Pub/Sub topic names (read from environment variables for flexibility)
SUMMARIES_TOPIC = os.environ.get("PUBSUB_TOPIC_SUMMARIES")
TRANSCRIPTION_TOPIC = os.environ.get("PUBSUB_TOPIC_TRANSCRIPTION")
PREVIEWS_TOPIC = os.environ.get("PUBSUB_TOPIC_PREVIEWS")

# Pre-format the full topic paths for efficiency
TOPIC_PATHS = {
    "summary": publisher.topic_path(project_id, SUMMARIES_TOPIC) if SUMMARIES_TOPIC else None,
    "transcription": publisher.topic_path(project_id, TRANSCRIPTION_TOPIC) if TRANSCRIPTION_TOPIC else None,
    "previews": publisher.topic_path(project_id, PREVIEWS_TOPIC) if PREVIEWS_TOPIC else None,
}


app = Flask(__name__)

def process_file_event(event_data):
    """
    Processes a single file event to dispatch metadata generation tasks.
    """
    file_location = event_data.get("file_location")
    content_type = event_data.get("content_type")
    asset_id = event_data.get("asset_id")
    file_category = event_data.get("file_category")
    public_url = event_data.get("public_url") 

    if not all([file_location, content_type, asset_id, file_category]):
        logger.warning("Skipping invalid message due to missing fields.", extra={"extra_fields": {"event_data": event_data}})
        return

    log_extra = {
        "extra_fields": {
            "asset_id": asset_id,
            "file_category": file_category,
            "content_type": content_type,
            "file_location": file_location,
            "public_url": public_url
        }
    }
    logger.info(f"Received event for asset_id: {asset_id}", extra=log_extra)

    # 1. Create the initial asset record in Firestore using the manager.
    # This sets up the full document structure with 'pending' or 'not_applicable' statuses.
    if not asset_manager.insert_asset(
        asset_id=asset_id,
        file_path=file_location,
        content_type=content_type,
        file_category=file_category,
        public_url=public_url,
    ):
        # The asset_manager already logs the detailed error.
        logger.error(f"Aborting dispatch for asset_id: {asset_id} due to Firestore insertion failure.", extra=log_extra)
        return

    # Get task configurations for this file type from the config map.
    task_configs = FILE_TYPE_PROMPT_MAP.get(file_category, {})

    # 2. Dispatch to Task-Specific Topics
    for task_name, topic_path in TOPIC_PATHS.items():
        task_prompt_config = task_configs.get(task_name)

        # Check if the task is applicable for this file type and the topic is configured
        if task_prompt_config and topic_path:
            message_data = {
                "asset_id": asset_id,
                "file_location": file_location,
                "prompt_config": task_prompt_config
            }
            try:
                future = publisher.publish(topic_path, json.dumps(message_data).encode("utf-8"))
                message_id = future.result()
                logger.info(f"Dispatched {task_name} for {asset_id}.", extra={"extra_fields": {"asset_id": asset_id, "task": task_name, "message_id": message_id}})
                asset_manager.update_asset_metadata(asset_id, task_name, {"status": "dispatched"})
            except Exception as e:
                logger.error(f"Error dispatching {task_name} for {asset_id}", exc_info=True, extra={"extra_fields": {"asset_id": asset_id, "task": task_name}})
                # Update Firestore status to reflect dispatch error
                asset_manager.update_asset_metadata(asset_id, task_name, {
                    "status": "dispatch_failed",
                    "error_message": str(e)
                })
        else:
            # This is an expected outcome, so we log at INFO level.
            # The status is already 'not_applicable' from the insert_asset call, so no need for an explicit update here.
            logger.info(f"Skipping task '{task_name}' for file_category '{file_category}' (not applicable or topic config missing).", extra={"extra_fields": {"asset_id": asset_id, "task": task_name, "file_category": file_category}})


@app.route("/", methods=["POST"])
def handle_message():
    """
    Cloud Run entry point for Pub/Sub push messages.
    """
    request_json = request.get_json(silent=True)
    if not request_json or not 'message' in request_json:
        logger.warning("Invalid Pub/Sub message format. Request missing 'message' key.")
        return 'Bad Request: invalid Pub/Sub message format', 400

    pubsub_message = request_json['message']
    try:
        # The 'data' field is a base64-encoded string.
        # 1. Decode the base64 string to get the raw UTF-8 bytes.
        # 2. Decode the UTF-8 bytes to get the JSON string, then parse it.
        message_data = json.loads(base64.b64decode(pubsub_message['data']).decode('utf-8'))
        process_file_event(message_data)
        return '', 204 # Acknowledge the message
    except Exception as e:
        logger.critical("Overall processing failed for Pub/Sub message.", exc_info=True, extra={"extra_fields": {"pubsub_message": pubsub_message}})
        # Acknowledge the message by returning a success code (204) to Pub/Sub.
        # This prevents the message from being retried, avoiding "poison pill" scenarios
        # where a malformed message could cause an infinite retry loop.
        # For critical errors, a Dead-Letter Queue (DLQ) would be the next step.
        return "Error processing message, but acknowledging to prevent retries.", 204



