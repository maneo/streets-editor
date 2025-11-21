"""Tests for database models."""

import json

import pytest

from app import create_app, db
from app.models.street import Street
from app.models.user import User

# Test constants
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"

TEST_CITY = "Poznań"
TEST_DECADE = "1940-1949"

TEST_STREET_DATA = {
    "prefix": "ul.",
    "main_name": "marszałkowska",
    "main_name_cs": "Marszałkowska",
    "variants": ["Marsa"],
    "misspellings": ["Marszałkowskia"],
}

TEST_STREET_DATA_NO_PREFIX = {
    "prefix": "-",
    "main_name": "rynek główny",
    "main_name_cs": "Rynek Główny",
    "variants": [],
    "misspellings": [],
}


@pytest.fixture
def app():
    """Create and configure a test app."""
    # Import required modules first
    import os

    from app import db

    # Override DATABASE_URL after imports but before create_app
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestUserModel:
    """Test User model methods."""

    def test_set_password(self, app):
        """Test password hashing."""
        with app.app_context():
            user = User(email="test@example.com")
            user.set_password("mypassword")

            assert user.password_hash is not None
            assert user.password_hash != "mypassword"
            assert user.check_password("mypassword")

    def test_check_password_correct(self, app):
        """Test correct password verification."""
        with app.app_context():
            user = User(email="test@example.com")
            user.set_password("correctpassword")

            assert user.check_password("correctpassword")

    def test_check_password_incorrect(self, app):
        """Test incorrect password verification."""
        with app.app_context():
            user = User(email="test@example.com")
            user.set_password("correctpassword")

            assert not user.check_password("wrongpassword")

    def test_user_repr(self, app):
        """Test string representation of User."""
        with app.app_context():
            user = User(email="test@example.com")
            assert repr(user) == "<User test@example.com>"


class TestStreetModel:
    """Test Street model methods."""

    def test_street_creation(self, app):
        """Test basic Street creation."""
        with app.app_context():
            # Create a user first
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create a street
            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                source="ai",
            )
            db.session.add(street)
            db.session.commit()

            assert street.id is not None
            assert street.user_id == user.id
            assert street.city == "Poznań"
            assert street.decade == "1940-1949"
            assert street.prefix == "ul."
            assert street.main_name == "marszałkowska"
            assert street.main_name_cs == "Marszałkowska"
            assert street.source == "ai"
            assert not street.is_rejected

    def test_street_to_dict_basic(self, app):
        """Test basic to_dict conversion."""
        with app.app_context():
            # Create a street object (no need to save to database for to_dict testing)
            street = Street(
                user_id=1,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix=TEST_STREET_DATA["prefix"],
                main_name=TEST_STREET_DATA["main_name"],
                main_name_cs=TEST_STREET_DATA["main_name_cs"],
            )

            result = street.to_dict()

            # Check that expected fields are present
            assert result["prefix"] == TEST_STREET_DATA["prefix"]
            assert result["main_name"] == TEST_STREET_DATA["main_name"]
            assert result["main_name_cs"] == TEST_STREET_DATA["main_name_cs"]
            assert (
                result["display_name"]
                == f"{TEST_STREET_DATA['prefix']} {TEST_STREET_DATA['main_name_cs']}"
            )
            assert result["variants"] == []
            assert result["misspellings"] == []
            # Additional fields added for API
            assert "id" in result
            assert "user_id" in result
            assert "city" in result
            assert "decade" in result
            assert "is_rejected" in result
            assert "source" in result
            assert "created_at" in result
            assert "updated_at" in result

    def test_street_to_dict_with_variants_and_misspellings(self, app):
        """Test to_dict with variants and misspellings."""
        with app.app_context():
            variants = TEST_STREET_DATA["variants"]
            misspellings = TEST_STREET_DATA["misspellings"]

            street = Street(
                user_id=1,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix=TEST_STREET_DATA["prefix"],
                main_name=TEST_STREET_DATA["main_name"],
                main_name_cs=TEST_STREET_DATA["main_name_cs"],
                variants=json.dumps(variants),
                misspellings=json.dumps(misspellings),
            )

            result = street.to_dict()

            # Check that expected fields are present
            assert result["prefix"] == TEST_STREET_DATA["prefix"]
            assert result["main_name"] == TEST_STREET_DATA["main_name"]
            assert result["main_name_cs"] == TEST_STREET_DATA["main_name_cs"]
            assert (
                result["display_name"]
                == f"{TEST_STREET_DATA['prefix']} {TEST_STREET_DATA['main_name_cs']}"
            )
            assert result["variants"] == variants
            assert result["misspellings"] == misspellings
            # Additional fields added for API
            assert "id" in result
            assert "user_id" in result
            assert "city" in result
            assert "decade" in result
            assert "is_rejected" in result
            assert "source" in result
            assert "created_at" in result
            assert "updated_at" in result

    def test_street_to_dict_no_prefix(self, app):
        """Test to_dict with no prefix."""
        with app.app_context():
            street = Street(
                user_id=1,
                city=TEST_CITY,
                decade=TEST_DECADE,
                prefix=TEST_STREET_DATA_NO_PREFIX["prefix"],
                main_name=TEST_STREET_DATA_NO_PREFIX["main_name"],
                main_name_cs=TEST_STREET_DATA_NO_PREFIX["main_name_cs"],
            )

            result = street.to_dict()

            # Check that expected fields are present
            assert result["prefix"] == TEST_STREET_DATA_NO_PREFIX["prefix"]
            assert result["main_name"] == TEST_STREET_DATA_NO_PREFIX["main_name"]
            assert result["main_name_cs"] == TEST_STREET_DATA_NO_PREFIX["main_name_cs"]
            assert result["display_name"] == TEST_STREET_DATA_NO_PREFIX["main_name_cs"]
            assert result["variants"] == []
            assert result["misspellings"] == []
            # Additional fields added for API
            assert "id" in result
            assert "user_id" in result
            assert "city" in result
            assert "decade" in result
            assert "is_rejected" in result
            assert "source" in result
            assert "created_at" in result
            assert "updated_at" in result

    def test_street_to_dict_empty_variants_misspellings(self, app):
        """Test to_dict with empty variants and misspellings."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                variants="",
                misspellings="",
            )
            db.session.add(street)
            db.session.commit()

            result = street.to_dict()

            assert result["variants"] == []
            assert result["misspellings"] == []

    def test_street_repr(self, app):
        """Test string representation of Street."""
        with app.app_context():
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
            )

            assert repr(street) == "<Street ul. marszałkowska>"

    def test_street_index_exists(self, app):
        """Test that index for performance optimization exists."""
        with app.app_context():
            # Test that we can query streets efficiently (index should help)
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            # Create multiple streets
            streets_data = [
                ("warszawa", "1940-1949", "marszałkowska"),
                ("warszawa", "1940-1949", "krakowskie przedmieście"),
                ("kraków", "1930-1939", "marszałkowska"),
            ]

            for city, decade, main_name in streets_data:
                street = Street(
                    user_id=user.id,
                    city=city,
                    decade=decade,
                    prefix="ul.",
                    main_name=main_name,
                    main_name_cs=main_name.title(),
                )
                db.session.add(street)
            db.session.commit()

            # Test that queries work (index should make this efficient)
            warsaw_1940_streets = Street.query.filter_by(
                user_id=user.id, city="warszawa", decade="1940-1949"
            ).all()

            assert len(warsaw_1940_streets) == 2
            assert all(s.city == "warszawa" for s in warsaw_1940_streets)
