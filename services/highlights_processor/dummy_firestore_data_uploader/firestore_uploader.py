import json
import logging
from google.cloud import firestore
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def upload_single_json_to_firestore(json_file_path: str, collection_name: str, document_id: str, project_id: str = None):
    """
    Reads a JSON file containing a single object and uploads it as one
    document to a specified Firestore collection.

    Args:
        json_file_path (str): The local path to the JSON file.
        collection_name (str): The name of the Firestore collection to upload to.
        document_id (str): The ID to use for the new document in Firestore.
        project_id (str, optional): Your Google Cloud project ID. Defaults to None,
                                     in which case the client library tries to find it
                                     from the environment.
    """
    try:
        # Initialize the Firestore client
        db = firestore.Client(project=project_id)
        logging.info(f"Successfully connected to Firestore project: {db.project}")

        # Open and load the JSON file
        with open(json_file_path, 'r') as f:
            doc_data = json.load(f)
        
        if not isinstance(doc_data, dict):
            logging.error("Error: JSON file must contain a single dictionary (object).")
            return

        logging.info(f"Preparing to upload data to document '{document_id}' in collection '{collection_name}'.")

        # Get a reference to the document and set its data
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.set(doc_data)
        
        logging.info(f"Successfully uploaded document: {document_id}")

    except FileNotFoundError:
        logging.error(f"Error: The file '{json_file_path}' was not found.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == '__main__':
    # --- CONFIGURATION ---
    # 1. Replace with your actual GCP project ID
    #    You can also set this via the GOOGLE_CLOUD_PROJECT environment variable
    GCP_PROJECT_ID = "Your Project HERE"
    
    # 2. The path to your new JSON file
    JSON_FILE = "video_data_file.json"
    
    # 3. The name you want for your Firestore collection
    COLLECTION_NAME = "highlights-demo-test" 
    
    # 4. The unique ID for this video document in Firestore
    DOCUMENT_ID = "sbs-news-broadcast-01"
    
    # --- RUN THE UPLOAD ---
    upload_single_json_to_firestore(
        json_file_path=JSON_FILE, 
        collection_name=COLLECTION_NAME, 
        document_id=DOCUMENT_ID, 
        project_id=GCP_PROJECT_ID
    )