"""Application configuration.

Database Configuration:
- Development: Local PostgreSQL via Docker Compose or SQLite fallback
- Testing: Neon database for e2e tests, SQLite in-memory for unit tests
- Production: Neon PostgreSQL database

Environment Variables:
- DATABASE_URL: PostgreSQL connection string (required for production and e2e testing)
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_SIZE", 52428800))  # 50 MB
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "app/static/uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    # AI Model Options (for street name recognition):
    EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "google/gemini-2.5-pro")

    # Database batch operations
    BATCH_INSERT_SIZE = int(os.environ.get("BATCH_INSERT_SIZE", 50))

    # Google Cloud Storage
    GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
    GCS_BUCKET_DEV = os.environ.get("GCS_BUCKET_DEV", "streets-editor-dev")
    GCS_BUCKET_TEST = os.environ.get("GCS_BUCKET_TEST", "streets-editor-test")
    GCS_BUCKET_PROD = os.environ.get("GCS_BUCKET_PROD", "streets-editor-prod")


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


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    WTF_CSRF_ENABLED = False

    def __init__(self):
        super().__init__()
        # Use Neon database for e2e tests, fallback to in-memory SQLite for unit tests
        database_url = os.environ.get("DATABASE_URL") or "sqlite:///:memory:"
        self.SQLALCHEMY_DATABASE_URI = database_url


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
