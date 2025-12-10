"""Flask CLI commands for development and testing."""

import os

import click
import requests

from app import db
from app.models.source_maps import SourceMaps
from app.models.street import Street
from app.models.street_content import StreetContent
from app.models.user import User
from app.services.ai_extraction import extract_streets_from_image
from app.services.geocoding_service import GeocodingService


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
        # Delete in correct order to avoid foreign key constraints
        # Streets -> SourceMaps -> Users (reverse dependency order)
        num_streets = Street.query.delete()
        num_source_maps = SourceMaps.query.delete()
        num_users = User.query.delete()

        db.session.commit()

        click.echo("Database cleared!")
        click.echo(f"  Deleted {num_streets} streets")
        click.echo(f"  Deleted {num_source_maps} source maps")
        click.echo(f"  Deleted {num_users} users")

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
            source_map_count = SourceMaps.query.filter_by(user_id=user.id).count()
            click.echo(f"  ID: {user.id}")
            click.echo(f"  Email: {user.email}")
            click.echo(f"  Created: {user.created_at}")
            click.echo(f"  Streets: {street_count}")
            click.echo(f"  Source Maps: {source_map_count}")
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

    @app.cli.command("delete-bucket")
    @click.option(
        "--env",
        required=True,
        type=click.Choice(["dev", "test", "prod"]),
        help="Environment (dev, test, prod)",
    )
    @click.confirmation_option(
        prompt="Are you sure you want to delete the bucket? This will permanently delete all files!"
    )
    def delete_bucket(env):
        """Delete Google Cloud Storage bucket for the specified environment.

        Usage:
            flask delete-bucket --env dev
            flask delete-bucket --env test
            flask delete-bucket --env prod
        """
        # Map env to bucket config key
        bucket_config_key = f"GCS_BUCKET_{env.upper()}"
        bucket_name = app.config.get(bucket_config_key)

        if not bucket_name:
            click.echo(
                f"❌ Bucket not configured for environment '{env}'. Make sure {bucket_config_key} is set."
            )
            return

        try:
            # Initialize GCS client
            gcs_service = app.gcs_service
            client = gcs_service.client

            # Get bucket
            bucket = client.bucket(bucket_name)

            # Check if bucket exists
            if not bucket.exists():
                click.echo(f"❌ Bucket '{bucket_name}' does not exist.")
                return

            # Delete bucket (force=True deletes all objects)
            click.echo(f"Deleting bucket '{bucket_name}' and all its contents...")
            bucket.delete(force=True)

            click.echo(f"✅ Bucket '{bucket_name}' deleted successfully!")

        except Exception as e:
            click.echo(f"❌ Failed to delete bucket: {str(e)}")

    @app.cli.command("recreate-bucket")
    @click.option(
        "--env",
        required=True,
        type=click.Choice(["dev", "test", "prod"]),
        help="Environment (dev, test, prod)",
    )
    def recreate_bucket(env):
        """Recreate Google Cloud Storage bucket with proper permissions for the specified environment.

        This creates the bucket in the europe-west1 region with:
        - Public read access for all users
        - Uniform bucket-level access enabled

        Usage:
            flask recreate-bucket --env dev
            flask recreate-bucket --env test
            flask recreate-bucket --env prod
        """
        # Map env to bucket config key
        bucket_config_key = f"GCS_BUCKET_{env.upper()}"
        bucket_name = app.config.get(bucket_config_key)

        if not bucket_name:
            click.echo(
                f"❌ Bucket not configured for environment '{env}'. Make sure {bucket_config_key} is set."
            )
            return

        try:
            # Initialize GCS client
            gcs_service = app.gcs_service
            client = gcs_service.client
            project_id = app.config.get("GCP_PROJECT_ID")

            # Create bucket in Europe West 1 region
            click.echo(f"Creating bucket '{bucket_name}' in europe-west1 region...")
            bucket = client.create_bucket(bucket_name, project=project_id, location="europe-west1")

            # Set public read access for all users
            click.echo("Setting public read access...")
            policy = bucket.get_iam_policy()
            policy.bindings.append({"role": "roles/storage.objectViewer", "members": ["allUsers"]})
            bucket.set_iam_policy(policy)

            click.echo(f"✅ Bucket '{bucket_name}' recreated successfully with public read access!")

        except Exception as e:
            click.echo(f"❌ Failed to recreate bucket: {str(e)}")

    @app.cli.command("enrich-streets-geo")
    @click.option("--city", required=True, help="City name")
    @click.option("--user-id", type=int, help="User ID (defaults to first user if not specified)")
    def enrich_streets_geo(city, user_id):
        """Enrich default streets with geolocation data using Nominatim API.

        This command processes all default streets for a city that don't have
        street_content yet, and enriches them with latitude/longitude.

        Usage:
            flask enrich-streets-geo --city "Poznań"
            flask enrich-streets-geo --city "Warszawa" --user-id 1
        """
        with app.app_context():
            # Get user
            if user_id:
                user = User.query.get(user_id)
                if not user:
                    click.echo(f"❌ User with ID {user_id} not found.")
                    return
            else:
                user = User.query.first()
                if not user:
                    click.echo("❌ No users found in database.")
                    return

            click.echo(f"Enriching streets for city: {city} (User: {user.email})")

            # Get all default streets for the city that don't have street_content yet
            streets = (
                Street.query.filter_by(
                    user_id=user.id, city=city, is_default_street=True, is_rejected=False
                )
                .outerjoin(StreetContent)
                .filter(StreetContent.id.is_(None))
                .order_by(Street.main_name)
                .all()
            )

            if not streets:
                click.echo(f"No default streets found for {city} without content.")
                return

            click.echo(f"Found {len(streets)} streets to enrich.")
            click.echo()

            # Initialize geocoding service
            geocoding_service = GeocodingService()

            success_count = 0
            failed_count = 0

            for idx, street in enumerate(streets, 1):
                display_prefix = (
                    "" if not street.prefix or street.prefix == "-" else f"{street.prefix} "
                )
                display_name = f"{display_prefix}{street.main_name_cs}".strip()

                click.echo(f"Enriching street {idx}/{len(streets)}: {display_name}...", nl=False)

                # Geocode the street
                result = geocoding_service.geocode_street(
                    street.main_name_cs, street.city, street.prefix
                )

                if result:
                    # Create or update street content
                    street_content = StreetContent(
                        street_id=street.id,
                        latitude=result["latitude"],
                        longitude=result["longitude"],
                        updated_by=user.id,
                    )
                    db.session.add(street_content)
                    db.session.commit()

                    click.echo(f" ✅ ({result['latitude']:.6f}, {result['longitude']:.6f})")
                    success_count += 1
                else:
                    click.echo(" ❌ Not found")
                    failed_count += 1

            click.echo()
            click.echo("✅ Enrichment complete!")
            click.echo(f"   Enriched: {success_count}/{len(streets)} streets")
            if failed_count > 0:
                click.echo(f"   Failed: {failed_count} streets")
