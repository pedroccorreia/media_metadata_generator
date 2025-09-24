import os
import base64
import json
import logging
from flask import Flask, request
from firestore_util import get_firestore_client, get_video_metadata
from video_processor import process_video_from_document_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Flask application
app = Flask(__name__)

@app.route("/", methods=["POST"])
def index():
    """
    Entry point for the Cloud Run service.
    Handles both direct POST requests and Pub/Sub messages.
    """
    message_data = None
    envelope = request.get_json()

    # Check if the request is a Pub/Sub message or a direct call
    if envelope and "message" in envelope:
        # This is likely a Pub/Sub message, decode it
        logging.info("Pub/Sub message format detected. Decoding...")
        try:
            pubsub_message = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
            message_data = json.loads(pubsub_message)
        except Exception as e:
            msg = f"Bad Request: Error decoding Pub/Sub message: {e}"
            logging.error(msg, exc_info=True)
            return msg, 400
    else:
        # This is a direct call, use the request body as the message
        logging.info("Direct POST request detected.")
        message_data = envelope
        
    if not message_data:
        msg = "Bad Request: No valid message data found."
        logging.error(msg)
        return msg, 400
        
    logging.info(f"Received message data: {message_data}")
    doc_id = message_data.get("doc_id")
    collection_name = message_data.get("collection_name")

    if not doc_id or not collection_name:
        msg = "Bad Request: 'doc_id' and 'collection_name' are required."
        logging.error(msg)
        return msg, 400

    # --- Main Business Logic ---
    try:
        logging.info(f"--- Starting video processing for document: {doc_id} ---")
        db = get_firestore_client()
        if not db:
            raise ConnectionError("Could not create Firestore client.")

        video_data = get_video_metadata(db, collection_name, doc_id)
        if not video_data:
            raise FileNotFoundError(f"Document '{doc_id}' not found.")

        process_video_from_document_data(video_data, doc_id)

        logging.info(f"--- Successfully finished processing for document: {doc_id} ---")
        return "Processing complete.", 200

    except Exception as e:
        logging.error(f"An error occurred during video processing for {doc_id}: {e}", exc_info=True)
        # Return a success status so the trigger doesn't retry a failed job
        return f"Internal Server Error: {e}", 200

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT, debug=True)