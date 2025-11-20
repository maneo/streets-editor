"""Tests for service modules."""

import json
import os
from unittest.mock import Mock, patch

import pytest

from app import create_app, db
from app.models.street import Street
from app.models.user import User
from app.services.export_service import generate_json_export, generate_txt_export
from app.services.file_handler import allowed_file, save_upload, validate_file

# Test constants
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"
TEST_CITY = "Poznań"
TEST_DECADE = "1940-1949"

TEST_STREET_DATA = {"prefix": "ul.", "main_name": "marszałkowska", "main_name_cs": "Marszałkowska"}


@pytest.fixture
def app():
    """Create and configure a test app."""
    # Set DATABASE_URL for testing configuration
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestFileHandler:
    """Test file handling utilities."""

    def test_allowed_file_valid_extensions(self, app):
        """Test allowed_file function with valid extensions."""
        with app.app_context():
            assert allowed_file("test.png") is True
            assert allowed_file("test.jpg") is True
            assert allowed_file("test.jpeg") is True
            assert allowed_file("TEST.PNG") is True

    def test_allowed_file_invalid_extensions(self, app):
        """Test allowed_file function with invalid extensions."""
        with app.app_context():
            assert allowed_file("test.txt") is False
            assert allowed_file("test.pdf") is False
            assert allowed_file("test") is False
            assert allowed_file("") is False

    def test_allowed_file_no_extension(self, app):
        """Test allowed_file function with no extension."""
        with app.app_context():
            assert allowed_file("test") is False
            assert allowed_file("test.") is False

    @patch("app.services.file_handler.Image")
    def test_validate_file_valid_image(self, mock_image, app):
        """Test validate_file with valid image file."""
        with app.app_context():
            # Create a mock file
            mock_file = Mock()
            mock_file.filename = "test.png"
            mock_file.seek = Mock()
            mock_file.tell = Mock(return_value=1024)  # 1KB file

            # Mock PIL Image
            mock_img = Mock()
            mock_image.open.return_value = mock_img
            mock_img.verify = Mock()

            result = validate_file(mock_file)
            assert result is None  # No error

    def test_validate_file_no_file(self, app):
        """Test validate_file with no file provided."""
        with app.app_context():
            result = validate_file(None)
            assert result == "No file provided."

    def test_validate_file_no_filename(self, app):
        """Test validate_file with empty filename."""
        with app.app_context():
            mock_file = Mock()
            mock_file.filename = ""
            mock_file.seek = Mock()

            result = validate_file(mock_file)
            assert result == "No file selected."

    def test_validate_file_invalid_extension(self, app):
        """Test validate_file with invalid file extension."""
        with app.app_context():
            mock_file = Mock()
            mock_file.filename = "test.txt"

            result = validate_file(mock_file)
            assert result == "Invalid file type. Only JPG and PNG files are allowed."

    def test_validate_file_too_large(self, app):
        """Test validate_file with file exceeding size limit."""
        with app.app_context():
            mock_file = Mock()
            mock_file.filename = "test.png"
            mock_file.seek = Mock()
            mock_file.tell = Mock(return_value=60 * 1024 * 1024)  # 60MB

            result = validate_file(mock_file)
            assert "File size exceeds maximum limit" in result

    @patch("app.services.file_handler.Image")
    def test_validate_file_corrupted_image(self, mock_image, app):
        """Test validate_file with corrupted image."""
        with app.app_context():
            mock_file = Mock()
            mock_file.filename = "test.png"
            mock_file.seek = Mock()
            mock_file.tell = Mock(return_value=1024)

            # Mock PIL Image to raise exception
            mock_image.open.side_effect = Exception("Invalid image")

            result = validate_file(mock_file)
            assert result == "Invalid image file."

    @patch("app.services.file_handler.os.makedirs")
    @patch("app.services.file_handler.os.path.join")
    def test_save_upload(self, mock_join, mock_makedirs, app):
        """Test save_upload function."""
        with app.app_context():
            mock_join.return_value = "/tmp/test_1_test.png"

            mock_file = Mock()
            mock_file.filename = "test.png"
            mock_file.save = Mock()

            result = save_upload(mock_file, 1)

            assert result == "/tmp/test_1_test.png"
            mock_makedirs.assert_called_once()
            mock_file.save.assert_called_once_with("/tmp/test_1_test.png")


class TestExportService:
    """Test export service functions."""

    def test_generate_txt_export(self, app):
        """Test TXT export generation."""
        with app.app_context():
            # Create test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create test streets
            streets = [
                Street(
                    user_id=user.id,
                    city="Poznań",
                    decade="1940-1949",
                    prefix="ul.",
                    main_name="marszałkowska",
                    main_name_cs="Marszałkowska",
                ),
                Street(
                    user_id=user.id,
                    city="Poznań",
                    decade="1940-1949",
                    prefix="pl.",
                    main_name="piłsudskiego",
                    main_name_cs="Piłsudskiego",
                ),
            ]

            for street in streets:
                db.session.add(street)
            db.session.commit()

            result = generate_txt_export(streets)

            expected_lines = ["Marszałkowska", "Piłsudskiego"]
            assert result == "\n".join(expected_lines)

    def test_generate_txt_export_empty_list(self, app):
        """Test TXT export with empty street list."""
        with app.app_context():
            result = generate_txt_export([])
            assert result == ""

    def test_generate_json_export(self, app):
        """Test JSON export generation."""
        with app.app_context():
            # Create test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create test streets
            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                variants=json.dumps(["Marsa", "Marsz"]),
                misspellings=json.dumps(["Marszałkowskia"]),
            )
            db.session.add(street)
            db.session.commit()

            result = generate_json_export([street], "Poznań", "1940-1949")

            parsed = json.loads(result)
            assert parsed["city"] == "Poznań"
            assert parsed["decade"] == "1940-1949"
            assert len(parsed["streets"]) == 1

            street_data = parsed["streets"][0]
            assert street_data["prefix"] == "ul."
            assert street_data["main_name"] == "marszałkowska"
            assert street_data["main_name_cs"] == "Marszałkowska"
            assert street_data["display_name"] == "ul. Marszałkowska"
            assert street_data["variants"] == ["Marsa", "Marsz"]
            assert street_data["misspellings"] == ["Marszałkowskia"]

    def test_generate_json_export_empty_list(self, app):
        """Test JSON export with empty street list."""
        with app.app_context():
            result = generate_json_export([], "Poznań", "1940-1949")

            parsed = json.loads(result)
            assert parsed["city"] == "Poznań"
            assert parsed["decade"] == "1940-1949"
            assert parsed["streets"] == []

    def test_generate_json_export_multiple_streets(self, app):
        """Test JSON export with multiple streets."""
        with app.app_context():
            # Create test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create test streets
            streets = [
                Street(
                    user_id=user.id,
                    city="Poznań",
                    decade="1940-1949",
                    prefix="ul.",
                    main_name="marszałkowska",
                    main_name_cs="Marszałkowska",
                ),
                Street(
                    user_id=user.id,
                    city="Poznań",
                    decade="1940-1949",
                    prefix="-",
                    main_name="rynek główny",
                    main_name_cs="Rynek Główny",
                ),
            ]

            for street in streets:
                db.session.add(street)
            db.session.commit()

            result = generate_json_export(streets, "Poznań", "1940-1949")

            parsed = json.loads(result)
            assert len(parsed["streets"]) == 2

            # Check first street (with prefix)
            assert parsed["streets"][0]["display_name"] == "ul. Marszałkowska"

            # Check second street (no prefix)
            assert parsed["streets"][1]["display_name"] == "Rynek Główny"
