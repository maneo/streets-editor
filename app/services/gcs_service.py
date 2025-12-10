"""Google Cloud Storage service for handling file uploads."""

import mimetypes
import os

from google.cloud import storage
from werkzeug.datastructures import FileStorage


class GCSService:
    """Service for handling Google Cloud Storage operations."""

    def __init__(self, app, bucket_name: str):
        """Initialize GCS client."""
        self.app = app
        self.bucket_name = bucket_name
        self.project_id = app.config.get("GCP_PROJECT_ID")
        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID not configured")

        # Try multiple credential sources in order of preference
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            # Try GCP_SA_KEY environment variable
            credentials_path = os.environ.get("GCP_SA_KEY")
            if credentials_path and os.path.exists(credentials_path):
                self.client = storage.Client.from_service_account_json(credentials_path)
            else:
                # Use default credentials (for GCP environments)
                self.client = storage.Client(project=self.project_id)

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
        bucket_name = self.bucket_name
        bucket = self.client.bucket(bucket_name)

        # Generate filename based on source_map_id
        # Keep file extension from original filename
        _, ext = os.path.splitext(original_filename)
        gcs_filename = f"{source_map_id}{ext}"

        blob = bucket.blob(gcs_filename)

        guessed_type, _ = mimetypes.guess_type(original_filename)
        content_type = file.content_type or guessed_type or "application/octet-stream"

        blob.upload_from_file(file, content_type=content_type)

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
        try:
            bucket_name = self.bucket_name
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(gcs_filename)
            return blob.exists()
        except Exception as e:
            from flask import current_app

            current_app.logger.error(f"Failed to check if file {gcs_filename} exists in GCS: {e}")
            return False

    def delete_bucket_with_contents(self, bucket_name: str) -> None:
        """
        Delete a GCS bucket and all its contents.

        Args:
            bucket_name: Name of the bucket to delete

        Raises:
            Exception: If bucket doesn't exist or deletion fails
        """
        bucket = self.client.bucket(bucket_name)

        if not bucket.exists():
            raise ValueError(f"Bucket '{bucket_name}' does not exist.")

        # Delete bucket (force=True deletes all objects)
        bucket.delete(force=True)

    def create_public_bucket(self, bucket_name: str, location: str = "europe-west1") -> None:
        """
        Create a GCS bucket with public read access.

        Args:
            bucket_name: Name of the bucket to create
            location: GCS location/region (default: europe-west1)

        Raises:
            Exception: If bucket creation or permission setup fails
        """
        # Create bucket in specified region
        bucket = self.client.create_bucket(bucket_name, project=self.project_id, location=location)

        # Set public read access for all users
        policy = bucket.get_iam_policy()
        policy.bindings.append({"role": "roles/storage.objectViewer", "members": ["allUsers"]})
        bucket.set_iam_policy(policy)
