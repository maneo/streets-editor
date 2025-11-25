"""Google Cloud Storage service for handling file uploads."""

import os

from google.cloud import storage
from werkzeug.datastructures import FileStorage

from app import current_app


class GCSService:
    """Service for handling Google Cloud Storage operations."""

    def __init__(self):
        """Initialize GCS client."""
        self.project_id = current_app.config.get("GCS_PROJECT_ID")
        if not self.project_id:
            raise ValueError("GCS_PROJECT_ID not configured")

        # Initialize client with service account key if provided
        credentials_path = os.environ.get("GCP_SA_KEY")
        if credentials_path and os.path.exists(credentials_path):
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            # Use default credentials (for GCP environments)
            self.client = storage.Client(project=self.project_id)

    def get_bucket_name(self) -> str:
        """Get the appropriate bucket name based on environment."""
        env = os.environ.get("FLASK_ENV", "development")

        if env == "production":
            bucket_name = current_app.config.get("GCS_BUCKET_PROD")
        elif env == "testing":
            bucket_name = current_app.config.get("GCS_BUCKET_TEST")
        else:  # development
            bucket_name = current_app.config.get("GCS_BUCKET_DEV")

        if not bucket_name:
            raise ValueError(f"GCS bucket not configured for environment: {env}")

        return bucket_name

    def upload_file(
        self, file: FileStorage, source_map_id: int, original_filename: str
    ) -> tuple[str, str]:
        """
        Upload file to GCS with ID-based naming.

        Args:
            file: FileStorage object from Flask request
            source_map_id: ID of the SourceMap record (used for filename)
            original_filename: Original filename from upload

        Returns:
            tuple: (gcs_filename, public_url)
        """
        bucket_name = self.get_bucket_name()
        bucket = self.client.bucket(bucket_name)

        # Generate filename based on source_map_id
        # Keep file extension from original filename
        _, ext = os.path.splitext(original_filename)
        gcs_filename = f"{source_map_id}{ext}"

        blob = bucket.blob(gcs_filename)
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public()
        public_url = blob.public_url

        return gcs_filename, public_url

    def file_exists(self, gcs_filename: str) -> bool:
        """
        Check if file exists in GCS.

        Args:
            gcs_filename: Filename in GCS

        Returns:
            bool: True if file exists
        """
        try:
            bucket_name = self.get_bucket_name()
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(gcs_filename)
            return blob.exists()
        except Exception as e:
            current_app.logger.error(f"Failed to check if file {gcs_filename} exists in GCS: {e}")
            return False
