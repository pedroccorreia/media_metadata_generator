import os
import json
import base64
import logging
from typing import Union
from flask import Flask, request

from google import genai
from google.genai import types

from common.media_asset_manager import MediaAssetManager
from common.logging_config import configure_logger

from .structured_output_schema import SHORTS_SCHEMA


# Configure logger for the service
configure_logger()
logger = logging.getLogger(__name__)

# Initialize clients
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
asset_manager = MediaAssetManager(project_id=project_id)

# Initialize Flask app
app = Flask(__name__)


def generate(
    prompt_text,
    video_uri,
    system_instruction_text,
    response_schema,
    model_name="gemini-2.5-pro") -> str:
    """"
    Common function that will execute the prompts as per the inputs and return the 
    result of the prompt
    Args:
        prompt_text (str): The text prompt for the model.
        video_uri (str): The GCS URI of the video file (e.g., "gs://your-bucket/your-video.mp4").
        system_instruction_text (str): The system instruction for the model.
        model_name (str): The name of the generative model to use (default: "gemini-2.5-pro").
    Returns:
        str: The generated text response from the model.

    """
    client = genai.Client(
        vertexai=True,
        project="fox-metadata-468100",
        location="global",
    )

    msg1_text1 = types.Part.from_text(text=prompt_text)

    msg1_video1 = types.Part.from_uri(
        file_uri=video_uri,
        mime_type="video/*",
    )

    si_text1 = system_instruction_text

    contents = [
        types.Content(
        role="user",
        parts=[
            msg1_text1,
            msg1_video1
        ]
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature = 1,
        top_p = 1,
        seed = 0,
        max_output_tokens = 65535,
        response_mime_type="application/json",
        response_schema=response_schema,
        safety_settings = [types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="OFF"
        ),types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="OFF"
        )],
        system_instruction=[types.Part.from_text(text=si_text1)],
        thinking_config=types.ThinkingConfig(
        thinking_budget=-1,
        ),
    )

    response = client.models.generate_content(
        model = model_name,
        contents = contents,
        config = generate_content_config,
    )

    return response.text


def generate_previews(asset_id: str, file_location: str) -> Union[list, dict]:
    """
    Generates a list of potential short video clips from a media asset using Gemini.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file (e.g., gs://bucket/path/to/file.mp4).

    Returns:
        Union[list, dict]: A list of preview clips on success, or a dictionary with an 'error' key on failure.
    """
    # Initialize raw_response to ensure it's available for the exception block
    raw_response = ""
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
    logger.info("Processing preview generation for asset: %s", asset_id, extra={"extra_fields": {"asset_id": asset_id, "file_location": file_location}})

    try:
        system_instructions_text = """
        You are helping an entertainment company create shorts out of their entertainment titles. 
        You are able to identify the scenes that would make users see the full title."""
        prompt = """
        Give me five key scenes that would work as a trailer for the content. 
        Minimum scene duration should be 30 seconds.
        No spoilers should be included. No results should be shown on screen.
        """
        model = "gemini-2.5-flash"
        raw_response = generate(prompt, file_location, system_instructions_text, SHORTS_SCHEMA, model_name=model)
        shorts_data = json.loads(raw_response)

        logger.info("Successfully generated previews for asset %s", asset_id, extra=log_extra)
        return shorts_data

    except json.JSONDecodeError:
        logger.error(
            "Failed to decode JSON for previews on asset %s. Raw response: %s",
            asset_id,
            raw_response,
            exc_info=True,
            extra=log_extra
        )
        return {"error": f"Malformed JSON response from model: {raw_response}"}
    except Exception as e:
        logger.error("Failed to generate previews for asset %s", asset_id, exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
        return { "error": f"Failed to generate previews: {str(e)}" }


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
        preview_results = generate_previews(asset_id, file_location)

        # A successful response is a list of clips, while an error is a dict.
        if isinstance(preview_results, dict) and "error" in preview_results:
            preview_error = preview_results["error"]
            update_data = {"status": "failed", "error_message": preview_error}
            asset_manager.update_asset_metadata(asset_id, "previews", update_data)
            logger.error("Preview generation failed for asset %s: %s", asset_id, preview_error, extra=log_extra)
        elif isinstance(preview_results, list):
            # The successful result is a list of clips, which we store in the 'clips' field.
            update_data = {"status": "completed", "clips": preview_results, "error_message": None}
            asset_manager.update_asset_metadata(asset_id, "previews", update_data)
            logger.info("Successfully completed preview generation for asset: %s", asset_id, extra=log_extra)
        else:
            # This case handles an unexpected return type from the generation function.
            error_msg = f"Unexpected response format from generate_previews: {preview_results}"
            update_data = {"status": "failed", "error_message": error_msg}
            asset_manager.update_asset_metadata(asset_id, "previews", update_data)
            logger.error("Preview generation failed for asset %s: %s", asset_id, error_msg, extra=log_extra)
        
        return '', 204
    except Exception as e:
        logger.critical("Unhandled exception during preview generation.", exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
        if asset_id:
            asset_manager.update_asset_metadata(asset_id, "previews", {"status": "failed", "error_message": f"Critical error in service: {str(e)}"})
        return "Error processing message, but acknowledging to prevent retries.", 204







    
