import logging
from google.cloud import firestore
import google.auth

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_firestore_client():
    """
    Initializes and returns a Firestore client, explicitly finding the project ID.
    """
    try:
     
        # Manually set your project ID here for local debugging.
        project_id = "Your Project ID here" 

        if not project_id:
            credentials, project_id = google.auth.default()

        if not project_id:
             logging.error("GCP Project ID could not be determined. Please set it manually.")
             return None

        db = firestore.Client(project=project_id)
        logging.info(f"Successfully connected to Firestore project: {project_id}")
        return db
    except Exception as e:
        logging.error(f"Failed to create Firestore client: {e}", exc_info=True)
        return None

def get_video_metadata(db: firestore.Client, collection_name: str, document_id: str) -> dict:
    """
    Fetches a specific document from a given collection in Firestore.
    """
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            logging.info(f"Successfully fetched document '{document_id}' from collection '{collection_name}'.")
            return doc.to_dict()
        else:
            logging.error(f"Document '{document_id}' not found in collection '{collection_name}'.")
            return None
    except Exception as e:
        logging.error(f"An error occurred while fetching document '{document_id}': {e}", exc_info=True)
        return None