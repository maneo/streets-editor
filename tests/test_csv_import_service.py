"""Tests for service modules."""

import json
import os
from unittest.mock import Mock, patch

import pytest

from app import create_app, db
from app.models.street import Street
from app.models.user import User
from app.services.csv_import import import_streets_from_csv
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


class TestBatchInsertion:
    """Test batch insertion functionality for street uploads."""

    def test_batch_insertion_success(self, app):
        """Test successful batch insertion of streets."""
        with app.app_context():
            # Create test user
            user = User(email=TEST_USER_EMAIL, password_hash="dummy")
            db.session.add(user)
            db.session.commit()

            # Simulate extracted streets (more than batch size)
            batch_size = app.config["BATCH_INSERT_SIZE"]  # Should be 50
            num_streets = batch_size + 10  # 60 streets to test multiple batches

            extracted_streets = []
            for i in range(num_streets):
                extracted_streets.append({"prefix": "ul.", "main_name": f"Test Street {i}"})

            # Simulate the batch insertion logic from upload.py
            inserted_count = 0
            for i in range(0, len(extracted_streets), batch_size):
                batch = extracted_streets[i : i + batch_size]

                for street_data in batch:
                    street = Street(
                        user_id=user.id,
                        city=TEST_CITY,
                        decade=TEST_DECADE,
                        prefix=street_data.get("prefix", "ul."),
                        main_name=street_data["main_name"].lower(),
                        main_name_cs=street_data["main_name"],
                        source="ai",
                    )
                    db.session.add(street)

                db.session.commit()
                inserted_count += len(batch)

            # Verify all streets were inserted
            assert inserted_count == num_streets
            streets_in_db = Street.query.filter_by(
                user_id=user.id, city=TEST_CITY, decade=TEST_DECADE
            ).all()
            assert len(streets_in_db) == num_streets

            # Verify street data is correct (sort by ID to get insertion order)
            streets_in_db_sorted = sorted(streets_in_db, key=lambda s: s.id)
            for i, street in enumerate(streets_in_db_sorted):
                assert street.main_name == f"test street {i}"
                assert street.main_name_cs == f"Test Street {i}"
                assert street.prefix == "ul."
                assert street.source == "ai"

    def test_batch_insertion_partial_failure(self, app):
        """Test batch insertion with partial failures."""
        with app.app_context():
            # Create test user
            user = User(email=TEST_USER_EMAIL, password_hash="dummy")
            db.session.add(user)
            db.session.commit()

            # Simulate extracted streets
            batch_size = 3  # Small batch for testing
            extracted_streets = [
                {"prefix": "ul.", "main_name": "Street 1"},
                {"prefix": "ul.", "main_name": "Street 2"},
                {"prefix": "ul.", "main_name": "Street 3"},
                {"prefix": "ul.", "main_name": "Street 4"},
            ]

            # Mock db.session.commit to fail on second batch
            original_commit = db.session.commit
            call_count = 0

            def mock_commit():
                nonlocal call_count
                call_count += 1
                if call_count == 2:  # Fail on second batch
                    db.session.rollback()
                    raise Exception("Database timeout")
                return original_commit()

            db.session.commit = mock_commit

            try:
                # Simulate the batch insertion logic
                inserted_count = 0
                for i in range(0, len(extracted_streets), batch_size):
                    batch = extracted_streets[i : i + batch_size]

                    for street_data in batch:
                        street = Street(
                            user_id=user.id,
                            city=TEST_CITY,
                            decade=TEST_DECADE,
                            prefix=street_data.get("prefix", "ul."),
                            main_name=street_data["main_name"].lower(),
                            main_name_cs=street_data["main_name"],
                            source="ai",
                        )
                        db.session.add(street)

                    try:
                        db.session.commit()
                        inserted_count += len(batch)
                    except Exception:
                        db.session.rollback()
                        continue  # Continue with next batch

                # Should have inserted first batch (3 streets) but not second batch (1 street)
                assert inserted_count == 3
                streets_in_db = Street.query.filter_by(
                    user_id=user.id, city=TEST_CITY, decade=TEST_DECADE
                ).all()
                assert len(streets_in_db) == 3

            finally:
                # Restore original commit
                db.session.commit = original_commit


class TestCSVImport:
    """Test CSV street import service."""

    def test_import_valid_csv(self, app, tmp_path):
        """Test importing valid CSV with all required fields."""
        with app.app_context():
            # Create test user
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create CSV file
            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul.,Marszałkowska,Grunwald
Poznań,pl.,Piłsudskiego,Jeżyce
Poznań,al.,Niepodległości,Nowe Miasto"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 3
            assert result["updated"] == 0
            assert result["skipped_city"] == 0
            assert len(result["errors"]) == 0

            # Verify streets in database
            streets = Street.query.filter_by(
                user_id=user.id, city=TEST_CITY, decade=TEST_DECADE
            ).all()
            assert len(streets) == 3

            # Check first street
            street1 = Street.query.filter_by(main_name="marszałkowska").first()
            assert street1 is not None
            assert street1.prefix == "ul."
            assert street1.main_name_cs == "Marszałkowska"
            assert street1.district == "Grunwald"
            assert street1.source == "csv"

    def test_import_csv_with_prefix_normalization(self, app, tmp_path):
        """Test prefix normalization (ul -> ul., etc.)."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul,Marszałkowska,Grunwald
Poznań,ul.,Piłsudskiego,Jeżyce
Poznań,al,Nowa,Nowe Miasto
Poznań,al.,Stara,Stare Miasto
Poznań,pl,Centrum,Centrum
Poznań,os,Osiedle,Osiedle"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 6
            assert len(result["errors"]) == 0

            # Check normalized prefixes
            street1 = Street.query.filter_by(main_name="marszałkowska").first()
            assert street1.prefix == "ul."

            street2 = Street.query.filter_by(main_name="nowa").first()
            assert street2.prefix == "al."

            street3 = Street.query.filter_by(main_name="centrum").first()
            assert street3.prefix == "pl."

            street4 = Street.query.filter_by(main_name="osiedle").first()
            assert street4.prefix == "os."

    def test_import_csv_with_unknown_prefixes(self, app, tmp_path):
        """Test handling of unknown prefixes (should keep as-is but track)."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul.,Marszałkowska,Grunwald
Poznań,unknown_prefix,Test Street,District
Poznań,another_unknown,Another Street,District"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 3
            assert len(result["unknown_prefixes"]) == 2
            assert "unknown_prefix" in result["unknown_prefixes"]
            assert "another_unknown" in result["unknown_prefixes"]

            # Verify unknown prefixes are stored (truncated to 10 chars if needed)
            street2 = Street.query.filter_by(main_name="test street").first()
            assert street2.prefix == "unknown_pr"  # Truncated to 10 characters

    def test_import_csv_city_mismatch(self, app, tmp_path):
        """Test skipping rows with city mismatch."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul.,Marszałkowska,Grunwald
Warszawa,ul.,Krakowskie Przedmieście,Śródmieście
Poznań,pl.,Piłsudskiego,Jeżyce
Kraków,ul.,Floriańska,Stare Miasto"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 2
            assert result["skipped_city"] == 2
            assert len(result["errors"]) == 0

            # Verify only Poznań streets were imported
            streets = Street.query.filter_by(
                user_id=user.id, city=TEST_CITY, decade=TEST_DECADE
            ).all()
            assert len(streets) == 2
            assert all(s.main_name_cs in ["Marszałkowska", "Piłsudskiego"] for s in streets)

    def test_import_csv_duplicate_update(self, app, tmp_path):
        """Test updating existing streets when duplicates are found."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create existing street
            existing = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix="pl.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska Old",
                district="Old District",
                source="manual",
            )
            db.session.add(existing)
            db.session.commit()

            # Import CSV with same street name but different data
            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul.,Marszałkowska,New District
Poznań,pl.,Piłsudskiego,Jeżyce"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 1  # Only Piłsudskiego
            assert result["updated"] == 1  # Marszałkowska updated

            # Verify update
            updated = Street.query.filter_by(main_name="marszałkowska").first()
            assert updated.prefix == "ul."  # Updated
            assert updated.main_name_cs == "Marszałkowska"  # Updated
            assert updated.district == "New District"  # Updated
            assert updated.source == "csv"  # Updated
            assert updated.is_rejected is False  # Should be un-rejected

    def test_import_csv_missing_street_name(self, app, tmp_path):
        """Test error handling for missing street_name_cs."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul.,Marszałkowska,Grunwald
Poznań,pl.,,Jeżyce
Poznań,al.,Niepodległości,Nowe Miasto"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 2
            assert len(result["errors"]) == 1
            assert "Row 2" in result["errors"][0]
            assert "street_name_cs is required" in result["errors"][0]

    def test_import_csv_invalid_row_format(self, app, tmp_path):
        """Test error handling for rows with wrong number of columns."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul.,Marszałkowska,Grunwald
Poznań,pl.,Piłsudskiego
Poznań,al.,Niepodległości,Nowe Miasto,Extra Column
Poznań,skwer"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 1  # Only first valid row
            assert len(result["errors"]) == 3
            assert any("Row 2" in e and "expected 4 columns" in e for e in result["errors"])
            assert any("Row 3" in e and "expected 4 columns" in e for e in result["errors"])
            assert any("Row 4" in e and "expected 4 columns" in e for e in result["errors"])

    def test_import_csv_empty_district(self, app, tmp_path):
        """Test handling of empty/blank district field."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul.,Marszałkowska,Grunwald
Poznań,pl.,Piłsudskiego,
Poznań,al.,Niepodległości,  """
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 3
            assert len(result["errors"]) == 0

            # Check districts
            street1 = Street.query.filter_by(main_name="marszałkowska").first()
            assert street1.district == "Grunwald"

            street2 = Street.query.filter_by(main_name="piłsudskiego").first()
            assert street2.district is None

            street3 = Street.query.filter_by(main_name="niepodległości").first()
            assert street3.district is None

    def test_import_csv_empty_prefix_defaults_to_ul(self, app, tmp_path):
        """Test that empty prefix defaults to 'ul.'."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,,Marszałkowska,Grunwald
Poznań,  ,Piłsudskiego,Jeżyce"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 2

            # Check default prefix
            street1 = Street.query.filter_by(main_name="marszałkowska").first()
            assert street1.prefix == "ul."

            street2 = Street.query.filter_by(main_name="piłsudskiego").first()
            assert street2.prefix == "ul."

    def test_import_csv_case_insensitive_city_matching(self, app, tmp_path):
        """Test that city matching is case-insensitive."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """poznań,ul.,Marszałkowska,Grunwald
POZNAŃ,pl.,Piłsudskiego,Jeżyce
Poznań,al.,Niepodległości,Nowe Miasto"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 3
            assert result["skipped_city"] == 0

            # All should be imported with correct city (from parameter, not CSV)
            streets = Street.query.filter_by(
                user_id=user.id, city=TEST_CITY, decade=TEST_DECADE
            ).all()
            assert len(streets) == 3
            assert all(s.city == TEST_CITY for s in streets)

    def test_import_csv_batch_commits(self, app, tmp_path):
        """Test that batch commits work correctly."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Set small batch size for testing
            original_batch_size = app.config["BATCH_INSERT_SIZE"]
            app.config["BATCH_INSERT_SIZE"] = 3

            try:
                # Create CSV with more rows than batch size
                csv_file = tmp_path / "test_streets.csv"
                rows = []
                for i in range(7):  # 7 rows, batch size 3 = 3 batches
                    rows.append(f"Poznań,ul.,Street {i},District {i}")
                csv_file.write_text("\n".join(rows), encoding="utf-8")

                result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

                assert result["inserted"] == 7
                assert len(result["errors"]) == 0

                # Verify all streets are in database
                streets = Street.query.filter_by(
                    user_id=user.id, city=TEST_CITY, decade=TEST_DECADE
                ).all()
                assert len(streets) == 7
            finally:
                app.config["BATCH_INSERT_SIZE"] = original_batch_size

    def test_import_csv_all_prefix_types(self, app, tmp_path):
        """Test importing streets with all allowed prefix types."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            csv_file = tmp_path / "test_streets.csv"
            csv_content = """Poznań,ul.,Ulica,Grunwald
Poznań,al.,Aleja,Jeżyce
Poznań,pl.,Plac,Nowe Miasto
Poznań,-,Bez Prefiks,Stare Miasto
Poznań,skwer,Skwer,Centrum
Poznań,wiadukt,Wiadukt,Osiedle
Poznań,zaułek,Zaułek,District
Poznań,os.,Osiedle,District
Poznań,park,Park,District
Poznań,rondo,Rondo,District
Poznań,tunel,Tunel,District
Poznań,most,Most,District
Poznań,rynek,Rynek,District
Poznań,droga,Droga,District"""
            csv_file.write_text(csv_content, encoding="utf-8")

            result = import_streets_from_csv(str(csv_file), user.id, TEST_CITY, TEST_DECADE)

            assert result["inserted"] == 14
            assert len(result["errors"]) == 0
            assert len(result["unknown_prefixes"]) == 0

            # Verify all prefixes are correct
            prefixes = {
                s.prefix
                for s in Street.query.filter_by(
                    user_id=user.id, city=TEST_CITY, decade=TEST_DECADE
                ).all()
            }
            expected_prefixes = {
                "ul.",
                "al.",
                "pl.",
                "-",
                "skwer",
                "wiadukt",
                "zaułek",
                "os.",
                "park",
                "rondo",
                "tunel",
                "most",
                "rynek",
                "droga",
            }
            assert prefixes == expected_prefixes
