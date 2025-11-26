"""Application entry point."""

import os

from app import create_app

# Determine config name from FLASK_ENV
flask_env = os.environ.get("FLASK_ENV", "development")
config_name = {"development": "development", "production": "production", "testing": "testing"}.get(
    flask_env, "development"
)

app = create_app(config_name)

if __name__ == "__main__":
    app.run(debug=True)
