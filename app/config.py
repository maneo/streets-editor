"""Application configuration.

Database Configuration:
- Development: Local PostgreSQL via Docker Compose or SQLite fallback
- Testing: Neon database for e2e tests, SQLite in-memory for unit tests
- Production: Neon PostgreSQL database

Environment Variables:
- DATABASE_URL: PostgreSQL connection string (required for production and e2e testing)
"""

import os
from unittest.mock import Mock

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Parse MAX_UPLOAD_SIZE, handling potential whitespace/comments
    _max_upload_size = os.environ.get("MAX_UPLOAD_SIZE", "52428800")
    # Strip whitespace and take first token (in case comment was included)
    _max_upload_size_stripped = _max_upload_size.strip() if _max_upload_size else ""
    _max_upload_size_clean = (
        _max_upload_size_stripped.split()[0] if _max_upload_size_stripped else "52428800"
    )
    MAX_CONTENT_LENGTH = int(_max_upload_size_clean)  # 50 MB
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "app/static/uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
    ALLOWED_CSV_EXTENSIONS = {"csv"}
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    # AI Model Options (for street name recognition):
    EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "google/gemini-2.5-pro")

    # Database batch operations
    _batch_size = os.environ.get("BATCH_INSERT_SIZE", "50")
    _batch_size_stripped = _batch_size.strip() if _batch_size else ""
    BATCH_INSERT_SIZE = int(_batch_size_stripped.split()[0] if _batch_size_stripped else "50")

    # Google Cloud Storage
    GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gazety-poznan-pl")
    GCS_BUCKET_DEV = os.environ.get("GCS_BUCKET_DEV", "streets-editor-dev")
    GCS_BUCKET_TEST = os.environ.get("GCS_BUCKET_TEST", "streets-editor-test")
    GCS_BUCKET_PROD = os.environ.get("GCS_BUCKET_PROD", "streets-editor-prod")

    def get_gcs_bucket_name(self) -> str:
        """Get the GCS bucket name for this configuration."""
        bucket_name = self.GCS_BUCKET_DEV
        if not bucket_name:
            raise ValueError("GCS bucket not configured for development environment")
        return bucket_name

    def create_gcs_service(self, app):
        """Factory method to create appropriate GCS service for the environment."""
        from app.services.gcs_service import GCSService

        bucket_name = self.get_gcs_bucket_name()
        return GCSService(app, bucket_name)


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    # Use PostgreSQL for development (Docker Compose) or fallback to SQLite
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "postgresql://postgres:postgres@localhost:5432/streets_editor_dev"
    )


class ProductionConfig(Config):
    """Production configuration using Neon PostgreSQL."""

    DEBUG = False

    def __init__(self):
        super().__init__()
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required for production. "
                "Please set it to your Neon database connection string."
            )
        self.SQLALCHEMY_DATABASE_URI = database_url

    def get_gcs_bucket_name(self) -> str:
        """Get the GCS bucket name for production."""
        bucket_name = self.GCS_BUCKET_PROD
        if not bucket_name:
            raise ValueError("GCS bucket not configured for production environment")
        return bucket_name


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    WTF_CSRF_ENABLED = False

    def __init__(self):
        super().__init__()
        # Use Neon database for e2e tests (DATABASE_URL_E2E).
        # Fallback to in-memory SQLite for unit tests or if not configured.
        self.SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL_E2E") or "sqlite:///:memory:"

    def get_gcs_bucket_name(self) -> str:
        """Get the GCS bucket name for testing."""
        bucket_name = self.GCS_BUCKET_TEST
        if not bucket_name:
            raise ValueError("GCS bucket not configured for testing environment")
        return bucket_name

    def create_gcs_service(self, app):
        """Return mocked GCS service for testing."""
        mock_service = Mock()

        # Set bucket_name attribute for consistency with real service
        mock_service.bucket_name = self.get_gcs_bucket_name()

        # Configure upload_file to return predictable values
        mock_service.upload_file.return_value = (
            "mock_123.png",
            "https://mock-storage/mock_123.png",
        )

        # Configure file_exists for different test cases
        mock_service.file_exists.return_value = False

        # You can make it configurable for different tests
        if hasattr(app.config, "MOCK_GCS_ERROR"):
            mock_service.upload_file.side_effect = Exception("Mock GCS error")

        return mock_service


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
