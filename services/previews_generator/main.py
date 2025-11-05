"""Service for the creation of the metadata related to previews - i,e: shorts"""

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


# Highlight Generation service Imports
import tempfile
import moviepy as mp
from google.cloud import storage
from google.cloud import firestore

from .firestore_util import get_video_metadata
from .final_highlight_gen import analyze_video_overview, initialize_vertex_client,create_highlight_reel



# Configure logger for the service
configure_logger()
logger = logging.getLogger(__name__)

# Initialize clients
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
asset_manager = MediaAssetManager(project_id=project_id)
llm_model = os.environ.get("LLM_MODEL", "gemini-1.5-flash")

storage_client = storage.Client()
firestore_client = firestore.Client()

# Initialize Flask app
app = Flask(__name__)


def generate(
    prompt_text,
    video_uri,
    source,
    system_instruction_text,
    response_schema,
    model_name=llm_model,
) -> str:
    """ "
    Invokes a generative AI model with a video and text prompt to generate structured data.

    Args:
        prompt_text (str): The text prompt for the model.
        video_uri (str): The GCS URI of the video file (e.g., "gs://your-bucket/your-video.mp4").
        source (str): The source of the video, e.g., "GCS" or "youtube".
        system_instruction_text (str): The system instruction for the model.
        response_schema (dict): The schema for the expected JSON output.
        model_name (str): The name of the generative model to use (default: "gemini-2.5-pro").

    Returns:
        str: The generated JSON string response from the model.

    """
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location="global",
    )

    # Prepare the user prompt parts: one for the text instruction and one for the video file.
    msg1_text1 = types.Part.from_text(text=prompt_text)
    msg1_video1 = types.Part.from_uri(
       file_uri=video_uri,
        mime_type="video/youtube" if source == "youtube" else "video/*",
    )
    msg1_video1 = types.Part.from_uri(
       file_uri=video_uri,
        mime_type="video/*",
    )

    # The system instruction guides the model's behavior and persona.
    si_text1 = system_instruction_text

    # Combine the parts into a single user content block.
    contents = [
        types.Content(role="user", parts=[msg1_text1, msg1_video1]),
    ]

    # Configure the generation settings for the model.
    generate_content_config = types.GenerateContentConfig(
        # Model creativity and determinism settings.
        temperature=1,
        top_p=1,
        seed=0,
        # Enforce JSON output according to the provided schema.
        max_output_tokens=65535,
        response_mime_type="application/json",
        response_schema=response_schema,
        # Disable safety filters to allow processing of a wide range of content.
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
        # Set the system-level instructions for the model.
        system_instruction=[types.Part.from_text(text=si_text1)],
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1,
        ),
    )

    # Send the request to the generative model.
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=generate_content_config,
    )

    return response.text


def generate_previews(asset_id: str, file_location: str, source: str) -> Union[list, dict]:
    """
    Generates a list of potential short video clips from a media asset using Gemini.

    Args:
        asset_id (str): The ID of the asset.
        file_location (str): GCS URI of the media file (e.g., gs://bucket/path/to/file.mp4).

    Returns:
        Union[list, dict]: A list of preview clips on success, 
        or a dictionary with an 'error' key on failure.
    """
    # Initialize raw_response to ensure it's available for the exception block
    raw_response = ""
    log_extra = {"extra_fields": {"asset_id": asset_id, "file_location": file_location}}
    logger.info(
        "Processing preview generation for asset: %s",
        asset_id,
        extra={"extra_fields": {"asset_id": asset_id, "file_location": file_location}},
    )

    

    try:
        # Define the system instructions and user prompt for the model.
        system_instructions_text = """
        You are helping an entertainment company create shorts out of their entertainment titles. 
        You are able to identify the scenes that would make users see the full title."""
        prompt = """
        Give me five key scenes that would work as a trailer for the content. 
        Minimum scene duration should be 30 seconds.
        No spoilers should be included. No results should be shown on screen.
        """
        raw_response = generate(
            prompt,
            file_location,
            source,
            system_instructions_text,
            SHORTS_SCHEMA,
            model_name=llm_model,
        )
        # Parse the JSON string response into a Python list.
        shorts_data = json.loads(raw_response)

        logger.info(
            "Successfully generated previews for asset %s", asset_id, extra=log_extra
        )
        return shorts_data

    except json.JSONDecodeError:
        # Handle cases where the model's output is not valid JSON.
        logger.error(
            "Failed to decode JSON for previews on asset %s. Raw response: %s",
            asset_id,
            raw_response,
            exc_info=True,
            extra=log_extra,
        )
        return {"error": f"Malformed JSON response from model: {raw_response}"}
    except Exception as e:
        # Catch any other exceptions during the generation process.
        logger.error(
            "Failed to generate previews for asset %s",
            asset_id,
            exc_info=True,
            extra={"extra_fields": {"asset_id": asset_id}},
        )
        return {"error": f"Failed to generate previews: {str(e)}"}

def create_video_metadata(bucket_name, source_blob_name,collection_name):
    """
    Downloads a video from a GCS bucket, extracts its duration,
    ,stores the metadata in a Firestore document
    and returns the document ID.

    Args:
        bucket_name (str): The name of the GCS bucket.
        source_blob_name (str): The full path to the video object in the bucket.
        collection_name (str): The Firestore collection name to store the metadata.
    """
    
    # 1. Download the video to a temporary local file.
    # We use a temporary file to avoid cluttering the system and
    # ensure it's deleted automatically.
    
    # Create a temporary file with a .mp4 extension for moviepy to recognize it.
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_file_path = temp_file.name
    temp_file.close()

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        #local_path = os.path.join(temp_dir, os.path.basename(blob_name))
        
        print(f"Downloading {source_blob_name} from bucket {bucket_name} to {temp_file_path}...")
        blob.download_to_filename(temp_file_path)
        print("Download complete.")

        # 2. Use moviepy to get the video metadata.
        # This is a much more efficient and reliable method for technical metadata
        # like duration, as opposed to a large language model.
        try:
            video_clip = mp.VideoFileClip(temp_file_path)
            duration_seconds = video_clip.duration
            print(f"Video duration: {duration_seconds} seconds")
            
            # Close the video clip to release the file handle
            video_clip.close()

        except Exception as e:
            print(f"Error processing video with moviepy: {e}")
            return

        # 3. Store the metadata in a Firestore document.
        # The document will be created in the 'video_metadata' collection.
        metadata = {
            #'video_path': f"gs://{bucket_name}/{source_blob_name}",
            'duration_seconds': duration_seconds,
            'timestamp': firestore.SERVER_TIMESTAMP
        }

        doc_ref = firestore_client.collection('video_metadata').add(metadata)
        print(f"Metadata for {source_blob_name} stored in Firestore with ID: {doc_ref[1].id}")
        return doc_ref[1].id

    finally:
        # Clean up the temporary file, regardless of success or failure.
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"Cleaned up temporary file: {temp_file_path}")

@app.route("/", methods=["POST"])
def handle_message():
    """
    Cloud Run entry point that processes Pub/Sub messages to generate previews.
    """
    # Safely get the JSON payload from the request.
    request_json = request.get_json(silent=True)
    if not request_json or "message" not in request_json:
        logger.error("Invalid Pub/Sub message format: missing 'message' key.")
        return "Bad Request: invalid Pub/Sub message format", 400

    # The actual message is nested and base64-encoded within the Pub/Sub payload.
    pubsub_message = request_json["message"]
    asset_id = None  # Initialize asset_id to handle errors before it's parsed

    try:
        # Decode and parse the message data.
        message_data = json.loads(
            base64.b64decode(pubsub_message["data"]).decode("utf-8")
        )
        asset_id = message_data.get("asset_id")
        file_location = message_data.get("file_location")
        file_name = message_data.get("file_name")
        source = message_data.get("source", "GCS")

        
        #log all input params
        logger.info(
            "Processing preview generation request for asset: %s | file_name: %s | file_location: %s message_data %s",
            asset_id,
            file_name,
            file_location,
            message_data
        )
        
        # Validate that all required fields are present in the message.
        if not all([asset_id, file_location, file_name, source]):
            logger.error(
                "Message missing required data: asset_id, file_location, or file_name",
                extra={"extra_fields": {"message_data": message_data}},
            )
            return "Bad Request: missing required data", 400

        log_extra = {
            "extra_fields": {
                "asset_id": asset_id,
                "file_name": file_name,
                "file_location": file_location,
            }
        }
        logger.info(
            "Processing preview generation request for asset: %s",
            asset_id,
            extra=log_extra,
        )

        # Update the asset's status to 'processing' in Firestore.
        asset_manager.update_asset_metadata(
            asset_id, "previews", {"status": "processing"}
        )
        # Trigger the core logic to generate preview clips.
        preview_results = generate_previews(asset_id, file_location, source)

        #### Trigger the core logic to generate highlights only do this if source != 'youtube'
        # video_file_name= file_name +".mp4"
        # bucket_name=file_location.split("/")[2] 
        # collection_name = message_data.get("collection_name")
        # #Creating the new Metadata entry in Firestore for highlights
        # doc_id=create_video_metadata(bucket_name, video_file_name,collection_name)

        # #Feching of created new Metadata entry from Firestore
        # Document_data=get_video_metadata(firestore_client, collection_name, doc_id)
        # print(f"Fetched metadata from Firestore document ID: {doc_id}")
        # print(f"Document data: {Document_data}")

        # duration=Document_data['duration_seconds']
        # model_id=llm_model

        # print(f"Creating Highlight Reel... for {file_name}")
        # create_highlight_reel(file_location,duration,model_id)



        # A successful response is a list of clips, while an error is a dict.
        if isinstance(preview_results, dict) and "error" in preview_results:
            preview_error = preview_results["error"]
            update_data = {"status": "failed", "error_message": preview_error}
            asset_manager.update_asset_metadata(asset_id, "previews", update_data)
            logger.error(
                "Preview generation failed for asset %s: %s",
                asset_id,
                preview_error,
                extra=log_extra,
            )
        elif isinstance(preview_results, list):
            # The successful result is a list of clips, which we store in the 'clips' field.
            update_data = {
                "status": "completed",
                "clips": preview_results,
                "error_message": None,
            }
            asset_manager.update_asset_metadata(asset_id, "previews", update_data)
            logger.info(
                "Successfully completed preview generation for asset: %s",
                asset_id,
                extra=log_extra,
            )
        else:
            # This case handles an unexpected return type from the generation function.
            error_msg = (
                f"Unexpected response format from generate_previews: {preview_results}"
            )
            update_data = {"status": "failed", "error_message": error_msg}
            asset_manager.update_asset_metadata(asset_id, "previews", update_data)
            logger.error(
                "Preview generation failed for asset %s: %s",
                asset_id,
                error_msg,
                extra=log_extra,
            )

        return "", 204
    except Exception as e:
        # This is a critical failure block for any unhandled exceptions in the process.
        # It logs the error and updates Firestore to prevent the asset from being stuck in 'processing'.
        logger.critical(
            "Unhandled exception during preview generation.",
            exc_info=True,
            extra={"extra_fields": {"asset_id": asset_id}},
        )
        if asset_id:
            asset_manager.update_asset_metadata(
                asset_id,
                "previews",
                {
                    "status": "failed",
                    "error_message": f"Critical error in service: {str(e)}",
                },
            )
        # Return a 204 status to acknowledge the Pub/Sub message and prevent retries,
        # even though an error occurred. This is a common pattern for non-recoverable errors.
        return "Error processing message, but acknowledging to prevent retries.", 204