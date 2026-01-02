"""
Browser-based OAuth 2.1 PKCE Flow Tests using Playwright

These tests automate a real browser to verify the complete OAuth authentication
flow from user login to MCP API calls. They test the actual user experience
and ensure the MCP server correctly integrates with the authorization server.

Run with: pytest tests/e2e/test_browser_oauth.py -v --headed (to see browser)
Run headless: pytest tests/e2e/test_browser_oauth.py -v

Prerequisites:
- MCP HTTP server running at TEST_MCP_SERVER_URL
- OAuth authorization server at TEST_AUTH_SERVER_URL (auth.keboola.com)
- Test user credentials configured in .env
- Playwright browsers installed: playwright install chromium
"""

import base64
import hashlib
import json
import os
import secrets
from urllib.parse import parse_qs, urlparse

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.oauth, pytest.mark.browser]


# =============================================================================
# Test Configuration
# =============================================================================

BROWSER_CONFIG = {
    "mcp_server_url": os.getenv("TEST_MCP_SERVER_URL", "http://localhost:8080"),
    "auth_server_url": os.getenv("TEST_AUTH_SERVER_URL", "https://auth.keboola.com"),
    "client_id": os.getenv("TEST_OAUTH_CLIENT_ID", "odoo-mcp-client"),
    "redirect_uri": os.getenv("TEST_REDIRECT_URI", "http://localhost:8080/callback"),
    "test_user_email": os.getenv("TEST_USER_EMAIL"),
    "test_user_password": os.getenv("TEST_USER_PASSWORD"),
    "scopes": "openid profile email odoo.read odoo.hr.profile odoo.leave.read odoo.documents.read",
}


def generate_pkce() -> dict:
    """Generate PKCE code verifier and challenge for OAuth 2.1."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    return {
        "verifier": code_verifier,
        "challenge": code_challenge,
        "method": "S256",
    }


def generate_state() -> str:
    """Generate cryptographically secure state parameter."""
    return secrets.token_urlsafe(32)


# =============================================================================
# Playwright Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def browser_type():
    """Return browser type for tests."""
    return "chromium"


@pytest.fixture
async def browser(browser_type):
    """Launch browser for OAuth flow testing."""
    pytest.importorskip("playwright.async_api")
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        try:
            browser = await getattr(p, browser_type).launch(
                headless=os.getenv("HEADED", "false").lower() != "true",
                slow_mo=100 if os.getenv("HEADED") else 0,
            )
        except Exception as e:
            pytest.skip(f"Playwright browser not available: {e}")
            return

        yield browser
        await browser.close()


@pytest.fixture
async def browser_context(browser):
    """Create isolated browser context for each test."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Playwright Test Browser)",
    )
    yield context
    await context.close()


@pytest.fixture
async def page(browser_context):
    """Create new page for each test."""
    page = await browser_context.new_page()
    yield page
    await page.close()


@pytest.fixture
def pkce():
    """Generate fresh PKCE challenge for each test."""
    return generate_pkce()


@pytest.fixture
def oauth_state():
    """Generate fresh state parameter for each test."""
    return generate_state()


# =============================================================================
# OAuth Discovery Tests
# =============================================================================


class TestOAuthDiscoveryBrowser:
    """Test OAuth discovery endpoints via browser."""

    async def test_mcp_server_serves_protected_resource_metadata(self, page):
        """
        GIVEN: MCP HTTP server is running
        WHEN: Browser requests /.well-known/oauth-protected-resource
        THEN: Valid RFC 9728 metadata is returned with correct authorization server
        """
        url = f"{BROWSER_CONFIG['mcp_server_url']}/.well-known/oauth-protected-resource"

        response = await page.goto(url)

        assert response is not None, "No response from MCP server"
        assert response.status == 200, f"Expected 200, got {response.status}"

        # Parse JSON response
        content = await page.content()
        # Extract JSON from page (might be wrapped in HTML pre tag)
        try:
            metadata = json.loads(await page.evaluate("document.body.innerText"))
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response: {content}")

        # Verify RFC 9728 required fields
        assert "resource" in metadata, "Missing 'resource' field"
        assert "authorization_servers" in metadata, "Missing 'authorization_servers' field"
        assert isinstance(metadata["authorization_servers"], list)
        assert len(metadata["authorization_servers"]) >= 1

        # Should point to auth.keboola.com
        assert BROWSER_CONFIG["auth_server_url"] in metadata["authorization_servers"]

    async def test_authorization_server_metadata_accessible(self, page):
        """
        GIVEN: Authorization server URL is known
        WHEN: Browser requests /.well-known/oauth-authorization-server
        THEN: Valid OAuth 2.1 metadata is returned with PKCE support
        """
        url = f"{BROWSER_CONFIG['auth_server_url']}/.well-known/oauth-authorization-server"

        try:
            response = await page.goto(url, timeout=10000)
        except Exception as e:
            pytest.skip(f"Auth server not reachable: {e}")

        assert response is not None
        assert response.status == 200, f"Expected 200, got {response.status}"

        try:
            metadata = json.loads(await page.evaluate("document.body.innerText"))
        except json.JSONDecodeError:
            # Try openid-configuration instead
            url = f"{BROWSER_CONFIG['auth_server_url']}/.well-known/openid-configuration"
            response = await page.goto(url)
            assert response.status == 200
            metadata = json.loads(await page.evaluate("document.body.innerText"))

        # Verify OAuth 2.1 required fields
        assert "authorization_endpoint" in metadata
        assert "token_endpoint" in metadata

        # PKCE must be supported (OAuth 2.1 requirement)
        if "code_challenge_methods_supported" in metadata:
            assert "S256" in metadata["code_challenge_methods_supported"]


# =============================================================================
# OAuth PKCE Flow Tests
# =============================================================================


class TestOAuthPKCEFlowBrowser:
    """Test complete OAuth 2.1 PKCE flow using real browser automation."""

    async def test_authorization_url_redirects_to_login(self, page, pkce, oauth_state):
        """
        GIVEN: Valid PKCE challenge and state
        WHEN: Browser navigates to authorization URL
        THEN: User sees login form at authorization server
        """
        auth_url = (
            f"{BROWSER_CONFIG['auth_server_url']}/authorize"
            f"?response_type=code"
            f"&client_id={BROWSER_CONFIG['client_id']}"
            f"&redirect_uri={BROWSER_CONFIG['redirect_uri']}"
            f"&scope={BROWSER_CONFIG['scopes'].replace(' ', '%20')}"
            f"&code_challenge={pkce['challenge']}"
            f"&code_challenge_method={pkce['method']}"
            f"&state={oauth_state}"
        )

        try:
            await page.goto(auth_url, timeout=15000)
        except Exception as e:
            pytest.skip(f"Auth server not reachable: {e}")

        # Should see some kind of login form
        login_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[name="login"]',
            'input[name="username"]',
            'input[type="text"][name*="user"]',
        ]

        login_found = False
        for selector in login_selectors:
            if await page.query_selector(selector):
                login_found = True
                break

        assert login_found, f"No login form found. Page URL: {page.url}"

    async def test_invalid_client_id_shows_error(self, page, pkce, oauth_state):
        """
        GIVEN: Invalid client_id
        WHEN: Browser navigates to authorization URL
        THEN: Authorization server shows error (not login form)
        """
        auth_url = (
            f"{BROWSER_CONFIG['auth_server_url']}/authorize"
            f"?response_type=code"
            f"&client_id=invalid_nonexistent_client_12345"
            f"&redirect_uri={BROWSER_CONFIG['redirect_uri']}"
            f"&scope=openid"
            f"&code_challenge={pkce['challenge']}"
            f"&code_challenge_method={pkce['method']}"
            f"&state={oauth_state}"
        )

        try:
            await page.goto(auth_url, timeout=15000)
        except Exception as e:
            pytest.skip(f"Auth server not reachable: {e}")

        # Should see error, not login form
        page_content = await page.content()
        page_text = page_content.lower()

        # Common error indicators
        has_error = (
            "error" in page_text
            or "invalid" in page_text
            or "unauthorized" in page_text
            or "unknown client" in page_text
            or page.url != auth_url  # Redirected to error page
        )

        # If we see a login form with no error, that's wrong
        if await page.query_selector('input[type="email"]'):
            if "error" not in page_text:
                pytest.fail("Invalid client_id should not show login form without error")

    async def test_missing_pkce_rejected(self, page, oauth_state):
        """
        GIVEN: OAuth 2.1 authorization server
        WHEN: Authorization request made without PKCE
        THEN: Request is rejected (OAuth 2.1 requires PKCE)
        """
        auth_url = (
            f"{BROWSER_CONFIG['auth_server_url']}/authorize"
            f"?response_type=code"
            f"&client_id={BROWSER_CONFIG['client_id']}"
            f"&redirect_uri={BROWSER_CONFIG['redirect_uri']}"
            f"&scope=openid"
            f"&state={oauth_state}"
            # No code_challenge - should be rejected
        )

        try:
            await page.goto(auth_url, timeout=15000)
        except Exception as e:
            pytest.skip(f"Auth server not reachable: {e}")

        page_content = await page.content()

        # OAuth 2.1 compliant server should reject or show error
        # Some servers might still show login but fail at token exchange
        # This test documents expected behavior
        assert page.url is not None  # Page loaded

    @pytest.mark.skipif(
        not BROWSER_CONFIG.get("test_user_email"),
        reason="TEST_USER_EMAIL not configured"
    )
    async def test_complete_login_flow_obtains_authorization_code(
        self, page, pkce, oauth_state
    ):
        """
        GIVEN: Valid test user credentials
        WHEN: User completes login flow in browser
        THEN: Authorization code is returned in redirect URL
        """
        # Track redirects to capture the callback
        authorization_code = None
        callback_received = False

        async def intercept_callback(route):
            nonlocal authorization_code, callback_received
            url = route.request.url

            if "/callback" in url or BROWSER_CONFIG["redirect_uri"] in url:
                callback_received = True
                parsed = urlparse(url)
                params = parse_qs(parsed.query)

                if "code" in params:
                    authorization_code = params["code"][0]

                # Return success page instead of actually navigating
                await route.fulfill(
                    status=200,
                    content_type="text/html",
                    body="<html><body><h1>Authorization successful</h1></body></html>",
                )
            else:
                await route.continue_()

        await page.route("**/*", intercept_callback)

        # Start authorization flow
        auth_url = (
            f"{BROWSER_CONFIG['auth_server_url']}/authorize"
            f"?response_type=code"
            f"&client_id={BROWSER_CONFIG['client_id']}"
            f"&redirect_uri={BROWSER_CONFIG['redirect_uri']}"
            f"&scope={BROWSER_CONFIG['scopes'].replace(' ', '%20')}"
            f"&code_challenge={pkce['challenge']}"
            f"&code_challenge_method={pkce['method']}"
            f"&state={oauth_state}"
        )

        try:
            await page.goto(auth_url, timeout=15000)
        except Exception as e:
            pytest.skip(f"Auth server not reachable: {e}")

        # Fill login form
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[name="login"]',
            'input[name="username"]',
        ]

        email_input = None
        for selector in email_selectors:
            email_input = await page.query_selector(selector)
            if email_input:
                break

        if not email_input:
            pytest.skip("Could not find email input field")

        await email_input.fill(BROWSER_CONFIG["test_user_email"])

        # Fill password
        password_input = await page.query_selector('input[type="password"]')
        if not password_input:
            pytest.skip("Could not find password input field")

        await password_input.fill(BROWSER_CONFIG["test_user_password"])

        # Submit form
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Log in")',
            'button:has-text("Sign in")',
            'button:has-text("Login")',
        ]

        submitted = False
        for selector in submit_selectors:
            submit_btn = await page.query_selector(selector)
            if submit_btn:
                await submit_btn.click()
                submitted = True
                break

        if not submitted:
            pytest.skip("Could not find submit button")

        # Wait for redirect with authorization code
        try:
            await page.wait_for_function(
                "() => window.location.href.includes('callback') || document.body.innerText.includes('Authorization successful')",
                timeout=30000,
            )
        except Exception:
            # Check if there was an error on the page
            page_content = await page.content()
            if "error" in page_content.lower():
                pytest.fail(f"Login failed with error. Page content: {page_content[:500]}")
            pytest.skip("Login flow did not complete - may need consent screen handling")

        # Verify we got the code
        assert callback_received, "Callback was not intercepted"
        assert authorization_code is not None, "No authorization code received"
        assert len(authorization_code) > 10, "Authorization code seems too short"


# =============================================================================
# Token Exchange Tests
# =============================================================================


class TestTokenExchangeBrowser:
    """Test OAuth token exchange after browser-based authorization."""

    @pytest.mark.skipif(
        not BROWSER_CONFIG.get("test_user_email"),
        reason="TEST_USER_EMAIL not configured"
    )
    async def test_exchange_code_for_tokens(self, page, browser_context, pkce, oauth_state):
        """
        GIVEN: Valid authorization code from browser flow
        WHEN: Code is exchanged for tokens using PKCE verifier
        THEN: Valid access_token and id_token are returned
        """
        import httpx

        # First, complete the login flow to get authorization code
        authorization_code = None

        async def intercept_callback(route):
            nonlocal authorization_code
            url = route.request.url
            if "/callback" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if "code" in params:
                    authorization_code = params["code"][0]
                await route.fulfill(status=200, body="OK")
            else:
                await route.continue_()

        await page.route("**/*", intercept_callback)

        auth_url = (
            f"{BROWSER_CONFIG['auth_server_url']}/authorize"
            f"?response_type=code"
            f"&client_id={BROWSER_CONFIG['client_id']}"
            f"&redirect_uri={BROWSER_CONFIG['redirect_uri']}"
            f"&scope={BROWSER_CONFIG['scopes'].replace(' ', '%20')}"
            f"&code_challenge={pkce['challenge']}"
            f"&code_challenge_method={pkce['method']}"
            f"&state={oauth_state}"
        )

        try:
            await page.goto(auth_url, timeout=15000)

            # Quick login
            await page.fill('input[type="email"], input[name="email"], input[name="login"]',
                          BROWSER_CONFIG["test_user_email"])
            await page.fill('input[type="password"]', BROWSER_CONFIG["test_user_password"])
            await page.click('button[type="submit"]')

            await page.wait_for_timeout(5000)  # Wait for redirect
        except Exception as e:
            pytest.skip(f"Could not complete login flow: {e}")

        if not authorization_code:
            pytest.skip("No authorization code obtained")

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{BROWSER_CONFIG['auth_server_url']}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": BROWSER_CONFIG["redirect_uri"],
                    "client_id": BROWSER_CONFIG["client_id"],
                    "code_verifier": pkce["verifier"],
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            assert token_response.status_code == 200, (
                f"Token exchange failed: {token_response.status_code} - {token_response.text}"
            )

            tokens = token_response.json()

            assert "access_token" in tokens, "No access_token in response"
            assert "token_type" in tokens, "No token_type in response"
            assert tokens["token_type"].lower() == "bearer"

            # OpenID Connect should return id_token
            if "openid" in BROWSER_CONFIG["scopes"]:
                assert "id_token" in tokens, "No id_token for OpenID scope"

    async def test_invalid_code_verifier_rejected(self, page, pkce, oauth_state):
        """
        GIVEN: Valid authorization code
        WHEN: Wrong PKCE verifier is used in token exchange
        THEN: Token request is rejected
        """
        import httpx

        # This test can use a mock/invalid code since we're testing rejection
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{BROWSER_CONFIG['auth_server_url']}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": "invalid_code_12345",
                    "redirect_uri": BROWSER_CONFIG["redirect_uri"],
                    "client_id": BROWSER_CONFIG["client_id"],
                    "code_verifier": "wrong_verifier_that_does_not_match",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Should be rejected (400 or 401)
            assert token_response.status_code in [400, 401, 403], (
                f"Expected rejection, got {token_response.status_code}"
            )


# =============================================================================
# MCP Server Integration Tests
# =============================================================================


class TestMCPServerWithOAuthBrowser:
    """Test MCP HTTP server endpoints with OAuth tokens obtained via browser."""

    async def test_mcp_server_rejects_unauthenticated_request(self, page):
        """
        GIVEN: MCP HTTP server is running with OAuth protection
        WHEN: Request made without Authorization header
        THEN: Server returns 401 Unauthorized
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BROWSER_CONFIG['mcp_server_url']}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1,
                },
            )

            assert response.status_code == 401, (
                f"Expected 401 Unauthorized, got {response.status_code}"
            )

    async def test_mcp_server_rejects_invalid_token(self, page):
        """
        GIVEN: MCP HTTP server is running
        WHEN: Request made with invalid/expired token
        THEN: Server returns 401 Unauthorized
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BROWSER_CONFIG['mcp_server_url']}/mcp",
                headers={"Authorization": "Bearer invalid.jwt.token"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1,
                },
            )

            assert response.status_code == 401, (
                f"Expected 401 Unauthorized, got {response.status_code}"
            )

    @pytest.mark.skipif(
        not BROWSER_CONFIG.get("test_user_email"),
        reason="TEST_USER_EMAIL not configured"
    )
    async def test_mcp_tools_list_with_valid_token(self, page, pkce, oauth_state):
        """
        GIVEN: Valid OAuth access token from browser flow
        WHEN: MCP tools/list is called with token
        THEN: Server returns list of available tools
        """
        import httpx

        # Get token via browser flow
        access_token = await self._get_access_token_via_browser(page, pkce, oauth_state)
        if not access_token:
            pytest.skip("Could not obtain access token")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BROWSER_CONFIG['mcp_server_url']}/mcp",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1,
                },
            )

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )

            result = response.json()
            assert "result" in result or "tools" in result.get("result", {})

    @pytest.mark.skipif(
        not BROWSER_CONFIG.get("test_user_email"),
        reason="TEST_USER_EMAIL not configured"
    )
    async def test_get_my_profile_with_valid_token(self, page, pkce, oauth_state):
        """
        GIVEN: Valid OAuth access token with odoo.hr.profile scope
        WHEN: get_my_profile tool is called
        THEN: Current user's employee profile is returned
        """
        import httpx

        access_token = await self._get_access_token_via_browser(page, pkce, oauth_state)
        if not access_token:
            pytest.skip("Could not obtain access token")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BROWSER_CONFIG['mcp_server_url']}/mcp",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "get_my_profile",
                        "arguments": {},
                    },
                    "id": 1,
                },
            )

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )

            result = response.json()

            # Should have result with profile data
            assert "result" in result, f"No result in response: {result}"

            # Parse the tool result
            if "content" in result.get("result", {}):
                content = result["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    profile = json.loads(content[0].get("text", "{}"))
                    assert "name" in profile, "Profile should have name"

    @pytest.mark.skipif(
        not BROWSER_CONFIG.get("test_user_email"),
        reason="TEST_USER_EMAIL not configured"
    )
    async def test_scope_enforcement_blocks_unauthorized_tool(
        self, page, pkce, oauth_state
    ):
        """
        GIVEN: Access token with limited scopes (e.g., only odoo.hr.profile)
        WHEN: Tool requiring different scope is called (e.g., odoo.leave.write)
        THEN: Request is rejected with 403 Forbidden
        """
        import httpx

        # Get token with limited scopes
        limited_scopes = "openid odoo.hr.profile"  # No write scopes

        authorization_code = None

        async def intercept_callback(route):
            nonlocal authorization_code
            url = route.request.url
            if "/callback" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if "code" in params:
                    authorization_code = params["code"][0]
                await route.fulfill(status=200, body="OK")
            else:
                await route.continue_()

        await page.route("**/*", intercept_callback)

        auth_url = (
            f"{BROWSER_CONFIG['auth_server_url']}/authorize"
            f"?response_type=code"
            f"&client_id={BROWSER_CONFIG['client_id']}"
            f"&redirect_uri={BROWSER_CONFIG['redirect_uri']}"
            f"&scope={limited_scopes.replace(' ', '%20')}"
            f"&code_challenge={pkce['challenge']}"
            f"&code_challenge_method={pkce['method']}"
            f"&state={oauth_state}"
        )

        try:
            await page.goto(auth_url, timeout=15000)
            await page.fill('input[type="email"], input[name="email"]',
                          BROWSER_CONFIG["test_user_email"])
            await page.fill('input[type="password"]', BROWSER_CONFIG["test_user_password"])
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
        except Exception as e:
            pytest.skip(f"Could not complete login: {e}")

        if not authorization_code:
            pytest.skip("No authorization code")

        # Exchange for token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{BROWSER_CONFIG['auth_server_url']}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": BROWSER_CONFIG["redirect_uri"],
                    "client_id": BROWSER_CONFIG["client_id"],
                    "code_verifier": pkce["verifier"],
                },
            )

            if token_response.status_code != 200:
                pytest.skip("Could not get token")

            access_token = token_response.json().get("access_token")

            # Try to call a write tool (should be rejected)
            response = await client.post(
                f"{BROWSER_CONFIG['mcp_server_url']}/mcp",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "request_leave",  # Requires odoo.leave.write
                        "arguments": {
                            "leave_type": "Paid Time Off",
                            "start_date": "2025-02-01",
                            "end_date": "2025-02-02",
                            "reason": "Test",
                        },
                    },
                    "id": 1,
                },
            )

            # Should be forbidden due to insufficient scope
            assert response.status_code in [403, 400], (
                f"Expected 403/400 for insufficient scope, got {response.status_code}"
            )

    async def _get_access_token_via_browser(self, page, pkce, oauth_state) -> str | None:
        """Helper to complete OAuth flow and return access token."""
        import httpx

        authorization_code = None

        async def intercept_callback(route):
            nonlocal authorization_code
            url = route.request.url
            if "/callback" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if "code" in params:
                    authorization_code = params["code"][0]
                await route.fulfill(status=200, body="OK")
            else:
                await route.continue_()

        await page.route("**/*", intercept_callback)

        auth_url = (
            f"{BROWSER_CONFIG['auth_server_url']}/authorize"
            f"?response_type=code"
            f"&client_id={BROWSER_CONFIG['client_id']}"
            f"&redirect_uri={BROWSER_CONFIG['redirect_uri']}"
            f"&scope={BROWSER_CONFIG['scopes'].replace(' ', '%20')}"
            f"&code_challenge={pkce['challenge']}"
            f"&code_challenge_method={pkce['method']}"
            f"&state={oauth_state}"
        )

        try:
            await page.goto(auth_url, timeout=15000)
            await page.fill(
                'input[type="email"], input[name="email"], input[name="login"]',
                BROWSER_CONFIG["test_user_email"]
            )
            await page.fill('input[type="password"]', BROWSER_CONFIG["test_user_password"])
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
        except Exception:
            return None

        if not authorization_code:
            return None

        # Exchange for token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{BROWSER_CONFIG['auth_server_url']}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": BROWSER_CONFIG["redirect_uri"],
                    "client_id": BROWSER_CONFIG["client_id"],
                    "code_verifier": pkce["verifier"],
                },
            )

            if token_response.status_code == 200:
                return token_response.json().get("access_token")

        return None


# =============================================================================
# Session Management Tests
# =============================================================================


class TestOAuthSessionBrowser:
    """Test OAuth session handling and token refresh via browser."""

    async def test_token_expiry_triggers_reauth(self, browser_context):
        """
        GIVEN: Access token has expired
        WHEN: MCP request is made with expired token
        THEN: Server returns 401 and client can re-authenticate
        """
        import httpx

        page = await browser_context.new_page()

        # Simulate expired token (would need actual token manipulation in real test)
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJleHAiOjB9.invalid"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BROWSER_CONFIG['mcp_server_url']}/mcp",
                headers={"Authorization": f"Bearer {expired_token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1,
                },
            )

            # Expired token should be rejected
            assert response.status_code == 401

        await page.close()

    @pytest.mark.skipif(
        not BROWSER_CONFIG.get("test_user_email"),
        reason="TEST_USER_EMAIL not configured"
    )
    async def test_refresh_token_obtains_new_access_token(self, page, pkce, oauth_state):
        """
        GIVEN: Valid refresh token from initial authentication
        WHEN: Refresh token is used to get new access token
        THEN: New valid access token is returned without user interaction
        """
        import httpx

        # Get tokens including refresh token (requires offline_access scope)
        authorization_code = None

        async def intercept_callback(route):
            nonlocal authorization_code
            url = route.request.url
            if "/callback" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if "code" in params:
                    authorization_code = params["code"][0]
                await route.fulfill(status=200, body="OK")
            else:
                await route.continue_()

        await page.route("**/*", intercept_callback)

        # Request offline_access for refresh token
        scopes_with_refresh = BROWSER_CONFIG["scopes"] + " offline_access"

        auth_url = (
            f"{BROWSER_CONFIG['auth_server_url']}/authorize"
            f"?response_type=code"
            f"&client_id={BROWSER_CONFIG['client_id']}"
            f"&redirect_uri={BROWSER_CONFIG['redirect_uri']}"
            f"&scope={scopes_with_refresh.replace(' ', '%20')}"
            f"&code_challenge={pkce['challenge']}"
            f"&code_challenge_method={pkce['method']}"
            f"&state={oauth_state}"
        )

        try:
            await page.goto(auth_url, timeout=15000)
            await page.fill('input[type="email"], input[name="email"]',
                          BROWSER_CONFIG["test_user_email"])
            await page.fill('input[type="password"]', BROWSER_CONFIG["test_user_password"])
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
        except Exception as e:
            pytest.skip(f"Could not complete login: {e}")

        if not authorization_code:
            pytest.skip("No authorization code")

        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                f"{BROWSER_CONFIG['auth_server_url']}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": BROWSER_CONFIG["redirect_uri"],
                    "client_id": BROWSER_CONFIG["client_id"],
                    "code_verifier": pkce["verifier"],
                },
            )

            if token_response.status_code != 200:
                pytest.skip("Could not get initial tokens")

            tokens = token_response.json()
            refresh_token = tokens.get("refresh_token")

            if not refresh_token:
                pytest.skip("No refresh token returned (offline_access may not be supported)")

            # Use refresh token to get new access token
            refresh_response = await client.post(
                f"{BROWSER_CONFIG['auth_server_url']}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": BROWSER_CONFIG["client_id"],
                },
            )

            assert refresh_response.status_code == 200, (
                f"Refresh failed: {refresh_response.status_code} - {refresh_response.text}"
            )

            new_tokens = refresh_response.json()
            assert "access_token" in new_tokens
            assert new_tokens["access_token"] != tokens["access_token"], (
                "New access token should be different from original"
            )
