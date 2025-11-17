"""Flask CLI commands for development and testing."""

import os

import click
import requests

from app import db
from app.models.street import Street
from app.models.user import User
from app.services.ai_extraction import extract_streets_from_image


def register_cli_commands(app):
    """Register Flask CLI commands."""

    @app.cli.command("create-test-user")
    @click.option("--email", default="test@example.com", help="User email")
    @click.option("--password", default="password123", help="User password")
    def create_test_user(email, password):
        """Create a test user for development and testing.

        Usage:
            flask create-test-user
            flask create-test-user --email admin@test.com --password admin123
        """
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            click.echo(f"User with email '{email}' already exists.")
            return

        # Create new user
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        click.echo("Test user created successfully!")
        click.echo(f"  Email: {email}")
        click.echo(f"  Password: {password}")
        click.echo(f"  User ID: {user.id}")

    @app.cli.command("clear-db")
    @click.confirmation_option(prompt="Are you sure you want to delete all data?")
    def clear_database():
        """Clear all data from database (requires confirmation).

        Usage:
            flask clear-db
        """
        # Delete all streets
        num_streets = Street.query.delete()

        # Delete all users
        num_users = User.query.delete()

        db.session.commit()

        click.echo("Database cleared!")
        click.echo(f"  Deleted {num_users} users")
        click.echo(f"  Deleted {num_streets} streets")

    @app.cli.command("list-users")
    def list_users():
        """List all users in the database.

        Usage:
            flask list-users
        """
        users = User.query.all()

        if not users:
            click.echo("No users found in database.")
            return

        click.echo(f"Found {len(users)} user(s):")
        click.echo()

        for user in users:
            street_count = Street.query.filter_by(user_id=user.id, is_rejected=False).count()
            click.echo(f"  ID: {user.id}")
            click.echo(f"  Email: {user.email}")
            click.echo(f"  Created: {user.created_at}")
            click.echo(f"  Streets: {street_count}")
            click.echo()

    @app.cli.command("test-model")
    @click.option(
        "--model", default=None, help="AI model to test (uses EXTRACTION_MODEL if not specified)"
    )
    def test_ai_model(model, create_test_image):
        """Test AI model extraction with a sample image.

        Usage:
            flask test-model
            flask test-model --model google/gemini-flash-1.5
            flask test-model --model openai/gpt-4o-mini
            flask test-model --create-test-image
        """
        # Override model if specified
        if model:
            os.environ["EXTRACTION_MODEL"] = model
            app.config["EXTRACTION_MODEL"] = model

        click.echo(f"Testing AI model: {app.config['EXTRACTION_MODEL']}")

        # Find or create test image
        test_image_path = None

        # Check if example image exists
        example_image = "tests/example_of_city_plan.jpg"
        if os.path.exists(example_image):
            test_image_path = example_image
            click.echo(f"Using existing test image: {example_image}")
        else:
            click.echo("No test image found. Use --create-test-image to create one.")
            return

        try:
            # Test extraction
            result = extract_streets_from_image(test_image_path, "Test City", "2020-2029")
            click.echo("✅ Model test successful!")
            click.echo(f"   Extracted {len(result)} streets:")
            for street in result[:5]:  # Show first 5 results
                click.echo(f"   - {street.get('prefix', '')} {street.get('main_name', '')}")

        except Exception as e:
            click.echo(f"❌ Model test failed: {str(e)}")

    @app.cli.command("list-models")
    def list_available_models():
        """List available models from OpenRouter API.

        Usage:
            flask list-models
        """
        api_key = app.config.get("OPENROUTER_API_KEY")
        if not api_key:
            click.echo("❌ No OPENROUTER_API_KEY found in config")
            return

        click.echo("Fetching available models from OpenRouter...")
        click.echo(f"API Key: {api_key[:20]}...")

        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(
                "https://openrouter.ai/api/v1/models", headers=headers, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            models = data.get("data", [])

            # Filter for vision-capable models (those that support images)
            vision_models = []
            for model in models:
                model_id = model.get("id", "")
                if any(
                    keyword in model_id.lower()
                    for keyword in ["vision", "gpt-4", "gemini", "claude"]
                ):
                    vision_models.append(model)

            click.echo(f"✅ Found {len(vision_models)} vision-capable models:")
            click.echo()

            for model in vision_models[:20]:  # Show first 20
                model_id = model.get("id", "")
                model_name = model.get("name", "")
                pricing = model.get("pricing", {})
                input_price = pricing.get("prompt", "N/A")
                output_price = pricing.get("completion", "N/A")

                click.echo(f"  {model_id}")
                click.echo(f"    Name: {model_name}")
                click.echo(f"    Input: ${input_price}, Output: ${output_price}")
                click.echo()

            if len(vision_models) > 20:
                click.echo(f"... and {len(vision_models) - 20} more models")

        except requests.exceptions.RequestException as e:
            click.echo(f"❌ Failed to fetch models: {str(e)}")
            if hasattr(e, "response") and e.response:
                click.echo(f"Response: {e.response.text}")
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
