"""Tests for dictionaries API routes."""

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

TEST_STREET_DATA = {"prefix": "ul.", "main_name": "marszałkowska", "main_name_cs": "Marszałkowska"}


@pytest.fixture
def app():
    """Create and configure a test app."""
    # Set DATABASE_URL for testing configuration
    import os

    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """A test client with authenticated user."""
    # Create a user
    with app.app_context():
        user = User(email=TEST_USER_EMAIL)
        user.set_password(TEST_USER_PASSWORD)
        db.session.add(user)
        db.session.commit()

        # Login the user
        client.post(
            "/auth/login",
            data={"email": "test@example.com", "password": "password123"},
            follow_redirects=True,
        )

    return client


class TestDictionariesAPIAuth:
    """Test authentication requirements for dictionaries API."""

    def test_get_dictionaries_unauthenticated(self, client):
        """Test GET /api/dictionaries requires authentication."""
        response = client.get("/api/dictionaries")
        # Flask-Login redirects to login instead of 401
        assert response.status_code == 302

    def test_get_dictionaries_streets_unauthenticated(self, client):
        """Test GET /api/dictionaries/{city}/{decade}/streets/json requires authentication."""
        response = client.get("/api/dictionaries/Poznań/1940-1949/streets/json")
        # Flask-Login redirects to login instead of 401
        assert response.status_code == 302

    def test_get_dictionaries_streets_txt_unauthenticated(self, client):
        """Test GET /api/dictionaries/{city}/{decade}/streets/txt requires authentication."""
        response = client.get("/api/dictionaries/Poznań/1940-1949/streets/txt")
        # Flask-Login redirects to login instead of 401
        assert response.status_code == 302


class TestDictionariesAPI:
    """Test dictionaries API endpoints."""

    def test_get_dictionaries_empty(self, auth_client):
        """Test GET /api/dictionaries with no data."""
        response = auth_client.get("/api/dictionaries")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "dictionaries" in data
        assert "total_dictionaries" in data
        assert "total_streets" in data
        assert data["dictionaries"] == []
        assert data["total_dictionaries"] == 0
        assert data["total_streets"] == 0

    def test_get_dictionaries_with_data(self, auth_client, app):
        """Test GET /api/dictionaries with street data."""
        # Create test data
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()

            # Create streets for different cities/decades
            streets_data = [
                ("Poznań", "1940-1949", "marszałkowska"),
                ("Poznań", "1940-1949", "krakowskie przedmieście"),
                ("Poznań", "1950-1959", "puławska"),
                ("Kraków", "1930-1939", "rynek główny"),
            ]

            for city, decade, name in streets_data:
                street = Street(
                    user_id=user.id,
                    city=city,
                    decade=decade,
                    main_name=name.lower(),
                    main_name_cs=name.title(),
                    source="ai",
                )
                db.session.add(street)
            db.session.commit()

        response = auth_client.get("/api/dictionaries")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["total_dictionaries"] == 3  # 3 unique city-decade combinations
        assert data["total_streets"] == 4

        dictionaries = data["dictionaries"]
        assert len(dictionaries) == 3

        # Check sorting (by city, then decade descending)
        assert dictionaries[0]["city"] == "Kraków"
        assert dictionaries[0]["decade"] == "1930-1939"
        assert dictionaries[0]["street_count"] == 1

        assert dictionaries[1]["city"] == "Poznań"
        assert dictionaries[1]["decade"] == "1950-1959"
        assert dictionaries[1]["street_count"] == 1

        assert dictionaries[2]["city"] == "Poznań"
        assert dictionaries[2]["decade"] == "1940-1949"
        assert dictionaries[2]["street_count"] == 2

    def test_get_dictionaries_streets_json_success(self, auth_client, app):
        """Test GET /api/dictionaries/{city}/{decade}/streets/json."""
        # Create test data
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()

            streets_data = [
                (
                    "Poznań",
                    "1940-1949",
                    "marszałkowska",
                    "ul.",
                    "Marszałkowska",
                    ["Marsa"],
                    ["Marszałkowskia"],
                ),
                (
                    "Poznań",
                    "1940-1949",
                    "krakowskie przedmieście",
                    "ul.",
                    "Krakowskie Przedmieście",
                    [],
                    [],
                ),
            ]

            for (
                city,
                decade,
                main_name,
                prefix,
                main_name_cs,
                variants,
                misspellings,
            ) in streets_data:
                street = Street(
                    user_id=user.id,
                    city=city,
                    decade=decade,
                    prefix=prefix,
                    main_name=main_name,
                    main_name_cs=main_name_cs,
                    variants=json.dumps(variants),
                    misspellings=json.dumps(misspellings),
                    source="ai",
                )
                db.session.add(street)
            db.session.commit()

        response = auth_client.get("/api/dictionaries/Poznań/1940-1949/streets/json")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "dictionary" in data
        assert "streets" in data
        assert "pagination" in data

        assert data["dictionary"]["city"] == "Poznań"
        assert data["dictionary"]["decade"] == "1940-1949"
        assert data["dictionary"]["total_streets"] == 2

        assert len(data["streets"]) == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 50
        assert data["pagination"]["total"] == 2

        # Check streets data (order may vary due to sorting)
        streets = data["streets"]
        assert len(streets) == 2

        # Find specific streets by main_name
        marszalkowska_street = next(s for s in streets if s["main_name"] == "marszałkowska")
        krakowskie_street = next(s for s in streets if s["main_name"] == "krakowskie przedmieście")

        # Check Marszałkowska street
        assert "id" in marszalkowska_street
        assert marszalkowska_street["prefix"] == "ul."
        assert marszalkowska_street["main_name"] == "marszałkowska"
        assert marszalkowska_street["main_name_cs"] == "Marszałkowska"
        assert marszalkowska_street["variants"] == ["Marsa"]
        assert marszalkowska_street["misspellings"] == ["Marszałkowskia"]

        # Check Krakowskie Przedmieście street
        assert krakowskie_street["prefix"] == "ul."
        assert krakowskie_street["main_name"] == "krakowskie przedmieście"
        assert krakowskie_street["main_name_cs"] == "Krakowskie Przedmieście"
        assert krakowskie_street["variants"] == []
        assert krakowskie_street["misspellings"] == []

    def test_get_dictionaries_streets_json_not_found(self, auth_client):
        """Test GET /api/dictionaries/{city}/{decade}/streets/json with no data."""
        response = auth_client.get("/api/dictionaries/NonExistent/1900-1909/streets/json")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "No streets found" in data["error"]

    def test_get_dictionaries_streets_json_pagination(self, auth_client, app):
        """Test pagination in GET /api/dictionaries/{city}/{decade}/streets/json."""
        # Create many streets
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()

            for i in range(5):
                street = Street(
                    user_id=user.id,
                    city="Poznań",
                    decade="1940-1949",
                    main_name=f"street_{i}",
                    main_name_cs=f"Street {i}",
                    source="ai",
                )
                db.session.add(street)
            db.session.commit()

        # Test page 1 with per_page=2
        response = auth_client.get(
            "/api/dictionaries/Poznań/1940-1949/streets/json?page=1&per_page=2"
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data["streets"]) == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 2
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["total_pages"] == 3

        # Test page 2
        response = auth_client.get(
            "/api/dictionaries/Poznań/1940-1949/streets/json?page=2&per_page=2"
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data["streets"]) == 2
        assert data["pagination"]["page"] == 2

    def test_get_dictionaries_streets_json_filter_source(self, auth_client, app):
        """Test source filtering in GET /api/dictionaries/{city}/{decade}/streets/json."""
        # Create streets with different sources
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()

            streets_data = [
                ("ai_street", "ai"),
                ("manual_street", "manual"),
                ("another_ai", "ai"),
            ]

            for main_name, source in streets_data:
                street = Street(
                    user_id=user.id,
                    city="Poznań",
                    decade="1940-1949",
                    main_name=main_name,
                    main_name_cs=main_name.title(),
                    source=source,
                )
                db.session.add(street)
            db.session.commit()

        # Filter by AI source
        response = auth_client.get("/api/dictionaries/Poznań/1940-1949/streets/json?source=ai")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data["streets"]) == 2
        for street in data["streets"]:
            assert street["source"] == "ai"

        # Filter by manual source
        response = auth_client.get("/api/dictionaries/Poznań/1940-1949/streets/json?source=manual")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data["streets"]) == 1
        assert data["streets"][0]["source"] == "manual"

    def test_get_dictionaries_streets_txt_success(self, auth_client, app):
        """Test GET /api/dictionaries/{city}/{decade}/streets/txt."""
        # Create test data
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()

            streets_data = [
                ("Marszałkowska", "marszałkowska"),
                ("Krakowskie Przedmieście", "krakowskie przedmieście"),
            ]

            for main_name_cs, main_name in streets_data:
                street = Street(
                    user_id=user.id,
                    city="Poznań",
                    decade="1940-1949",
                    main_name=main_name,
                    main_name_cs=main_name_cs,
                    source="ai",
                )
                db.session.add(street)
            db.session.commit()

        response = auth_client.get("/api/dictionaries/Poznań/1940-1949/streets/txt")
        assert response.status_code == 200

        # Should return plain text
        text = response.data.decode("utf-8")
        lines = text.strip().split("\n")
        assert len(lines) == 2
        assert "Marszałkowska" in lines
        assert "Krakowskie Przedmieście" in lines

    def test_get_dictionaries_streets_txt_empty(self, auth_client):
        """Test GET /api/dictionaries/{city}/{decade}/streets/txt with no data."""
        response = auth_client.get("/api/dictionaries/Empty/1900-1909/streets/txt")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "No streets found" in data["error"]

    def test_get_dictionaries_streets_txt_wrong_user(self, auth_client, app):
        """Test GET /api/dictionaries/{city}/{decade}/streets/txt for different user."""
        # Create another user with streets
        with app.app_context():
            other_user = User(email="other@example.com")
            other_user.set_password("password")
            db.session.add(other_user)
            db.session.commit()

            street = Street(
                user_id=other_user.id,
                city="Kraków",
                decade="1930-1939",
                main_name="rynek_główny",
                main_name_cs="Rynek Główny",
            )
            db.session.add(street)
            db.session.commit()

        # Try to access other user's data - should return 404 since no streets for current user
        response = auth_client.get("/api/dictionaries/Kraków/1930-1939/streets/txt")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "No streets found" in data["error"]


class TestDictionaryDelete:
    """Test cases for dictionary deletion functionality."""

    def test_delete_dictionary_success(self, auth_client, app):
        """Test successful dictionary deletion."""
        # Create test streets and source map
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()
            from app.models.source_maps import SourceMaps

            # Create streets
            street1 = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
            )
            street2 = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                main_name="piłsudskiego",
                main_name_cs="Piłsudskiego",
            )
            # Include a rejected street to ensure total count reflects all rows
            rejected_street = Street(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                main_name="rejected_name",
                main_name_cs="Rejected Name",
                is_rejected=True,
            )
            db.session.add(street1)
            db.session.add(street2)
            db.session.add(rejected_street)

            # Create source map
            source_map = SourceMaps(
                user_id=user.id,
                city=TEST_CITY,
                decade=TEST_DECADE,
                original_filename="test_map.jpg",
                gcs_filename="test_gcs_filename.jpg",
                gcs_url="https://storage.googleapis.com/test/test_gcs_filename.jpg",
                streets_count=2,
            )
            db.session.add(source_map)
            db.session.commit()

        # Delete the dictionary
        response = auth_client.delete(f"/api/dictionaries/{TEST_CITY}/{TEST_DECADE}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "message" in data
        assert "deleted successfully" in data["message"]
        assert data["deleted_streets"] == 3
        assert data["deleted_active_streets"] == 2

        # Verify streets are deleted
        with app.app_context():
            remaining_streets = Street.query.filter_by(city=TEST_CITY, decade=TEST_DECADE).all()
            assert len(remaining_streets) == 0

            # Verify source map is deleted
            remaining_source_maps = SourceMaps.query.filter_by(
                city=TEST_CITY, decade=TEST_DECADE
            ).all()
            assert len(remaining_source_maps) == 0

    def test_delete_dictionary_not_found(self, auth_client):
        """Test deleting non-existent dictionary."""
        response = auth_client.delete("/api/dictionaries/NonExistentCity/1990-1999")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"]

    def test_delete_dictionary_wrong_user(self, auth_client, app):
        """Test deleting dictionary that belongs to another user."""
        # Create another user with their own dictionary
        with app.app_context():
            other_user = User(email="other@example.com")
            other_user.set_password("password123")
            db.session.add(other_user)
            db.session.commit()

            street = Street(
                user_id=other_user.id,
                city="Warszawa",
                decade="1950-1959",
                main_name="nowy_świat",
                main_name_cs="Nowy Świat",
            )
            db.session.add(street)
            db.session.commit()

        # Try to delete other user's dictionary - should return 404
        response = auth_client.delete("/api/dictionaries/Warszawa/1950-1959")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"]

    def test_delete_dictionary_only_rejected_streets(self, auth_client, app):
        """Test deleting dictionary with only rejected streets returns 404."""
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()

            # Create only rejected streets
            street = Street(
                user_id=user.id,
                city="RejectedCity",
                decade="1960-1969",
                main_name="rejected_street",
                main_name_cs="Rejected Street",
                is_rejected=True,
            )
            db.session.add(street)
            db.session.commit()

        # Try to delete - should return 404 since no non-rejected streets
        response = auth_client.delete("/api/dictionaries/RejectedCity/1960-1969")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"]

    def test_delete_dictionary_unauthenticated(self, client):
        """Test DELETE /api/dictionaries/{city}/{decade} requires authentication."""
        response = client.delete("/api/dictionaries/TestCity/2000-2009")
        # Flask-Login redirects to login instead of 401
        assert response.status_code == 302

    def test_delete_dictionary_partial_success(self, auth_client, app):
        """Test dictionary deletion when some streets exist but source map doesn't."""
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()

            # Create streets but no source map
            street = Street(
                user_id=user.id,
                city="PartialCity",
                decade="1970-1979",
                main_name="partial_street",
                main_name_cs="Partial Street",
            )
            db.session.add(street)
            db.session.commit()

        # Delete should still work
        response = auth_client.delete("/api/dictionaries/PartialCity/1970-1979")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["deleted_streets"] == 1
        assert data["deleted_active_streets"] == 1

        # Verify street is deleted
        with app.app_context():
            remaining_streets = Street.query.filter_by(city="PartialCity", decade="1970-1979").all()
            assert len(remaining_streets) == 0
