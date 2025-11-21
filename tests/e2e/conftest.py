"""Configuration for end-to-end tests."""

import os
import time
from collections.abc import Generator

import pytest
from playwright.sync_api import BrowserContext, Page

# Test configuration
TEST_BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:5000")
TEST_USER_EMAIL = "test2@example.com"
TEST_USER_PASSWORD = "testpassword123"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "record_video_dir": "test-results/videos/" if os.getenv("CI") else None,
        "record_har_path": "test-results/har/" if os.getenv("CI") else None,
    }


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Provide a fresh page for each test."""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_app():
    """Set up test application and database."""
    # Start the Flask app in background if not already running
    # For now, assume the app is already running on TEST_BASE_URL
    # In CI, you might want to start it programmatically

    # Wait a moment for app to be ready
    time.sleep(1)


@pytest.fixture
def logged_in_page(page: Page) -> Page:
    """Provide a page with a logged-in user."""
    # Navigate to login page
    page.goto(f"{TEST_BASE_URL}/auth/login")

    # Fill login form
    page.fill("#email", TEST_USER_EMAIL)
    page.fill("#password", TEST_USER_PASSWORD)
    page.click("button[type='submit']")

    # Wait for redirect to upload page (successful login)
    page.wait_for_url(f"{TEST_BASE_URL}/")

    return page


@pytest.fixture
def test_user():
    """Test user credentials."""
    return {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
