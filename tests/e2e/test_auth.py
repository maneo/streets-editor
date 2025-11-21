"""End-to-end tests for authentication."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_successful_login(page: Page, test_user):
    """Test successful user login."""
    # Navigate to login page
    page.goto("/auth/login")

    # Verify we're on login page
    expect(page).to_have_title("Login - Streets Dictionary Editor")

    # Fill login form
    page.fill("#email", test_user["email"])
    page.fill("#password", test_user["password"])

    # Submit form
    page.click("button[type='submit']")

    # Should redirect to upload page after successful login
    expect(page).to_have_url("/")
    expect(page.locator("h1")).to_contain_text("Upload")


@pytest.mark.e2e
def test_failed_login_wrong_password(page: Page, test_user):
    """Test login with wrong password."""
    page.goto("/auth/login")

    # Fill form with wrong password
    page.fill("#email", test_user["email"])
    page.fill("#password", "wrongpassword")

    # Submit form
    page.click("button[type='submit']")

    # Should stay on login page with error message
    expect(page).to_have_url("/auth/login")
    # Check for flash message (this might need adjustment based on how flashes are displayed)
    expect(page.locator("body")).to_contain_text("Invalid email or password")


@pytest.mark.e2e
def test_failed_login_empty_fields(page: Page):
    """Test login with empty fields."""
    page.goto("/auth/login")

    # Try to submit empty form
    page.click("button[type='submit']")

    # Should stay on login page
    expect(page).to_have_url("/auth/login")


@pytest.mark.e2e
def test_logout_functionality(logged_in_page: Page):
    """Test logout functionality."""
    # We start with logged in page
    expect(logged_in_page).to_have_url("/")

    # Find and click logout link/button
    # This might be in a nav bar or dropdown - adjust selector as needed
    logged_in_page.click("text=Logout")

    # Should redirect to login page
    expect(logged_in_page).to_have_url("/auth/login")
    expect(logged_in_page.locator("h1")).to_contain_text("Login")
