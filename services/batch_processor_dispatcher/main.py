import os
import json
import base64
import logging
from common.logging_config import configure_logger
from flask import Flask, request
from google.cloud import pubsub_v1
from common.media_asset_manager import MediaAssetManager



#Logging setup
configure_logger()
# Get a logger instance for this specific module.
# It will inherit the configuration set by configure_logger()
logger = logging.getLogger(__name__) 

# Pub/Sub setup
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
# Pub/Sub topic names (read from environment variables for flexibility)
SUMMARIES_TOPIC = os.environ.get("PUBSUB_TOPIC_SUMMARIES")
TRANSCRIPTION_TOPIC = os.environ.get("PUBSUB_TOPIC_TRANSCRIPTION")
PREVIEWS_TOPIC = os.environ.get("PUBSUB_TOPIC_PREVIEWS")

# --- Configuration Validation ---
# Ensure all required environment variables are set. This prevents the service
# from running in a misconfigured state.
if not all([project_id, SUMMARIES_TOPIC, TRANSCRIPTION_TOPIC, PREVIEWS_TOPIC]):
    missing_vars = [
        var for var, val in {
            "GOOGLE_CLOUD_PROJECT": project_id,
            "PUBSUB_TOPIC_SUMMARIES": SUMMARIES_TOPIC,
            "PUBSUB_TOPIC_TRANSCRIPTION": TRANSCRIPTION_TOPIC,
            "PUBSUB_TOPIC_PREVIEWS": PREVIEWS_TOPIC,
        }.items() if not val
    ]
    # This is a critical configuration error. The service cannot run without these.
    logger.critical("Missing required environment variables: %s. Shutting down.", ', '.join(missing_vars))
    exit(1) # In a container, this will cause it to exit and be restarted.

logger.info("Booting up with the following env variables %s | %s | %s | %s", project_id, SUMMARIES_TOPIC, TRANSCRIPTION_TOPIC, PREVIEWS_TOPIC)

publisher = pubsub_v1.PublisherClient()
# MediaAssetManager setup
asset_manager = MediaAssetManager(project_id=project_id)
# Pre-format the full topic paths for efficiency
TOPIC_PATHS = {
    "summary": publisher.topic_path(project_id, SUMMARIES_TOPIC) if SUMMARIES_TOPIC else None,
    "transcription": publisher.topic_path(project_id, TRANSCRIPTION_TOPIC) if TRANSCRIPTION_TOPIC else None,
    "previews": publisher.topic_path(project_id, PREVIEWS_TOPIC) if PREVIEWS_TOPIC else None,
}

# Defines which tasks are applicable for each file category.
CATEGORY_TASK_MAP = {
    "video": ["summary", "transcription", "previews"],
    "audio": ["summary", "transcription"],
    "document": ["summary"],
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
    file_name = event_data.get("file_name")

    if not all([file_location, content_type, asset_id, file_category, file_name]):
        logger.warning("Skipping invalid message due to missing fields.", extra={"extra_fields": {"event_data": event_data}})
        return

    log_extra = {
        "extra_fields": {
            "asset_id": asset_id,
            "file_name": file_name,
            "file_category": file_category,
            "content_type": content_type,
            "file_location": file_location,
            "public_url": public_url
        }
    }
    logger.info("Received event for asset_id: %s", asset_id, extra=log_extra)

    # 1. Create the initial asset record in Firestore using the manager.
    # This sets up the full document structure with 'pending' or 'not_applicable' statuses.
    if not asset_manager.insert_asset(
        asset_id=asset_id,
        file_path=file_location,
        content_type=content_type,
        file_category=file_category,
        file_name=file_name,
        public_url=public_url,
    ):
        # The asset_manager already logs the detailed error.
        logger.error("Aborting dispatch for asset_id: %s due to Firestore insertion failure.", asset_id, extra=log_extra)
        return

    # 2. Determine which tasks to dispatch based on file category.
    tasks_to_dispatch = CATEGORY_TASK_MAP.get(file_category, [])

    # 3. Dispatch messages for applicable tasks.
    # The message payload is now simpler and the same for all tasks.
    message_data = {
        "asset_id": asset_id,
        "file_location": file_location,
        "file_name": file_name,
    }
    encoded_message = json.dumps(message_data).encode("utf-8")

    for task_name in tasks_to_dispatch:
        topic_path = TOPIC_PATHS.get(task_name)
        if topic_path:
            try:
                future = publisher.publish(topic_path, encoded_message)
                message_id = future.result()
                logger.info("Dispatched %s for %s.", task_name, asset_id, extra={"extra_fields": {"asset_id": asset_id, "task": task_name, "message_id": message_id}})
                asset_manager.update_asset_metadata(asset_id, task_name, {"status": "dispatched"})
            except Exception as e:
                logger.error("Error dispatching %s for %s", task_name, asset_id, exc_info=True, extra={"extra_fields": {"asset_id": asset_id, "task": task_name}})
                # Update Firestore status to reflect dispatch error
                asset_manager.update_asset_metadata(
                    asset_id, task_name, {"status": "dispatch_failed", "error_message": str(e)}
                )
        else:
            logger.warning("Skipping task '%s' because its topic is not configured.", task_name, extra={"extra_fields": {"asset_id": asset_id, "task": task_name}})
            asset_manager.update_asset_metadata(
                asset_id, task_name, {"status": "not_applicable", "error_message": "Topic not configured in dispatcher."}
            )

    # 4. Mark non-dispatched tasks as 'not_applicable'.
    # This corrects the initial 'pending' status set by insert_asset for tasks
    # that don't apply to this file type (e.g., previews for audio).
    all_possible_tasks = set(TOPIC_PATHS.keys())
    dispatched_tasks = set(tasks_to_dispatch)
    skipped_tasks = all_possible_tasks - dispatched_tasks

    for task_name in skipped_tasks:
        logger.info("Marking task '%s' as not_applicable for file_category '%s'.", task_name, file_category, extra={"extra_fields": {"asset_id": asset_id, "task": task_name}})
        asset_manager.update_asset_metadata(asset_id, task_name, {"status": "not_applicable"})


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
    except Exception:
        logger.critical("Overall processing failed for Pub/Sub message.", exc_info=True, extra={"extra_fields": {"pubsub_message": pubsub_message}})
        # Acknowledge the message by returning a success code (204) to Pub/Sub.
        # This prevents the message from being retried, avoiding "poison pill" scenarios
        # where a malformed message could cause an infinite retry loop.
        # For critical errors, a Dead-Letter Queue (DLQ) would be the next step.
        return "Error processing message, but acknowledging to prevent retries.", 204
