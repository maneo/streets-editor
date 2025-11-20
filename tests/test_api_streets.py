"""Tests for streets API routes."""

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
        user = User(email="test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        # Login the user
        client.post(
            "/auth/login",
            data={"email": "test@example.com", "password": "password123"},
            follow_redirects=True,
        )

    return client


class TestStreetsAPIAuth:
    """Test authentication requirements for streets API."""

    def test_post_street_unauthenticated(self, client):
        """Test POST /api/streets requires authentication."""
        response = client.post(
            "/api/streets",
            json={"city": "Poznań", "decade": "1940-1949", "main_name": "Test Street"},
        )
        # Flask-Login redirects to login instead of 401
        assert response.status_code == 302

    def test_get_street_unauthenticated(self, client, app):
        """Test GET /api/streets/{id} requires authentication."""
        with app.app_context():
            # Create a user and street
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                main_name="test_street",
                main_name_cs="Test Street",
            )
            db.session.add(street)
            db.session.commit()
            street_id = street.id

        response = client.get(f"/api/streets/{street_id}")
        # Flask-Login redirects to login instead of 401
        assert response.status_code == 302

    def test_put_street_unauthenticated(self, client, app):
        """Test PUT /api/streets/{id} requires authentication."""
        with app.app_context():
            # Create a user and street
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                main_name="test_street",
                main_name_cs="Test Street",
            )
            db.session.add(street)
            db.session.commit()
            street_id = street.id

        response = client.put(f"/api/streets/{street_id}", json={"main_name": "Updated Street"})
        # Flask-Login redirects to login instead of 401
        assert response.status_code == 302

    def test_delete_street_unauthenticated(self, client, app):
        """Test DELETE /api/streets/{id} requires authentication."""
        with app.app_context():
            # Create a user and street
            user = User(email=TEST_USER_EMAIL)
            user.set_password(TEST_USER_PASSWORD)
            db.session.add(user)
            db.session.commit()

            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                main_name="test_street",
                main_name_cs="Test Street",
            )
            db.session.add(street)
            db.session.commit()
            street_id = street.id

        response = client.delete(f"/api/streets/{street_id}")
        # Flask-Login redirects to login instead of 401
        assert response.status_code == 302


class TestStreetsAPICrud:
    """Test CRUD operations for streets API."""

    def test_post_street_success(self, auth_client, app):
        """Test successful street creation."""
        response = auth_client.post(
            "/api/streets",
            json={
                "city": "Poznań",
                "decade": "1940-1949",
                "prefix": "ul.",
                "main_name": "Marszałkowska",
                "variants": ["Marsa"],
                "misspellings": ["Marszałkowskia"],
            },
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "id" in data
        assert data["prefix"] == "ul."
        assert data["main_name"] == "Marszałkowska"

        # Verify in database
        with app.app_context():
            street = Street.query.get(data["id"])
            assert street is not None
            assert street.city == "Poznań"
            assert street.decade == "1940-1949"
            assert street.main_name == "marszałkowska"  # lowercase
            assert street.main_name_cs == "Marszałkowska"

    def test_post_street_minimal_data(self, auth_client, app):
        """Test street creation with minimal required data."""
        response = auth_client.post(
            "/api/streets",
            json={"city": "Poznań", "decade": "1940-1949", "main_name": "Test Street"},
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["prefix"] == "ul."  # default
        assert data["main_name"] == "Test Street"

    def test_post_street_duplicate(self, auth_client, app):
        """Test creating duplicate street fails."""
        # Create first street
        auth_client.post(
            "/api/streets",
            json={"city": "Poznań", "decade": "1940-1949", "main_name": "Marszałkowska"},
        )

        # Try to create duplicate
        response = auth_client.post(
            "/api/streets",
            json={"city": "Poznań", "decade": "1940-1949", "main_name": "Marszałkowska"},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "already exists" in data["error"].lower()

    def test_post_street_missing_required_fields(self, auth_client):
        """Test street creation with missing required fields."""
        # Missing city
        response = auth_client.post(
            "/api/streets", json={"decade": "1940-1949", "main_name": "Test Street"}
        )
        assert response.status_code == 400

        # Missing decade
        response = auth_client.post(
            "/api/streets", json={"city": "Poznań", "main_name": "Test Street"}
        )
        assert response.status_code == 400

        # Missing main_name
        response = auth_client.post("/api/streets", json={"city": "Poznań", "decade": "1940-1949"})
        assert response.status_code == 400

    def test_get_street_success(self, auth_client, app):
        """Test successful street retrieval."""
        # Create a street first
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()
            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
                variants=json.dumps(["Marsa"]),
                misspellings=json.dumps(["Marszałkowskia"]),
                source="ai",
            )
            db.session.add(street)
            db.session.commit()
            street_id = street.id

        response = auth_client.get(f"/api/streets/{street_id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["id"] == street_id
        assert data["city"] == "Poznań"
        assert data["decade"] == "1940-1949"
        assert data["prefix"] == "ul."
        assert data["main_name"] == "marszałkowska"
        assert data["main_name_cs"] == "Marszałkowska"
        assert data["variants"] == ["Marsa"]
        assert data["misspellings"] == ["Marszałkowskia"]
        assert data["source"] == "ai"
        assert data["is_rejected"] is False

    def test_get_street_not_found(self, auth_client):
        """Test getting non-existent street."""
        response = auth_client.get("/api/streets/999")
        assert response.status_code == 404

    def test_get_street_wrong_user(self, auth_client, app):
        """Test getting street from different user."""
        # Create another user and their street
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
            street_id = street.id

        response = auth_client.get(f"/api/streets/{street_id}")
        assert response.status_code == 403

    def test_put_street_success(self, auth_client, app):
        """Test successful street update."""
        # Create a street first
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()
            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
            )
            db.session.add(street)
            db.session.commit()
            street_id = street.id

        # Update the street
        response = auth_client.put(
            f"/api/streets/{street_id}",
            json={
                "prefix": "pl.",
                "main_name": "Marszałkowska Square",
                "variants": ["Marsa", "Marsz"],
                "misspellings": ["Marszałkowskia", "Marszałkowska"],
            },
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data

        # Verify in database
        with app.app_context():
            updated_street = Street.query.get(street_id)
            assert updated_street.prefix == "pl."
            assert updated_street.main_name == "marszałkowska square"  # updated to lowercase
            assert updated_street.main_name_cs == "Marszałkowska Square"
            assert json.loads(updated_street.variants) == ["Marsa", "Marsz"]

    def test_put_street_partial_update(self, auth_client, app):
        """Test partial street update."""
        # Create a street first
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()
            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                prefix="ul.",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
            )
            db.session.add(street)
            db.session.commit()
            street_id = street.id

        # Update only prefix
        response = auth_client.put(f"/api/streets/{street_id}", json={"prefix": "al."})

        assert response.status_code == 200

        # Verify in database
        with app.app_context():
            updated_street = Street.query.get(street_id)
            assert updated_street.prefix == "al."
            assert updated_street.main_name == "marszałkowska"  # unchanged

    def test_put_street_not_found(self, auth_client):
        """Test updating non-existent street."""
        response = auth_client.put("/api/streets/999", json={"prefix": "pl."})
        assert response.status_code == 404

    def test_put_street_wrong_user(self, auth_client, app):
        """Test updating street from different user."""
        # Create another user and their street
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
            street_id = street.id

        response = auth_client.put(f"/api/streets/{street_id}", json={"prefix": "pl."})
        assert response.status_code == 403

    def test_delete_street_success(self, auth_client, app):
        """Test successful street deletion (soft delete)."""
        # Create a street first
        with app.app_context():
            user = User.query.filter_by(email=TEST_USER_EMAIL).first()
            street = Street(
                user_id=user.id,
                city="Poznań",
                decade="1940-1949",
                main_name="marszałkowska",
                main_name_cs="Marszałkowska",
            )
            db.session.add(street)
            db.session.commit()
            street_id = street.id

        # Delete the street
        response = auth_client.delete(f"/api/streets/{street_id}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data

        # Verify soft delete in database
        with app.app_context():
            deleted_street = Street.query.get(street_id)
            assert deleted_street.is_rejected is True

    def test_delete_street_not_found(self, auth_client):
        """Test deleting non-existent street."""
        response = auth_client.delete("/api/streets/999")
        assert response.status_code == 404

    def test_delete_street_wrong_user(self, auth_client, app):
        """Test deleting street from different user."""
        # Create another user and their street
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
            street_id = street.id

        response = auth_client.delete(f"/api/streets/{street_id}")
        assert response.status_code == 403
