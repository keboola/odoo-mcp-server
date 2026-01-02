"""
Playwright Tests for Odoo Login Flow

These tests verify the actual Odoo login experience using browser automation.
They document the expected authentication flow that the MCP server must integrate with.

Run with:
  xvfb-run pytest tests/e2e/test_odoo_login_flow.py -v
  HEADED=true pytest tests/e2e/test_odoo_login_flow.py -v  # See browser
"""

import os
import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.browser, pytest.mark.odoo]

ODOO_URL = os.getenv("ODOO_URL", "https://erp.internal.keboola.com")


@pytest.fixture
async def browser():
    """Launch Playwright browser."""
    pytest.importorskip("playwright.async_api")
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=os.getenv("HEADED", "true").lower() != "true"
            )
        except Exception as e:
            pytest.skip(f"Playwright browser not available: {e}")
            return

        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Create browser page."""
    page = await browser.new_page()
    yield page
    await page.close()


class TestOdooLoginPage:
    """Test Odoo login page is accessible and has expected elements."""

    async def test_odoo_homepage_loads(self, page):
        """
        GIVEN: Odoo server is running
        WHEN: Browser navigates to Odoo URL
        THEN: Homepage loads with Sign in option
        """
        await page.goto(ODOO_URL, timeout=30000)

        title = await page.title()
        assert "Keboola" in title

        # Should have Sign in button
        signin = await page.query_selector('a:has-text("Sign in")')
        assert signin is not None

    async def test_login_page_has_email_password_fields(self, page):
        """
        GIVEN: Odoo login page
        WHEN: User navigates to login
        THEN: Email and password fields are present
        """
        await page.goto(f"{ODOO_URL}/web/login", timeout=30000)

        email_field = await page.query_selector('input[name="login"], input[type="email"]')
        password_field = await page.query_selector('input[name="password"], input[type="password"]')

        assert email_field is not None, "Email field not found"
        assert password_field is not None, "Password field not found"

    async def test_login_page_has_google_sso(self, page):
        """
        GIVEN: Odoo login page
        WHEN: User views login options
        THEN: Google SSO button is available
        """
        await page.goto(f"{ODOO_URL}/web/login", timeout=30000)

        google_btn = await page.query_selector('a:has-text("Google"), button:has-text("Google")')
        assert google_btn is not None, "Google SSO not found"

    async def test_google_sso_redirects_to_google(self, page):
        """
        GIVEN: Odoo login page with Google SSO
        WHEN: User clicks Google SSO
        THEN: Browser redirects to Google OAuth
        """
        await page.goto(f"{ODOO_URL}/web/login", timeout=30000)

        google_btn = await page.query_selector('a:has-text("Google SSO")')
        if not google_btn:
            pytest.skip("Google SSO button not found")

        await google_btn.click()
        await page.wait_for_timeout(3000)

        # Should redirect to Google
        url = page.url
        assert "google.com" in url or "accounts.google" in url, f"Expected Google redirect, got {url}"


class TestOdooLoginWithCredentials:
    """Test actual login with credentials (requires TEST_USER_EMAIL/PASSWORD)."""

    @pytest.mark.skipif(
        not os.getenv("TEST_USER_EMAIL"),
        reason="TEST_USER_EMAIL not configured"
    )
    async def test_login_with_valid_credentials(self, page):
        """
        GIVEN: Valid Odoo credentials
        WHEN: User logs in with email/password
        THEN: User is redirected to Odoo dashboard
        """
        await page.goto(f"{ODOO_URL}/web/login", timeout=30000)

        # Fill credentials
        await page.fill('input[name="login"]', os.getenv("TEST_USER_EMAIL"))
        await page.fill('input[name="password"]', os.getenv("TEST_USER_PASSWORD"))

        # Submit
        await page.click('button:has-text("Log in")')
        await page.wait_for_timeout(5000)

        # Should be logged in (not on login page)
        assert "/web/login" not in page.url, "Still on login page - login may have failed"

    async def test_login_with_invalid_credentials_shows_error(self, page):
        """
        GIVEN: Invalid credentials
        WHEN: User attempts to log in
        THEN: Error message is displayed
        """
        await page.goto(f"{ODOO_URL}/web/login", timeout=30000)

        await page.fill('input[name="login"]', "invalid@example.com")
        await page.fill('input[name="password"]', "wrongpassword")
        await page.click('button:has-text("Log in")')
        await page.wait_for_timeout(3000)

        # Should show error or stay on login page
        body = await page.inner_text("body")
        assert "error" in body.lower() or "wrong" in body.lower() or "/web/login" in page.url


class TestOdooSessionAfterLogin:
    """Test Odoo session management after successful login."""

    @pytest.mark.skipif(
        not os.getenv("TEST_USER_EMAIL"),
        reason="TEST_USER_EMAIL not configured"
    )
    async def test_session_persists_across_navigation(self, page):
        """
        GIVEN: Logged in user
        WHEN: User navigates within Odoo
        THEN: Session remains valid
        """
        await page.goto(f"{ODOO_URL}/web/login", timeout=30000)

        await page.fill('input[name="login"]', os.getenv("TEST_USER_EMAIL"))
        await page.fill('input[name="password"]', os.getenv("TEST_USER_PASSWORD"))
        await page.click('button:has-text("Log in")')
        await page.wait_for_timeout(5000)

        if "/web/login" in page.url:
            pytest.skip("Login failed")

        # Navigate to another page
        await page.goto(f"{ODOO_URL}/web", timeout=30000)

        # Should still be logged in
        assert "/web/login" not in page.url


class TestOdooAPIAccess:
    """Test Odoo XML-RPC API is accessible (for MCP integration)."""

    async def test_xmlrpc_common_endpoint(self, page):
        """
        GIVEN: Odoo server
        WHEN: Accessing XML-RPC common endpoint
        THEN: Endpoint is available
        """
        import httpx

        async with httpx.AsyncClient() as client:
            # XML-RPC version endpoint
            response = await client.post(
                f"{ODOO_URL}/xmlrpc/2/common",
                content="""<?xml version="1.0"?>
                <methodCall>
                    <methodName>version</methodName>
                    <params></params>
                </methodCall>""",
                headers={"Content-Type": "text/xml"},
            )

            assert response.status_code == 200
            assert "methodResponse" in response.text
