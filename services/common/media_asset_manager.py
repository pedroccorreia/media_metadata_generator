""" Service for handling document storage """
import logging
from typing import Optional

from google.cloud import firestore

# Get a logger instance for this module.
# It will inherit the configuration from the root logger in the service entry point.
logger = logging.getLogger(__name__)
# Assume __app_id is globally available in the Cloud Run environment
# For local testing, you might need to set it:
# __app_id = "your-default-app-id"
class MediaAssetManager:
    """
    Manages media asset metadata in Firestore, supporting read, insert, and update operations.
    The schema is designed for a single 'media_assets' collection with flexible documents.
    """

    def __init__(self, project_id: str):
        """
        Initializes the Firestore client and sets the base collection path.

        Args:
            project_id (str): Your Google Cloud project ID.
        """
        self.db = firestore.Client(project=project_id)
        # The root collection for all media assets.
        self.collection_path = "media_assets"
        self.media_assets_collection = self.db.collection(self.collection_path)
        logger.info("Initialized MediaAssetManager for collection: %s", self.collection_path)

    def _get_doc_ref(self, asset_id: str) -> firestore.DocumentReference:
        """
        Helper method to get a Firestore DocumentReference for a given asset_id.

        Args:
            asset_id (str): The unique ID of the media asset.

        Returns:
            firestore.DocumentReference: The reference to the asset's document.
        """
        return self.media_assets_collection.document(asset_id)

    def insert_asset(
        self,
        asset_id: str,
        file_path: str,
        content_type: str,
        file_category: str,
        file_name: str,
        public_url: Optional[str] = None,
        source: str = "GCS",
        poster_url: str = "https://placehold.co/1280x720/000000/FFFFFF?text=Default+Poster",
        is_dummy: bool = False
    ) -> bool:
        """
        Inserts a new media asset document into Firestore with initial 'pending' statuses.

        Args:
            asset_id (str): Unique ID for the new asset.
            file_path (str): GCS URI of the original media file.
            content_type (str): MIME type of the media file (e.g., "video/mp4").
            file_category (str): The category of the file (e.g., "video", "audio", "document").
            file_name (str): The original name of the file.
            public_url (Optional[str], optional): Publicly accessible URL for 
            the media file. Defaults to None.
            source (str, optional): The source of the media file (e.g., "GCS", "youtube"). Defaults to "GCS".
            poster_url (str, optional): URL for a poster image. Defaults to a placeholder.
            is_dummy (bool, optional): Flag if this is dummy content. Defaults to False.

        Returns:
            bool: True if insertion was successful, False otherwise.
        """
        doc_ref = self._get_doc_ref(asset_id)
        current_time = firestore.SERVER_TIMESTAMP # Use server timestamp for consistency

        # Determine initial status for each sub-metadata based on file_category
        is_video_audio = file_category in ["video", "audio"]
        initial_data = {
            "file_name": file_name,
            "file_path": file_path,
            "public_url": public_url,
            "content_type": content_type,
            "source": source,
            "file_category": file_category,
            "upload_time": current_time,
            "last_updated": current_time,
            "poster_url": poster_url,
            "is_dummy": is_dummy,
            "summary": {
                "status": "pending",
                "text": None,
                "chapters": [],
                "error_message": None,
                "last_updated": None
            },
            "transcription": {
                "status": "pending" if is_video_audio else "not_applicable",
                "text": None,
                "language": None,
                "gcs_uri": None,
                "error_message": None,
                "last_updated": None
            },
            "previews": {
                "status": "pending" if is_video_audio else "not_applicable",
                "clips": [],
                "error_message": None,
                "last_updated": None
            }
        }

        # Add type-specific detail objects, initially empty
        if file_category == "video":
            initial_data["video_details"] = {}
        elif file_category == "image":
            initial_data["image_details"] = {}
        elif file_category == "document":
            initial_data["article_details"] = {}

        try:
            doc_ref.set(initial_data, merge=False) # Use merge=False for initial creation
            logger.info("Successfully inserted asset: %s",
                        asset_id, extra={"extra_fields": {"asset_id": asset_id}})
            return True
        except Exception:
            logger.error("Error inserting asset %s",
                        asset_id, exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
            return False

    def get_asset(self, asset_id: str) -> Optional[dict]:
        """
        Retrieves a media asset document from Firestore.

        Args:
            asset_id (str): The unique ID of the media asset.

        Returns:
            Optional[dict]: The asset's data as a dictionary, or None if not found.
        """
        doc_ref = self._get_doc_ref(asset_id)
        try:
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                logger.debug("Retrieved asset: %s",
                            asset_id, extra={"extra_fields": {"asset_id": asset_id}})
                return data
            else:
                logger.warning("Asset %s not found.",
                                asset_id, extra={"extra_fields": {"asset_id": asset_id}})
                return None
        except Exception:
            logger.error("Error retrieving asset %s",
                        asset_id, exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
            return None

    def update_asset_metadata(
        self,
        asset_id: str,
        metadata_type: str, # e.g., "summary", "transcription", "previews", "video_details", etc.
        data: dict
    ) -> bool:
        """
        Updates a specific nested metadata section or top-level field for an asset.

        Args:
            asset_id (str): The unique ID of the media asset.
            metadata_type (str): The name of the top-level or nested field to update
                                 (e.g., "summary", "transcription", "previews", "poster_url").
                                 For nested fields, pass the object name.
            data (dict): A dictionary containing the fields to update within that section.
                         If updating a top-level field (like "poster_url"), 'data'
                         should be a dict like {"poster_url": "new_url"}.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        doc_ref = self._get_doc_ref(asset_id)
        update_payload = {}
        current_time = firestore.SERVER_TIMESTAMP

        # Check if the update is for a nested dictionary (e.g., "summary", "transcription").
        # These are predefined, structured objects within the Firestore document.
        if metadata_type in ["summary", "transcription", "previews", "video_details",
                        "image_details", "article_details"]:
            # For nested objects, construct the update payload using dot notation.
            # This allows Firestore to update individual fields within the nested object
            # without overwriting the entire object.
            for key, value in data.items():
                update_payload[f"{metadata_type}.{key}"] = value
            update_payload[f"{metadata_type}.last_updated"] = current_time
        else:
            # If it's not a known nested object, treat it as a top-level field.
            # The 'data' argument is expected to be the direct value for the field.
            update_payload[metadata_type] = data

        update_payload["last_updated"] = current_time # Always update top-level timestamp

        try:
            doc_ref.update(update_payload)
            logger.info("Successfully updated '%s' for asset: %s",
                        metadata_type, asset_id,
                        extra={"extra_fields":
                        {"asset_id": asset_id, "metadata_type": metadata_type}})
            return True
        except Exception:
            logger.error("Error updating '%s' for asset %s",
                        metadata_type,
                        asset_id,
                        exc_info=True,
                        extra={"extra_fields":
                        {"asset_id": asset_id, "metadata_type": metadata_type}})
            return False

    def delete_asset(self, asset_id: str) -> bool:
        """
        Deletes a media asset document from Firestore.

        Args:
            asset_id (str): The unique ID of the media asset to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        doc_ref = self._get_doc_ref(asset_id)
        try:
            doc_ref.delete()
            logger.info("Successfully deleted asset: %s",
                        asset_id, extra={"extra_fields": {"asset_id": asset_id}})
            return True
        except Exception :
            logger.error("Error deleting asset %s",
                        asset_id,
                        exc_info=True, extra={"extra_fields": {"asset_id": asset_id}})
            return False
