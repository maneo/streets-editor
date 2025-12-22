"""Flask CLI commands for development and testing."""

import csv
import json
import os

import click
import requests

from app import db
from app.models.source_maps import SourceMaps
from app.models.street import Street
from app.models.street_content import StreetContent
from app.models.user import User
from app.services.ai_extraction import extract_streets_from_image
from app.services.csv_import import _normalize_prefix
from app.services.geocoding_service import GeocodingService
from app.services.street_matching_service import StreetMatchingService


def _get_user_or_default(user_id=None):
    """Get user by ID or return first user.

    Args:
        user_id: Optional user ID

    Returns:
        tuple: (user, error_message) where error_message is None on success
    """
    if user_id:
        user = User.query.get(user_id)
        if not user:
            return None, f"User with ID {user_id} not found."
    else:
        user = User.query.first()
        if not user:
            return None, "No users found in database."
    return user, None


def _get_bucket_name_for_env(app, env):
    """Get bucket name for environment from config.

    Args:
        app: Flask application instance
        env: Environment name (dev, test, prod)

    Returns:
        tuple: (bucket_name, error_message) where error_message is None on success
    """
    bucket_config_key = f"GCS_BUCKET_{env.upper()}"
    bucket_name = app.config.get(bucket_config_key)
    if not bucket_name:
        return (
            None,
            f"Bucket not configured for environment '{env}'. Make sure {bucket_config_key} is set.",
        )
    return bucket_name, None


def _format_street_display_name(street):
    """Format street name with prefix for display.

    Args:
        street: Street model instance

    Returns:
        str: Formatted street name
    """
    if street.prefix and street.prefix != "-":
        return f"{street.prefix} {street.main_name_cs}"
    return street.main_name_cs


def _load_csv_streets(csv_file, city):
    """Load and filter CSV rows by city.

    Args:
        csv_file: Path to CSV file
        city: City name to filter by

    Returns:
        list: List of dicts with keys: prefix, street_name, link
    """
    csv_streets = []
    try:
        with open(csv_file, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_city = row.get("city", "").strip()
                if row_city.lower() == city.lower():
                    prefix_raw = row.get("prefix", "").strip()
                    street_name = row.get("street_name", "").strip()
                    link = row.get("link", "").strip()

                    if not street_name or not link:
                        continue

                    # Normalize prefix
                    prefix, _ = _normalize_prefix(prefix_raw)

                    csv_streets.append(
                        {
                            "prefix": prefix,
                            "street_name": street_name.lower(),
                            "link": link,
                        }
                    )
    except FileNotFoundError:
        raise click.ClickException(f"CSV file not found: {csv_file}") from None
    except Exception as e:
        raise click.ClickException(f"Error reading CSV file: {str(e)}") from e

    return csv_streets


def _extract_last_word(street_name):
    """Extract last word from street name for fallback matching.

    Args:
        street_name: Street name string

    Returns:
        str: Last word of the street name, or empty string if no words
    """
    words = street_name.strip().split()
    return words[-1] if words else ""


def _match_csv_to_defaults(csv_streets, default_lookup):
    """Match CSV streets to default streets using two-step matching.

    Args:
        csv_streets: List of dicts with prefix, street_name, link
        default_lookup: Dictionary mapping (prefix, main_name) to Street objects

    Returns:
        tuple: (matches, not_matched, duplicates) where:
            - matches is list of (csv_entry, default_street) tuples
            - not_matched is list of unmatched csv_entry dicts
            - duplicates is dict mapping default_street_id to list of csv_entry dicts
    """
    matches = []
    not_matched = []
    matched_default_ids = {}  # Track which default streets have been matched
    duplicates = {}  # Track multiple CSV entries matching same default street

    # Step 1: Exact matching
    for csv_entry in csv_streets:
        key = (csv_entry["prefix"], csv_entry["street_name"])
        default_street = default_lookup.get(key)

        if default_street:
            if default_street.id in matched_default_ids:
                # Duplicate match - add to duplicates dict
                if default_street.id not in duplicates:
                    duplicates[default_street.id] = [matched_default_ids[default_street.id]]
                duplicates[default_street.id].append(csv_entry)
            else:
                matches.append((csv_entry, default_street))
                matched_default_ids[default_street.id] = csv_entry

    # Step 2: Fallback - last word matching for unmatched entries
    unmatched_csv = [
        csv_entry for csv_entry in csv_streets if not any(csv_entry == m[0] for m in matches)
    ]

    for csv_entry in unmatched_csv:
        last_word = _extract_last_word(csv_entry["street_name"])
        if last_word:
            key = (csv_entry["prefix"], last_word)
            default_street = default_lookup.get(key)

            if default_street:
                if default_street.id in matched_default_ids:
                    # Duplicate match
                    if default_street.id not in duplicates:
                        duplicates[default_street.id] = [matched_default_ids[default_street.id]]
                    duplicates[default_street.id].append(csv_entry)
                else:
                    matches.append((csv_entry, default_street))
                    matched_default_ids[default_street.id] = csv_entry
                continue

        # Still no match
        not_matched.append(csv_entry)

    return matches, not_matched, duplicates


def _add_link_to_street_content(street, link, user_id, dry_run=False):
    """Add link to StreetContent.external_links.

    Args:
        street: Street model instance
        link: URL string to add
        user_id: User ID for updated_by field
        dry_run: If True, don't save to database

    Returns:
        tuple: (success, message) where success is bool
    """
    # Check if StreetContent exists
    street_content = street.street_content

    if not street_content:
        # Create new StreetContent
        if not dry_run:
            street_content = StreetContent(
                street_id=street.id,
                external_links=json.dumps([link]),
                updated_by=user_id,
            )
            db.session.add(street_content)
            db.session.commit()
        return True, "created"

    # Check if external_links already exists (not empty)
    existing_links = (
        json.loads(street_content.external_links) if street_content.external_links else []
    )

    if existing_links:
        return False, "skipped (links already exist)"

    # Add link
    if not dry_run:
        street_content.external_links = json.dumps([link])
        street_content.updated_by = user_id
        db.session.add(street_content)
        db.session.commit()
    return True, "added"


def _add_links_to_street_content(street, links, user_id, dry_run=False):
    """Add multiple links to StreetContent.external_links.

    Args:
        street: Street model instance
        links: List of URL strings to add
        user_id: User ID for updated_by field
        dry_run: If True, don't save to database

    Returns:
        tuple: (success, message) where success is bool
    """
    # Check if StreetContent exists
    street_content = street.street_content

    if not street_content:
        # Create new StreetContent with all links
        if not dry_run:
            street_content = StreetContent(
                street_id=street.id,
                external_links=json.dumps(links),
                updated_by=user_id,
            )
            db.session.add(street_content)
            db.session.commit()
        return True, "created"

    # Check if external_links already exists (not empty)
    existing_links = (
        json.loads(street_content.external_links) if street_content.external_links else []
    )

    if existing_links:
        return False, "skipped (links already exist)"

    # Add all links
    if not dry_run:
        street_content.external_links = json.dumps(links)
        street_content.updated_by = user_id
        db.session.add(street_content)
        db.session.commit()
    return True, "added"


def _handle_duplicates(duplicates, default_lookup, dry_run):
    """Handle duplicate matches interactively.

    Args:
        duplicates: Dict mapping default_street_id to list of csv_entry dicts
        default_lookup: Dictionary mapping (prefix, main_name) to Street objects
        dry_run: If True, don't save to database

    Returns:
        dict: Mapping of default_street_id to chosen csv_entry (or None if skipped)
    """
    if not duplicates:
        return {}

    click.echo()
    click.echo("⚠️  Duplicate matches detected:")
    click.echo()

    chosen = {}

    for default_id, csv_entries in duplicates.items():
        # Find the default street
        default_street = None
        for street in default_lookup.values():
            if street.id == default_id:
                default_street = street
                break

        if not default_street:
            continue

        default_display = _format_street_display_name(default_street)
        click.echo(f"  Default street: {default_display}")
        click.echo("  Multiple CSV entries match this street:")
        for idx, csv_entry in enumerate(csv_entries, 1):
            csv_display = f"{csv_entry['prefix']} {csv_entry['street_name']}"
            click.echo(f"    {idx}. {csv_display} -> {csv_entry['link']}")

        if dry_run:
            click.echo(f"  [DRY RUN] Would use first entry: {csv_entries[0]['link']}")
            chosen[default_id] = csv_entries[0]
        else:
            # Interactive mode
            while True:
                choice = (
                    click.prompt(
                        f"  Choose action: (1-{len(csv_entries)} to use that link, "
                        f"'a' to append all, 's' to skip)",
                        default="1",
                    )
                    .strip()
                    .lower()
                )

                if choice == "s":
                    chosen[default_id] = None
                    break
                elif choice == "a":
                    # Append all links
                    chosen[default_id] = csv_entries
                    break
                elif choice.isdigit() and 1 <= int(choice) <= len(csv_entries):
                    chosen[default_id] = csv_entries[int(choice) - 1]
                    break
                else:
                    click.echo("  Invalid choice. Please try again.")

        click.echo()

    return chosen


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
        bucket_name, error = _get_bucket_name_for_env(app, env)
        if error:
            click.echo(f"❌ {error}")
            return

        try:
            # Use GCS service to delete bucket
            gcs_service = app.gcs_service
            click.echo(f"Deleting bucket '{bucket_name}' and all its contents...")
            gcs_service.delete_bucket_with_contents(bucket_name)
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
        bucket_name, error = _get_bucket_name_for_env(app, env)
        if error:
            click.echo(f"❌ {error}")
            return

        try:
            # Use GCS service to create bucket with public access
            gcs_service = app.gcs_service
            click.echo(f"Creating bucket '{bucket_name}' in europe-west1 region...")
            click.echo("Setting public read access...")
            gcs_service.create_public_bucket(bucket_name, location="europe-west1")
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
            # Get user using utility function
            user, error = _get_user_or_default(user_id)
            if error:
                click.echo(f"❌ {error}")
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
                display_name = _format_street_display_name(street)
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

    @app.cli.command("match-streets-to-default")
    @click.option("--city", required=True, help="City name")
    @click.option("--decade", required=True, help="Decade (e.g. '1940-1949')")
    @click.option("--user-id", type=int, help="User ID (defaults to first user)")
    @click.option("--dry-run", is_flag=True, help="Perform matching without saving to database")
    def match_streets_to_default(city, decade, user_id, dry_run):
        """Match streets from a city/decade to the default street dictionary.

        This command matches streets from a specific city and decade to the
        default streets dictionary for that city. Matching is done by comparing
        prefix and main_name (case-insensitive).

        Usage:
            flask match-streets-to-default --city "Poznań" --decade "1940-1949"
            flask match-streets-to-default --city "Poznań" --decade "1940-1949" --dry-run
            flask match-streets-to-default --city "Poznań" --decade "1940-1949" --user-id 1
        """
        with app.app_context():
            # Get user using utility function
            user, error = _get_user_or_default(user_id)
            if error:
                click.echo(f"❌ {error}")
                return

            # Initialize street matching service
            matching_service = StreetMatchingService(db.session)

            # Get default streets lookup
            default_lookup, default_streets = matching_service.get_default_streets_lookup(
                user.id, city
            )

            if not default_streets:
                click.echo(f"❌ No default streets found for city '{city}'.")
                click.echo("   Please import default streets for this city first.")
                return

            click.echo("Matching streets to default dictionary:")
            click.echo(f"  City: {city}")
            click.echo(f"  Decade: {decade}")
            click.echo(f"  User: {user.email}")
            click.echo(f"  Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
            click.echo(f"  Default streets available: {len(default_streets)}")
            click.echo()

            # Get source streets that need matching
            source_streets = matching_service.find_unmatched_source_streets(user.id, city, decade)

            if not source_streets:
                click.echo(f"No streets found to match for decade '{decade}'.")
                click.echo("   Either all streets are already mapped or no streets exist.")
                return

            click.echo(f"Processing {len(source_streets)} streets...")
            click.echo("")

            # Match streets using the service
            matches, not_matched = matching_service.match_streets(
                source_streets, default_lookup, save=not dry_run
            )

            # Display results
            for source_street, default_street in matches:
                source_display = _format_street_display_name(source_street)
                default_display = _format_street_display_name(default_street)

                if dry_run:
                    click.echo(f"  ✓ {source_display} → {default_display}")
                else:
                    click.echo(f"  ✅ {source_display} → {default_display} (saved)")

            for source_street in not_matched:
                source_display = _format_street_display_name(source_street)
                click.echo(f"  ✗ {source_display} (no match found)")

            # Show summary
            click.echo()
            click.echo("=" * 60)
            click.echo("Summary:")
            click.echo(f"  Total streets processed: {len(source_streets)}")
            click.echo(f"  Successfully matched: {len(matches)}")
            click.echo(f"  Not matched: {len(not_matched)}")
            if dry_run:
                click.echo()
                click.echo("  ℹ️  This was a dry run. No changes were saved to the database.")
                click.echo("  Run without --dry-run to save the mappings.")
            else:
                click.echo()
                click.echo("  ✅ All mappings have been saved to the database!")
            click.echo("=" * 60)

    @app.cli.command("add-links-from-csv")
    @click.option(
        "--csv-file",
        default="poznan_streets.csv",
        help="Path to CSV file (default: poznan_streets.csv)",
    )
    @click.option("--city", required=True, help="City name")
    @click.option("--user-id", type=int, help="User ID (defaults to first user)")
    @click.option("--dry-run", is_flag=True, help="Perform matching without saving to database")
    def add_links_from_csv(csv_file, city, user_id, dry_run):
        """Add links from CSV to default streets' StreetContent.

        This command loads streets from a CSV file, matches them to default
        dictionary streets for a given city, and adds links to their
        StreetContent.external_links.

        Matching strategy:
        1. Exact match by (prefix, street_name)
        2. Fallback: match by (prefix, last_word_of_street_name)

        CSV format: city, prefix, street_name, link

        Usage:
            flask add-links-from-csv --city "Poznań"
            flask add-links-from-csv --city "Poznań" --csv-file poznan_streets.csv
            flask add-links-from-csv --city "Poznań" --dry-run
            flask add-links-from-csv --city "Poznań" --user-id 1
        """
        with app.app_context():
            # Get user using utility function
            user, error = _get_user_or_default(user_id)
            if error:
                click.echo(f"❌ {error}")
                return

            # Initialize street matching service
            matching_service = StreetMatchingService(db.session)

            # Get default streets lookup
            default_lookup, default_streets = matching_service.get_default_streets_lookup(
                user.id, city
            )

            if not default_streets:
                click.echo(f"❌ No default streets found for city '{city}'.")
                click.echo("   Please import default streets for this city first.")
                return

            click.echo("Adding links from CSV to default streets:")
            click.echo(f"  CSV file: {csv_file}")
            click.echo(f"  City: {city}")
            click.echo(f"  User: {user.email}")
            click.echo(f"  Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
            click.echo(f"  Default streets available: {len(default_streets)}")
            click.echo()

            # Load CSV streets
            try:
                csv_streets = _load_csv_streets(csv_file, city)
            except click.ClickException as e:
                click.echo(f"❌ {str(e)}")
                return

            if not csv_streets:
                click.echo(f"❌ No streets found in CSV for city '{city}'.")
                return

            click.echo(f"Loaded {len(csv_streets)} streets from CSV.")
            click.echo()

            # Match CSV streets to default streets
            matches, not_matched, duplicates = _match_csv_to_defaults(csv_streets, default_lookup)

            click.echo(f"Found {len(matches)} matches ({len(not_matched)} not matched).")
            if duplicates:
                click.echo(f"Found {len(duplicates)} duplicate matches.")
            click.echo()

            # Handle duplicates interactively
            duplicate_choices = {}
            if duplicates:
                duplicate_choices = _handle_duplicates(duplicates, default_lookup, dry_run)

            # Process matches
            links_added = 0
            links_skipped = 0
            links_created = 0

            click.echo("Processing matches...")
            click.echo()

            for csv_entry, default_street in matches:
                # Check if this match was in duplicates and user chose differently
                if default_street.id in duplicate_choices:
                    choice = duplicate_choices[default_street.id]
                    if choice is None:
                        # User chose to skip
                        default_display = _format_street_display_name(default_street)
                        csv_display = f"{csv_entry['prefix']} {csv_entry['street_name']}"
                        click.echo(f"  ⊘ {csv_display} → {default_display} (skipped by user)")
                        links_skipped += 1
                        continue
                    elif isinstance(choice, list):
                        # User chose to append all - add all links at once
                        all_links = [dup_entry["link"] for dup_entry in choice]
                        success, message = _add_links_to_street_content(
                            default_street, all_links, user.id, dry_run
                        )
                        if success:
                            if message == "created":
                                links_created += 1
                            else:
                                links_added += 1
                            default_display = _format_street_display_name(default_street)
                            click.echo(
                                f"  ✅ {len(choice)} links added to {default_display} "
                                f"({'DRY RUN' if dry_run else 'saved'})"
                            )
                        else:
                            links_skipped += 1
                            default_display = _format_street_display_name(default_street)
                            click.echo(f"  ⊘ {default_display} ({message})")
                        continue
                    else:
                        # User chose specific entry - use that instead
                        csv_entry = choice

                default_display = _format_street_display_name(default_street)
                csv_display = f"{csv_entry['prefix']} {csv_entry['street_name']}"

                success, message = _add_link_to_street_content(
                    default_street, csv_entry["link"], user.id, dry_run
                )

                if success:
                    if message == "created":
                        links_created += 1
                        click.echo(
                            f"  ✅ {csv_display} → {default_display} "
                            f"(created StreetContent, link added) {'[DRY RUN]' if dry_run else ''}"
                        )
                    else:
                        links_added += 1
                        click.echo(
                            f"  ✅ {csv_display} → {default_display} "
                            f"(link added) {'[DRY RUN]' if dry_run else ''}"
                        )
                else:
                    links_skipped += 1
                    click.echo(f"  ⊘ {csv_display} → {default_display} ({message})")

            # Process duplicate choices that weren't in regular matches
            for default_id, choice in duplicate_choices.items():
                if default_id in [m[1].id for m in matches]:
                    continue  # Already processed above

                # Find default street
                default_street = None
                for street in default_lookup.values():
                    if street.id == default_id:
                        default_street = street
                        break

                if not default_street or choice is None:
                    continue

                if isinstance(choice, list):
                    # User chose to append all - add all links at once
                    all_links = [dup_entry["link"] for dup_entry in choice]
                    success, message = _add_links_to_street_content(
                        default_street, all_links, user.id, dry_run
                    )
                    if success:
                        if message == "created":
                            links_created += 1
                        else:
                            links_added += 1
                    else:
                        links_skipped += 1
                else:
                    success, message = _add_link_to_street_content(
                        default_street, choice["link"], user.id, dry_run
                    )
                    if success:
                        if message == "created":
                            links_created += 1
                        else:
                            links_added += 1
                    else:
                        links_skipped += 1

            # Show unmatched streets
            if not_matched:
                click.echo()
                click.echo("Streets not matched:")
                for csv_entry in not_matched[:20]:  # Show first 20
                    csv_display = f"{csv_entry['prefix']} {csv_entry['street_name']}"
                    click.echo(f"  ✗ {csv_display}")
                if len(not_matched) > 20:
                    click.echo(f"  ... and {len(not_matched) - 20} more")

            # Show summary
            click.echo()
            click.echo("=" * 60)
            click.echo("Summary:")
            click.echo(f"  CSV streets processed: {len(csv_streets)}")
            click.echo(f"  Matches found: {len(matches)}")
            click.echo(f"  Links added: {links_added}")
            click.echo(f"  StreetContent records created: {links_created}")
            click.echo(f"  Links skipped (existing): {links_skipped}")
            click.echo(f"  Not matched: {len(not_matched)}")
            if duplicates:
                click.echo(f"  Duplicate matches: {len(duplicates)}")
            if dry_run:
                click.echo()
                click.echo("  ℹ️  This was a dry run. No changes were saved to the database.")
                click.echo("  Run without --dry-run to save the links.")
            else:
                click.echo()
                click.echo(
                    f"  ✅ {links_added + links_created} links have been saved to the database!"
                )
            click.echo("=" * 60)

    @app.cli.command("copy-districts-from-default")
    @click.option("--city", required=True, help="City name")
    @click.option("--decade", required=True, help="Decade (e.g. '1940-1949')")
    @click.option("--user-id", type=int, help="User ID (defaults to first user)")
    @click.option("--dry-run", is_flag=True, help="Perform copying without saving to database")
    def copy_districts_from_default(city, decade, user_id, dry_run):
        """Copy district information from default streets to mapped streets.

        This command analyzes all streets in a given city/decade dictionary and
        copies district information from their mapped default streets. Only streets
        that currently have no district (None) will be updated.

        Usage:
            flask copy-districts-from-default --city "Poznań" --decade "1940-1949"
            flask copy-districts-from-default --city "Poznań" --decade "1940-1949" --dry-run
            flask copy-districts-from-default --city "Poznań" --decade "1940-1949" --user-id 1
        """
        with app.app_context():
            # Get user using utility function
            user, error = _get_user_or_default(user_id)
            if error:
                click.echo(f"❌ {error}")
                return

            click.echo("Copying districts from default dictionary:")
            click.echo(f"  City: {city}")
            click.echo(f"  Decade: {decade}")
            click.echo(f"  User: {user.email}")
            click.echo(f"  Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
            click.echo()

            # Query streets for the given city/decade that:
            # - Are NOT default streets (is_default_street=False)
            # - Are NOT rejected (is_rejected=False)
            # - Have a mapping to default street (default_street_id IS NOT NULL)
            # - Currently have no district (district IS NULL)
            streets = (
                Street.query.filter_by(
                    user_id=user.id,
                    city=city,
                    decade=decade,
                    is_default_street=False,
                    is_rejected=False,
                )
                .filter(Street.default_street_id.isnot(None))
                .filter(Street.district.is_(None))
                .order_by(Street.main_name)
                .all()
            )

            if not streets:
                click.echo(f"No streets found to process for {city} / {decade}.")
                click.echo("   Streets must have a default_street_id mapping and no district.")
                return

            click.echo(f"Found {len(streets)} streets with mappings and no district.")
            click.echo()

            # Process each street
            updated_count = 0
            skipped_count = 0

            for street in streets:
                # Load the mapped default street
                default_street = street.mapped_to_default_street

                if not default_street:
                    # This shouldn't happen if default_street_id is set, but handle it
                    street_display = _format_street_display_name(street)
                    click.echo(f"  ⚠️  {street_display} (default street not found)")
                    skipped_count += 1
                    continue

                # Check if default street has a district
                if not default_street.district:
                    street_display = _format_street_display_name(street)
                    default_display = _format_street_display_name(default_street)
                    click.echo(
                        f"  ⊘ {street_display} → {default_display} (default has no district)"
                    )
                    skipped_count += 1
                    continue

                # Copy district from default street
                street_display = _format_street_display_name(street)
                default_display = _format_street_display_name(default_street)

                if not dry_run:
                    street.district = default_street.district
                    db.session.add(street)
                    db.session.commit()

                click.echo(
                    f"  ✅ {street_display} → {default_display} "
                    f"(district: {default_street.district}) "
                    f"{'[DRY RUN]' if dry_run else ''}"
                )
                updated_count += 1

            # Show summary
            click.echo()
            click.echo("=" * 60)
            click.echo("Summary:")
            click.echo(f"  Total streets processed: {len(streets)}")
            click.echo(f"  Districts copied: {updated_count}")
            click.echo(f"  Skipped (no district in default): {skipped_count}")
            if dry_run:
                click.echo()
                click.echo("  ℹ️  This was a dry run. No changes were saved to the database.")
                click.echo("  Run without --dry-run to save the districts.")
            else:
                click.echo()
                click.echo(f"  ✅ {updated_count} districts have been saved to the database!")
            click.echo("=" * 60)
