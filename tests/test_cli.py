"""Tests for CLI commands."""

import os

import pytest
from click.testing import CliRunner

from app import create_app, db
from app.cli import register_cli_commands
from app.models.street import Street
from app.models.user import User

# Test constants
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"

TEST_CITY = "Poznań"
TEST_DECADE = "1940-1949"


@pytest.fixture
def app():
    """Create and configure a test app."""
    # Override DATABASE_URL after imports but before create_app
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Register CLI commands
        register_cli_commands(app)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cli_runner(app):
    """Create a CLI runner for testing commands."""
    return CliRunner()


class TestCopyDistrictsFromDefault:
    """Test copy-districts-from-default CLI command."""

    def test_successful_district_copying(self, app, cli_runner):
        """Test successful district copying from default streets."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create a default street with district
            default_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",  # Different decade for default
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district="Centrum",
                is_default_street=True,
                source="manual",
            )
            db.session.add(default_street)
            db.session.commit()

            # Create a source street with mapping but no district
            source_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district=None,  # No district
                is_default_street=False,
                default_street_id=default_street.id,
                source="ai",
            )
            db.session.add(source_street)
            db.session.commit()

            # Run the command
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                ],
            )

            # Verify command succeeded
            assert result.exit_code == 0
            assert "Copying districts from default dictionary" in result.output
            assert "Districts copied: 1" in result.output
            assert "Centrum" in result.output

            # Verify district was copied
            db.session.refresh(source_street)
            assert source_street.district == "Centrum"

    def test_dry_run_mode(self, app, cli_runner):
        """Test dry-run mode doesn't save changes."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create a default street with district
            default_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district="Centrum",
                is_default_street=True,
                source="manual",
            )
            db.session.add(default_street)
            db.session.commit()

            # Create a source street with mapping but no district
            source_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district=None,
                is_default_street=False,
                default_street_id=default_street.id,
                source="ai",
            )
            db.session.add(source_street)
            db.session.commit()

            # Run the command in dry-run mode
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                    "--dry-run",
                ],
            )

            # Verify command succeeded
            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            assert "Districts copied: 1" in result.output
            assert "This was a dry run" in result.output

            # Verify district was NOT copied
            db.session.refresh(source_street)
            assert source_street.district is None

    def test_no_streets_found(self, app, cli_runner):
        """Test when no streets are found for city/decade."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Run the command with no streets in database
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                ],
            )

            # Verify command succeeded but found nothing
            assert result.exit_code == 0
            assert "No streets found to process" in result.output

    def test_streets_without_mappings(self, app, cli_runner):
        """Test streets without default_street_id mappings are skipped."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create a source street without mapping
            source_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district=None,
                is_default_street=False,
                default_street_id=None,  # No mapping
                source="ai",
            )
            db.session.add(source_street)
            db.session.commit()

            # Run the command
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                ],
            )

            # Verify no streets were processed
            assert result.exit_code == 0
            assert "No streets found to process" in result.output

    def test_streets_with_existing_districts(self, app, cli_runner):
        """Test streets that already have districts are skipped."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create a default street with district
            default_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district="Centrum",
                is_default_street=True,
                source="manual",
            )
            db.session.add(default_street)
            db.session.commit()

            # Create a source street with mapping AND existing district
            source_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district="Old District",  # Already has district
                is_default_street=False,
                default_street_id=default_street.id,
                source="ai",
            )
            db.session.add(source_street)
            db.session.commit()

            # Run the command
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                ],
            )

            # Verify no streets were processed (they have districts already)
            assert result.exit_code == 0
            assert "No streets found to process" in result.output

            # Verify district was not changed
            db.session.refresh(source_street)
            assert source_street.district == "Old District"

    def test_default_streets_without_districts(self, app, cli_runner):
        """Test default streets without districts are skipped."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create a default street WITHOUT district
            default_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district=None,  # No district
                is_default_street=True,
                source="manual",
            )
            db.session.add(default_street)
            db.session.commit()

            # Create a source street with mapping but no district
            source_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district=None,
                is_default_street=False,
                default_street_id=default_street.id,
                source="ai",
            )
            db.session.add(source_street)
            db.session.commit()

            # Run the command
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                ],
            )

            # Verify command succeeded but skipped
            assert result.exit_code == 0
            assert "Skipped (no district in default): 1" in result.output
            assert "default has no district" in result.output

            # Verify district was not copied
            db.session.refresh(source_street)
            assert source_street.district is None

    def test_invalid_user_id(self, app, cli_runner):
        """Test with invalid user ID."""
        with app.app_context():
            # Run the command with invalid user ID (no user created)
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                    "--user-id",
                    "999",
                ],
            )

            # Verify command failed with error
            assert result.exit_code == 0  # Command exits with 0 but shows error
            assert "User with ID 999 not found" in result.output

    def test_multiple_streets_processing(self, app, cli_runner):
        """Test processing multiple streets."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create default streets with districts
            default_street1 = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district="Centrum",
                is_default_street=True,
                source="manual",
            )
            default_street2 = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",
                prefix="ul.",
                main_name="głogowska",
                main_name_cs="Głogowska",
                district="Jeżyce",
                is_default_street=True,
                source="manual",
            )
            db.session.add_all([default_street1, default_street2])
            db.session.commit()

            # Create source streets with mappings but no districts
            source_street1 = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district=None,
                is_default_street=False,
                default_street_id=default_street1.id,
                source="ai",
            )
            source_street2 = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="ul.",
                main_name="głogowska",
                main_name_cs="Głogowska",
                district=None,
                is_default_street=False,
                default_street_id=default_street2.id,
                source="ai",
            )
            db.session.add_all([source_street1, source_street2])
            db.session.commit()

            # Run the command
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                ],
            )

            # Verify command succeeded
            assert result.exit_code == 0
            assert "Districts copied: 2" in result.output

            # Verify districts were copied
            db.session.refresh(source_street1)
            db.session.refresh(source_street2)
            assert source_street1.district == "Centrum"
            assert source_street2.district == "Jeżyce"

    def test_rejected_streets_skipped(self, app, cli_runner):
        """Test rejected streets are skipped."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create a default street with district
            default_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district="Centrum",
                is_default_street=True,
                source="manual",
            )
            db.session.add(default_street)
            db.session.commit()

            # Create a rejected source street with mapping
            source_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district=None,
                is_default_street=False,
                default_street_id=default_street.id,
                is_rejected=True,  # Rejected
                source="ai",
            )
            db.session.add(source_street)
            db.session.commit()

            # Run the command
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    TEST_DECADE,
                ],
            )

            # Verify no streets were processed (rejected streets are skipped)
            assert result.exit_code == 0
            assert "No streets found to process" in result.output

    def test_default_streets_not_processed(self, app, cli_runner):
        """Test default streets themselves are not processed."""
        with app.app_context():
            # Create a test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create a default street with district
            default_street1 = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district="Centrum",
                is_default_street=True,
                source="manual",
            )
            db.session.add(default_street1)
            db.session.commit()

            # Create another default street that maps to the first (edge case)
            default_street2 = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade="2020-2029",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                district=None,
                is_default_street=True,  # Still a default street
                default_street_id=default_street1.id,
                source="manual",
            )
            db.session.add(default_street2)
            db.session.commit()

            # Run the command for the default decade
            result = cli_runner.invoke(
                app.cli,
                [
                    "copy-districts-from-default",
                    "--city",
                    TEST_CITY,
                    "--decade",
                    "2020-2029",
                ],
            )

            # Verify no streets were processed (default streets are skipped)
            assert result.exit_code == 0
            assert "No streets found to process" in result.output
