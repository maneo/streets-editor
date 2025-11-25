"""Flask application factory."""

import os

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import config
from app.services.gcs_service import GCSService

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app(config_name="development"):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    # Load configuration
    app.config.from_object(config[config_name]())

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Initialize services
    app.gcs_service = GCSService(app)

    # Configure Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User

        return User.query.get(int(user_id))

    # Import models (required for Flask-Migrate)
    from app.models import street, user

    # Register blueprints
    from app.routes import api_dictionaries, api_streets, auth, upload

    app.register_blueprint(auth.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(api_streets.bp)
    app.register_blueprint(api_dictionaries.bp)

    # Register CLI commands
    from app.cli import register_cli_commands

    register_cli_commands(app)

    # Create database tables
    # with app.app_context():
    #     if config_name in ["development", "testing"]:
    #         db.create_all()

    return app
