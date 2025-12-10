"""Tests for JSON import service."""

import json
import os
import tempfile

import pytest

from app import create_app, db
from app.models.street import Street
from app.models.user import User
from app.services.json_import import import_streets_from_json


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(app):
    """Create a test user."""
    with app.app_context():
        user = User(email="test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user.id


def create_temp_json_file(data):
    """Helper to create a temporary JSON file."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def test_import_valid_json(app, test_user):
    """Test importing valid JSON data."""
    with app.app_context():
        data = [
            {
                "main_name": "27 grudnia",
                "variants": ["27—go Grudnia"],
                "misspellings": ["27 grnri", "2710 grudnia"],
                "prefix": "ul.",
                "display_name": "ul. 27 Grudnia",
                "main_name_cs": "27 Grudnia",
            },
            {
                "main_name": "wolności",
                "variants": [],
                "misspellings": [],
                "prefix": "pl.",
                "display_name": "pl. Wolności",
                "main_name_cs": "Wolności",
            },
        ]

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 2
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 0

            # Verify streets in database
            streets = Street.query.filter_by(user_id=test_user, city="Poznań").all()
            assert len(streets) == 2

            # Check first street
            street1 = Street.query.filter_by(main_name="27 grudnia").first()
            assert street1 is not None
            assert street1.main_name_cs == "27 Grudnia"
            assert street1.prefix == "ul."
            assert street1.source == "json"
            assert street1.is_default_street is False
            assert json.loads(street1.variants) == ["27—go Grudnia"]
            assert json.loads(street1.misspellings) == ["27 grnri", "2710 grudnia"]

            # Check second street
            street2 = Street.query.filter_by(main_name="wolności").first()
            assert street2 is not None
            assert street2.main_name_cs == "Wolności"
            assert street2.prefix == "pl."
            assert json.loads(street2.variants) == []
            assert json.loads(street2.misspellings) == []

        finally:
            os.unlink(filepath)


def test_import_duplicate_streets_skipped(app, test_user):
    """Test that duplicate streets are skipped."""
    with app.app_context():
        # Create existing street
        existing = Street(
            user_id=test_user,
            city="Poznań",
            decade="1940-1949",
            prefix="ul.",
            main_name="27 grudnia",
            main_name_cs="27 Grudnia",
            source="manual",
        )
        db.session.add(existing)
        db.session.commit()

        data = [
            {
                "main_name": "27 grudnia",
                "variants": ["27—go Grudnia"],
                "misspellings": [],
                "prefix": "ul.",
                "display_name": "ul. 27 Grudnia",
                "main_name_cs": "27 Grudnia",
            },
            {
                "main_name": "nowa",
                "variants": [],
                "misspellings": [],
                "prefix": "ul.",
                "display_name": "ul. Nowa",
                "main_name_cs": "Nowa",
            },
        ]

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 1
            assert summary["skipped"] == 1
            assert len(summary["errors"]) == 0

            # Verify only one new street was added
            streets = Street.query.filter_by(user_id=test_user, city="Poznań").all()
            assert len(streets) == 2

            # Verify existing street was not modified
            existing_street = Street.query.filter_by(main_name="27 grudnia").first()
            assert existing_street.source == "manual"  # Not changed to "json"

        finally:
            os.unlink(filepath)


def test_import_missing_required_fields(app, test_user):
    """Test that streets with missing required fields are rejected."""
    with app.app_context():
        data = [
            {
                "main_name": "27 grudnia",
                "variants": ["27—go Grudnia"],
                # Missing misspellings, prefix, display_name, main_name_cs
            },
            {
                "main_name": "wolności",
                "variants": [],
                "misspellings": [],
                "prefix": "pl.",
                "display_name": "pl. Wolności",
                "main_name_cs": "Wolności",
            },
        ]

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 1
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 1
            assert "missing required fields" in summary["errors"][0].lower()

        finally:
            os.unlink(filepath)


def test_import_invalid_prefix(app, test_user):
    """Test that streets with invalid prefixes are rejected."""
    with app.app_context():
        data = [
            {
                "main_name": "test",
                "variants": [],
                "misspellings": [],
                "prefix": "invalid_prefix",
                "display_name": "invalid_prefix Test",
                "main_name_cs": "Test",
            }
        ]

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 0
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 1
            assert "invalid prefix" in summary["errors"][0].lower()

        finally:
            os.unlink(filepath)


def test_import_invalid_json_format(app, test_user):
    """Test that invalid JSON format is handled."""
    with app.app_context():
        fd, filepath = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("{ invalid json }")

            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 0
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 1
            assert "invalid json" in summary["errors"][0].lower()

        finally:
            os.unlink(filepath)


def test_import_non_array_json(app, test_user):
    """Test that non-array JSON is rejected."""
    with app.app_context():
        data = {"main_name": "test", "variants": []}  # Object instead of array

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 0
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 1
            assert "array" in summary["errors"][0].lower()

        finally:
            os.unlink(filepath)


def test_import_empty_json_array(app, test_user):
    """Test importing empty JSON array."""
    with app.app_context():
        data = []

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 0
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 0

        finally:
            os.unlink(filepath)


def test_import_invalid_field_types(app, test_user):
    """Test that invalid field types are rejected."""
    with app.app_context():
        data = [
            {
                "main_name": "test",
                "variants": "not an array",  # Should be array
                "misspellings": [],
                "prefix": "ul.",
                "display_name": "ul. Test",
                "main_name_cs": "Test",
            }
        ]

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 0
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 1
            assert "variants must be an array" in summary["errors"][0].lower()

        finally:
            os.unlink(filepath)


def test_import_empty_main_name(app, test_user):
    """Test that empty main_name is rejected."""
    with app.app_context():
        data = [
            {
                "main_name": "",
                "variants": [],
                "misspellings": [],
                "prefix": "ul.",
                "display_name": "ul. ",
                "main_name_cs": "",
            }
        ]

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 0
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 1
            assert "main_name" in summary["errors"][0].lower()

        finally:
            os.unlink(filepath)


def test_import_batch_processing(app, test_user):
    """Test that large imports use batch processing."""
    with app.app_context():
        # Create a large dataset (more than batch size)
        data = []
        for i in range(100):
            data.append(
                {
                    "main_name": f"street {i}",
                    "variants": [],
                    "misspellings": [],
                    "prefix": "ul.",
                    "display_name": f"ul. Street {i}",
                    "main_name_cs": f"Street {i}",
                }
            )

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 100
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 0

            # Verify all streets in database
            streets = Street.query.filter_by(user_id=test_user, city="Poznań").all()
            assert len(streets) == 100

        finally:
            os.unlink(filepath)


def test_import_unicode_characters(app, test_user):
    """Test importing streets with Unicode characters."""
    with app.app_context():
        data = [
            {
                "main_name": "świętego marcina",
                "variants": ["Św. Marcina"],
                "misspellings": ["swietego marcina"],
                "prefix": "ul.",
                "display_name": "ul. Świętego Marcina",
                "main_name_cs": "Świętego Marcina",
            }
        ]

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 1
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 0

            street = Street.query.filter_by(main_name="świętego marcina").first()
            assert street is not None
            assert street.main_name_cs == "Świętego Marcina"
            assert json.loads(street.variants) == ["Św. Marcina"]

        finally:
            os.unlink(filepath)


def test_import_normalized_prefix(app, test_user):
    """Test that prefixes are normalized correctly."""
    with app.app_context():
        data = [
            {
                "main_name": "test1",
                "variants": [],
                "misspellings": [],
                "prefix": "UL.",  # Uppercase
                "display_name": "UL. Test1",
                "main_name_cs": "Test1",
            },
            {
                "main_name": "test2",
                "variants": [],
                "misspellings": [],
                "prefix": "  pl.  ",  # With whitespace
                "display_name": "pl. Test2",
                "main_name_cs": "Test2",
            },
        ]

        filepath = create_temp_json_file(data)
        try:
            summary = import_streets_from_json(filepath, test_user, "Poznań", "1940-1949")

            assert summary["inserted"] == 2
            assert summary["skipped"] == 0
            assert len(summary["errors"]) == 0

            street1 = Street.query.filter_by(main_name="test1").first()
            assert street1.prefix == "ul."

            street2 = Street.query.filter_by(main_name="test2").first()
            assert street2.prefix == "pl."

        finally:
            os.unlink(filepath)
