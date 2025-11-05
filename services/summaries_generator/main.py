"""Service for the creation of metadata for videos. Includes, summaries and key moments"""

import os
import json
import base64
import logging


from google import genai
from google.genai import types

from flask import Flask, request

from common.media_asset_manager import MediaAssetManager
from common.logging_config import configure_logger
from .structured_output_schema import (
    SUMMARY_SCHEMA,
    KEY_SECTIONS_SCHEMA,
    ASSET_CATEGORIZATION_SCHEMA,
)

# Configure logger for the service
configure_logger()
logger = logging.getLogger(__name__)

# Initialize clients and Flask app
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
# A location must be specified for Vertex AI
location = os.environ.get("GCP_REGION", "us-central1")
asset_manager = MediaAssetManager(project_id=project_id)

app = Flask(__name__)


def generate(
    prompt_text,
    video_uri,
    source,
    system_instruction_text,
    response_schema,
    model_name="gemini-2.5-pro",
) -> str:
    """ "
    Common function that will execute the prompts as per the inputs and return the
    result of the prompt
    Args:
        prompt_text (str): The text prompt for the model.
        video_uri (str): The GCS URI of the video file (e.g., "gs://your-bucket/your-video.mp4").
        source (str): The source of the video, e.g., "GCS" or "youtube".
        system_instruction_text (str): The system instruction for the model.
        model_name (str): The name of the generative model to use (default: "gemini-2.5-pro").
    Returns:
        str: The generated text response from the model.

    """
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location="global",
    )

    msg1_text1 = types.Part.from_text(text=prompt_text)

    if source == "youtube":
        msg1_video1 = types.Part.from_uri(
            file_uri=video_uri, mime_type="video/youtube"
        )
    else:  # Default to GCS
        msg1_video1 = types.Part.from_uri(
            file_uri=video_uri, mime_type="video/*"
        )

    si_text1 = system_instruction_text

    contents = [
        types.Content(role="user", parts=[msg1_text1, msg1_video1]),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=1,
        seed=0,
        max_output_tokens=65535,
        response_mime_type="application/json",
        response_schema=response_schema,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        system_instruction=[types.Part.from_text(text=si_text1)],
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1,
        ),
    )

    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=generate_content_config,
    )

    return response.text


def generate_summary(asset_id: str, file_location: str, source: str) -> dict:
    """
    Generates a summary for a media asset using GenAI models.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file.
    Returns:
        source (str): The source of the media file (e.g., "GCS", "youtube").
        dict: A dictionary containing the result of the summary prompt,
              or an error dictionary if generation fails.
    """
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
    logger.info("Generating summary for asset: %s", asset_id, extra=log_extra)
    raw_response = ""
    try:
        system_instructions_text = """
         You are a skilled video analysis expert. 
         You have a deep understanding of media. 
         Your task is to analyze the provided video and extract key information. """
        prompt = """
            Please analyze the following video and provide summary, itemized_summary and subject_topics.
            Avoid any additional comment or text.
        """
        model = "gemini-2.5-flash"
        raw_response = generate(
            prompt,
            file_location,
            source,
            system_instructions_text,
            SUMMARY_SCHEMA,
            model_name=model,
        )
        summary_data = json.loads(raw_response)

        logger.info(
            "Successfully generated summary text for asset %s",
            asset_id,
            extra=log_extra,
        )
        return summary_data
    except json.JSONDecodeError:
        logger.error(
            "Failed to decode JSON for summary on asset %s. Raw response: %s",
            asset_id,
            raw_response,
            exc_info=True,
            extra=log_extra,
        )
        return {"error": f"Malformed JSON response from model: {raw_response}"}
    except Exception as e:
        logger.error(
            "Failed to generate summary/chapters for asset %s",
            asset_id,
            exc_info=True,
            extra=log_extra,
        )
        return {"error": f"Failed to process with Gemini: {str(e)}"}


def generate_key_sections(asset_id: str, file_location: str, source: str) -> dict:
    """
    Generates key sections for a media asset using GenAI models.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file.
    Returns:
        source (str): The source of the media file (e.g., "GCS", "youtube").
        dict: A dictionary containing the result of the key sections prompt,
              or an error dictionary if generation fails.
    """
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
    logger.info("Generating key sections for asset: %s", asset_id, extra=log_extra)
    raw_response = ""
    try:
        # Define key section prompt
        prompt_content = """
            Please analyze the following video and provide a list of all the  clips with their type and timestamps. 
            Also explain the reason why the selection of that particular timestamp has been made. 
            Please format your response as a JSON object with the given structure. 
            Make sure the audio is not truncated while suggesting the clips. 
            Avoid any additional comment or text.
            Please make sure the timestamps are accurate and reflect the precise start and end of each clip.
            """
        # Establish system instructions
        system_instruction_text = """
            You are a skilled video analysis expert. 
            You have a deep understanding of media and can accurately identify key moments in a video. 
            Your task is to analyze the provided video and extract all the moments clips. 
            For each clip, you need to classify the type of moment and provide the precise start and end timestamps. """
        # Define a specific model so that the default one is not used
        model_name = "gemini-2.5-pro"
        # retrieve the result
        raw_response = generate(
            prompt_content,
            file_location,
            source,
            system_instruction_text,
            KEY_SECTIONS_SCHEMA,
            model_name=model_name,
        )
        key_sections_data = json.loads(raw_response)

        logger.info(
            "Successfully generated key sections for asset %s",
            asset_id,
            extra=log_extra,
        )
        return key_sections_data
    except json.JSONDecodeError:
        logger.error(
            "Failed to decode JSON for key sections on asset %s. Raw response: %s",
            asset_id,
            raw_response,
            exc_info=True,
            extra=log_extra,
        )
        return {"error": f"Malformed JSON response from model: {raw_response}"}
    except Exception as e:
        logger.error(
            "Failed to generate key sections for asset %s",
            asset_id,
            exc_info=True,
            extra=log_extra,
        )
        return {"error": f"Failed to process with Gemini: {str(e)}"}


def generate_asset_categorization(
    asset_id: str, file_location: str, source: str
) -> dict:
    """
    Generates Detailed Categorization for a media asset using GenAI models.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file.
    Returns:
        source (str): The source of the media file (e.g., "GCS", "youtube").
        dict: A dictionary containing the result of the categorizations prompt,
              or an error dictionary if generation fails.
    """
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
    logger.info(
        "Generating detailed categorization for asset: %s", asset_id, extra=log_extra
    )
    raw_response = ""
    try:
        # Define key section prompt
        prompt_content = """
        Create a detailed categorization of the movie or series title.

        The categories and their content are are follows:

        Character
        This item should list the various roles of people within the story, such as victims, suspects, law enforcement, and witnesses. Each role should be clearly defined to understand their function in the narrative.

        Concept
        This should describe the core idea or the foundation of the story, indicating whether it's an original creation or based on existing material.

        Scenario
        This section should outline the main plot points and the overall structure of the story, including the central problem to be solved and the genre elements like mystery or intrigue.

        Setting
        This item should detail the time and location of the story, including both the general environment (e.g., small town, city) and specific places where key events occur. It should also specify the time period, such as the decade or century.

        Subject
        This section should define the primary topic and themes of the story, such as the type of crime or the lifestyle depicted.

        Practice
        This item should describe the procedural and professional elements of the story, such as the legal, investigative, or judicial processes that are central to the plot.

        Theme
        This should list the abstract concepts and ideas explored in the narrative, such as justice, conflict, morality, and human nature.

        Video Mood
        This section should describe the intended emotional and atmospheric tone of the story, using adjectives to convey the viewing experience, such as suspenseful, chilling, or powerful.

        Do not have verbose description. Use single words when adding items to the result."""
        # Establish system instructions
        system_instruction_text = """
            You are a skilled video analysis expert. 
            You have a deep understanding of media and can accurately identify key moments in a video. 
            Your task is to analyze the provided video and extract all the moments clips. 
            For each clip, you need to classify the type of moment and provide the precise start and end timestamps. """
        # Define a specific model so that the default one is not used
        model_name = "gemini-2.5-flash"
        # retrieve the result
        raw_response = generate(
            prompt_content,
            file_location,
            source,
            system_instruction_text,
            ASSET_CATEGORIZATION_SCHEMA,
            model_name=model_name,
        )
        detailed_categorization_data = json.loads(raw_response)

        logger.info(
            "Successfully generated detailed categorization for asset %s",
            asset_id,
            extra=log_extra,
        )
        return detailed_categorization_data
    except json.JSONDecodeError:
        logger.error(
            "Failed to decode JSON for detail categorization on asset %s. Raw response: %s",
            asset_id,
            raw_response,
            exc_info=True,
            extra=log_extra,
        )
        return {"error": f"Malformed JSON response from model: {raw_response}"}
    except Exception as e:
        logger.error(
            "Failed to generate detail categorization for asset %s",
            asset_id,
            exc_info=True,
            extra=log_extra,
        )
        return {"error": f"Failed to process with Gemini: {str(e)}"}


@app.route("/", methods=["POST"])
def handle_message():
    """
    Cloud Run entry point that processes Pub/Sub messages to generate summaries.
    """

    # Checks if message is in the post input
    request_json = request.get_json(silent=True)
    if not request_json or "message" not in request_json:
        logger.error("Invalid Pub/Sub message format: missing 'message' key.")
        return "Bad Request: invalid Pub/Sub message format", 400

    pubsub_message = request_json["message"]
    asset_id = None  # Initialize asset_id for error logging

    try:
        # Extract basic information from message
        message_data = json.loads(
            base64.b64decode(pubsub_message["data"]).decode("utf-8")
        )
        asset_id = message_data.get("asset_id")
        file_location = message_data.get("file_location")
        file_name = message_data.get("file_name")
        source = message_data.get("source", "GCS")

        if not all([asset_id, file_location, file_name, source]):
            logger.error(
                "Message missing required data: asset_id, file_location, file_name, or source.",
                extra={"extra_fields": {"message_data": message_data}},
            )
            return "Bad Request: missing required data", 400

        log_extra = {
            "extra_fields": {
                "asset_id": asset_id,
                "file_name": file_name,
                "file_location": file_location,
                "source": source,
            }
        }
        logger.info(
            "Processing summary generation request for asset: %s",
            asset_id,
            extra=log_extra,
        )
        # Fetch asset details from Firestore to get file_category and content_type
        asset_data = asset_manager.get_asset(asset_id)
        if not asset_data:
            logger.error(
                "Asset %s not found in Firestore. Aborting.", asset_id, extra=log_extra
            )
            # Acknowledge to prevent retries for a non-existent asset
            return "", 204

        file_category = asset_data.get("file_category")
        content_type = asset_data.get("content_type")

        if not all([file_category, content_type]):
            error_msg = "Asset document in Firestore is missing 'file_category' or 'content_type'."
            logger.error(error_msg, extra=log_extra)
            asset_manager.update_asset_metadata(
                asset_id, "summary", {"status": "failed", "error_message": error_msg}
            )
            return "", 204

        asset_manager.update_asset_metadata(
            asset_id, "summary", {"status": "processing"}
        )

        # Generate both summary from asset
        summary_results = generate_summary(asset_id, file_location, source)
        # Obtains key sections
        key_sections_results = generate_key_sections(asset_id, file_location, source)
        # Obtains detailed categorization
        detailed_categorization_results = generate_asset_categorization(
            asset_id, file_location, source
        )

        # --- Consolidate results and handle partial failures ---
        combined_results = {}
        error_messages = []

        summary_error = summary_results.get("error")
        sections_error = key_sections_results.get("error")
        categorization_error = detailed_categorization_results.get("error")

        if summary_error:
            error_messages.append(f"SummaryError: {summary_error}")
            logger.warning(
                "Summary generation failed for asset %s: %s",
                asset_id,
                summary_error,
                extra=log_extra,
            )
        else:
            combined_results.update(summary_results)
            logger.info(
                "Successfully generated summary for asset %s", asset_id, extra=log_extra
            )

        if sections_error:
            error_messages.append(f"KeySectionsError: {sections_error}")
            logger.warning(
                "Key sections generation failed for asset %s : %s",
                asset_id,
                sections_error,
                extra=log_extra,
            )
        else:
            combined_results.update(key_sections_results)
            logger.info(
                "Successfully generated key sections for asset %s",
                asset_id,
                extra=log_extra,
            )

        if categorization_error:
            error_messages.append(f"CategorizationError: {categorization_error}")
            logger.warning(
                "Detailed categorization failed for asset %s : %s",
                asset_id,
                categorization_error,
                extra=log_extra,
            )
        else:
            combined_results.update(detailed_categorization_results)
            logger.info(
                "Successfully generated detailed categorization for asset %s",
                asset_id,
                extra=log_extra,
            )

        if error_messages:
            status = "partial_success" if combined_results else "failed"
            combined_error_message = " | ".join(error_messages)
            update_data = {
                "status": status,
                **combined_results,
                "error_message": combined_error_message,
            }
            logger.error(
                "Summary/sections/categorization generation for asset %s completed with status '%s'. Errors: %s",
                asset_id,
                status,
                combined_error_message,
                extra=log_extra,
            )
        else:
            update_data = {
                "status": "completed",
                **combined_results,
                "error_message": None,
            }
            logger.info(
                "Successfully completed summary, key sections, and categorization generation for asset: %s",
                asset_id,
                extra=log_extra,
            )

        asset_manager.update_asset_metadata(asset_id, "summary", update_data)

        return "", 204
    except Exception as e:
        logger.critical(
            "Unhandled exception during summary generation.",
            exc_info=True,
            extra={"extra_fields": {"asset_id": asset_id}},
        )
        if asset_id:
            asset_manager.update_asset_metadata(
                asset_id,
                "summary",
                {
                    "status": "failed",
                    "error_message": f"Critical error in service: {str(e)}",
                },
            )
        return "Error processing message, but acknowledging to prevent retries.", 204
