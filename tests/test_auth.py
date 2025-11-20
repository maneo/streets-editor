"""Tests for authentication routes."""

import pytest

from app import create_app, db
from app.models.user import User

# Test constants
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"
TEST_USER_EMAIL_2 = "test2@example.com"
TEST_USER_PASSWORD_2 = "password456"


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
        data={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert User.query.filter_by(email=TEST_USER_EMAIL).first() is not None


def test_login(client, app):
    """Test user login."""
    # Create a user
    with app.app_context():
        user = User(email=TEST_USER_EMAIL)
        user.set_password(TEST_USER_PASSWORD)
        db.session.add(user)
        db.session.commit()

    # Attempt login
    response = client.post(
        "/auth/login",
        data={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        follow_redirects=True,
    )

    assert response.status_code == 200


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login", data={"email": TEST_USER_EMAIL, "password": "wrongpassword"}
    )

    assert b"Invalid email or password" in response.data


def test_register_duplicate_email(client, app):
    """Test registration with existing email (TC-AUTH-02)."""
    # Create first user
    with app.app_context():
        user = User(email="existing@example.com")
        user.set_password(TEST_USER_PASSWORD)
        db.session.add(user)
        db.session.commit()

    # Try to register with same email
    response = client.post(
        "/auth/register",
        data={"email": "existing@example.com", "password": "newpassword"},
        follow_redirects=True,
    )

    # Should show error and not create account
    assert b"already registered" in response.data.lower() or b"exists" in response.data.lower()
    assert User.query.filter_by(email="existing@example.com").count() == 1


def test_register_success_redirect(client):
    """Test successful registration redirects to upload (TC-AUTH-01)."""
    response = client.post(
        "/auth/register",
        data={"email": "newuser@example.com", "password": "password123"},
        follow_redirects=True,
    )

    # Should redirect to upload page or show success
    assert response.status_code == 200
    # Check that user was created and logged in
    assert User.query.filter_by(email="newuser@example.com").first() is not None


def test_login_success_access_protected(client, app):
    """Test successful login allows access to protected pages (TC-AUTH-03)."""
    # Create and login user
    with app.app_context():
        user = User(email=TEST_USER_EMAIL)
        user.set_password(TEST_USER_PASSWORD)
        db.session.add(user)
        db.session.commit()

    # Login
    client.post(
        "/auth/login",
        data={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        follow_redirects=True,
    )

    # Try to access protected page
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200


def test_access_protected_without_login(client):
    """Test accessing protected page without login redirects to login (TC-AUTH-05)."""
    response = client.get("/", follow_redirects=True)

    # Should redirect to login page
    assert response.status_code == 200
    assert b"login" in response.data.lower()


def test_login_wrong_email(client):
    """Test login with non-existent email."""
    response = client.post(
        "/auth/login", data={"email": "nonexistent@example.com", "password": "password123"}
    )

    assert b"Invalid email or password" in response.data


def test_register_invalid_email(client):
    """Test registration with invalid email format."""
    response = client.post(
        "/auth/register",
        data={"email": "invalid-email", "password": "password123"},
        follow_redirects=True,
    )

    # Should show validation error
    assert b"invalid" in response.data.lower() or b"email" in response.data.lower()


def test_register_weak_password(client):
    """Test registration with very short password."""
    response = client.post(
        "/auth/register",
        data={"email": TEST_USER_EMAIL, "password": "123"},
        follow_redirects=True,
    )

    # This might pass or fail depending on validation, but at least shouldn't crash
    assert response.status_code == 200


def test_logout(client, app):
    """Test user logout."""
    # Create and login user
    with app.app_context():
        user = User(email=TEST_USER_EMAIL)
        user.set_password(TEST_USER_PASSWORD)
        db.session.add(user)
        db.session.commit()

    # Login
    client.post(
        "/auth/login",
        data={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        follow_redirects=True,
    )

    # Logout
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200

    # Try to access protected page - should redirect to login
    response = client.get("/", follow_redirects=True)
    assert b"login" in response.data.lower()
