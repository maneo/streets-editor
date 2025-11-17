"""Application configuration."""

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

    # AI Model Options (most economic for street name recognition):
    # Free: google/gemini-2.0-flash-exp:free (rate limited, unreliable)
    # Best value: google/gemini-flash-1.5 (~$0.000075/1K input, $0.0003/1K output tokens)
    # Alternative: google/gemini-pro-1.5 (~$0.00125/1K input, $0.005/1K output tokens)
    # Model selection - change this line to switch models:
    # Try these in order if one doesn't work: openai/gpt-4o-mini, google/gemini-flash-1.5, google/gemini-pro-1.5
    EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "google/gemini-2.5-pro")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "..", "instance", "streets_editor.db"
    )


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False

    def __init__(self):
        super().__init__()
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required for production. "
                "Please set it to your database connection string."
            )
        self.SQLALCHEMY_DATABASE_URI = database_url


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
