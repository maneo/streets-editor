"""Tests for authentication routes."""

import pytest

from app import create_app, db
from app.models.user import User


@pytest.fixture
def app():
    """Create and configure a test app."""
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


def test_register(client):
    """Test user registration."""
    response = client.post(
        "/auth/register",
        data={"email": "test@example.com", "password": "password123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert User.query.filter_by(email="test@example.com").first() is not None


def test_login(client, app):
    """Test user login."""
    # Create a user
    with app.app_context():
        user = User(email="test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    # Attempt login
    response = client.post(
        "/auth/login",
        data={"email": "test@example.com", "password": "password123"},
        follow_redirects=True,
    )

    assert response.status_code == 200


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login", data={"email": "test@example.com", "password": "wrongpassword"}
    )

    assert b"Invalid email or password" in response.data
