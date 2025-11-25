"""Google Cloud Storage service for handling file uploads."""

import os

from flask import current_app
from google.cloud import storage
from werkzeug.datastructures import FileStorage


class GCSService:
    """Service for handling Google Cloud Storage operations."""

    def __init__(self, app=None):
        """Initialize GCS client."""
        self.app = app
        if app:
            self._init_client(app)
        else:
            # Lazy initialization - will be done when first method is called
            self.client = None
            self.project_id = None

    def _init_client(self, app):
        """Initialize the GCS client with app config."""
        self.project_id = app.config.get("GCP_PROJECT_ID")
        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID not configured")

        # Initialize client with service account key if provided
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            self.client = storage.Client.from_service_account_json(credentials_path)
        elif app.config.get("FLASK_ENV") == "testing":
            # In testing environment, don't initialize actual GCS client
            # Just set a mock client or None to avoid authentication errors
            self.client = None
        else:
            # Use default credentials (for GCP environments)
            self.client = storage.Client(project=self.project_id)

        # Initialize client with service account key if provided
        credentials_path = os.environ.get("GCP_SA_KEY")
        if credentials_path and os.path.exists(credentials_path):
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            # Use default credentials (for GCP environments)
            self.client = storage.Client(project=self.project_id)

    def _ensure_initialized(self):
        """Ensure the GCS client is initialized."""
        if self.client is None:
            if self.app:
                self._init_client(self.app)
            else:
                # Try to get current_app if available
                from flask import current_app

                self._init_client(current_app)

    def get_bucket_name(self) -> str:
        """Get the appropriate bucket name based on environment."""
        self._ensure_initialized()

        env = os.environ.get("FLASK_ENV", "development")

        if env == "production":
            bucket_name = (
                self.app.config.get("GCS_BUCKET_PROD")
                if self.app
                else current_app.config.get("GCS_BUCKET_PROD")
            )
        elif env == "testing":
            bucket_name = (
                self.app.config.get("GCS_BUCKET_TEST")
                if self.app
                else current_app.config.get("GCS_BUCKET_TEST")
            )
        else:  # development
            bucket_name = (
                self.app.config.get("GCS_BUCKET_DEV")
                if self.app
                else current_app.config.get("GCS_BUCKET_DEV")
            )

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
        self._ensure_initialized()

        # In testing environment, skip actual upload
        if self.client is None:
            # Return mock data for testing
            _, ext = os.path.splitext(original_filename)
            gcs_filename = f"{source_map_id}{ext}"
            public_url = f"https://storage.googleapis.com/test-bucket/{gcs_filename}"
            return gcs_filename, public_url

        bucket_name = self.get_bucket_name()
        bucket = self.client.bucket(bucket_name)

        # Generate filename based on source_map_id
        # Keep file extension from original filename
        _, ext = os.path.splitext(original_filename)
        gcs_filename = f"{source_map_id}{ext}"

        blob = bucket.blob(gcs_filename)
        blob.upload_from_file(file, content_type=file.content_type)

        # For buckets with uniform bucket-level access, construct public URL directly
        # The bucket should be configured with public read access at bucket level
        public_url = f"https://storage.googleapis.com/{bucket_name}/{gcs_filename}"

        return gcs_filename, public_url

    def file_exists(self, gcs_filename: str) -> bool:
        """
        Check if file exists in GCS.

        Args:
            gcs_filename: Filename in GCS

        Returns:
            bool: True if file exists
        """
        self._ensure_initialized()

        # In testing environment, return False for file existence checks
        if self.client is None:
            return False

        try:
            bucket_name = self.get_bucket_name()
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(gcs_filename)
            return blob.exists()
        except Exception as e:
            from flask import current_app

            current_app.logger.error(f"Failed to check if file {gcs_filename} exists in GCS: {e}")
            return False
