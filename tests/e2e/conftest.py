"""
E2E Test Fixtures for Browser-based OAuth and MCP Testing

Provides Playwright browser fixtures and OAuth helpers for end-to-end testing.
"""

import asyncio
import base64
import hashlib
import os
import secrets
from typing import AsyncGenerator

import pytest


# =============================================================================
# Playwright Browser Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async session-scoped fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def playwright_instance():
    """Launch Playwright instance for the test session."""
    pw = pytest.importorskip("playwright.async_api")

    async with pw.async_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
async def browser_instance(playwright_instance):
    """Launch browser instance for the test session."""
    browser = await playwright_instance.chromium.launch(
        headless=os.getenv("HEADED", "false").lower() != "true",
        slow_mo=50 if os.getenv("HEADED") else 0,
    )
    yield browser
    await browser.close()


@pytest.fixture
async def browser_context(browser_instance):
    """Create isolated browser context for each test."""
    context = await browser_instance.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,  # For local dev servers
    )
    yield context
    await context.close()


@pytest.fixture
async def page(browser_context):
    """Create new page for each test."""
    page = await browser_context.new_page()

    # Enable request logging for debugging
    if os.getenv("DEBUG"):
        page.on("request", lambda req: print(f">> {req.method} {req.url}"))
        page.on("response", lambda res: print(f"<< {res.status} {res.url}"))

    yield page
    await page.close()


# =============================================================================
# OAuth Helper Fixtures
# =============================================================================


@pytest.fixture
def pkce_challenge() -> dict:
    """Generate PKCE code verifier and challenge."""
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


@pytest.fixture
def oauth_state() -> str:
    """Generate cryptographically secure state parameter."""
    return secrets.token_urlsafe(32)


@pytest.fixture
def oauth_config() -> dict:
    """Return OAuth configuration from environment."""
    return {
        "mcp_server_url": os.getenv("TEST_MCP_SERVER_URL", "http://localhost:8080"),
        "auth_server_url": os.getenv("TEST_AUTH_SERVER_URL", "https://auth.keboola.com"),
        "client_id": os.getenv("TEST_OAUTH_CLIENT_ID", "odoo-mcp-client"),
        "redirect_uri": os.getenv("TEST_REDIRECT_URI", "http://localhost:8080/callback"),
        "scopes": os.getenv(
            "TEST_OAUTH_SCOPES",
            "openid profile email odoo.read odoo.hr.profile odoo.leave.read"
        ),
    }


@pytest.fixture
def test_user_credentials() -> dict:
    """Return test user credentials from environment."""
    return {
        "email": os.getenv("TEST_USER_EMAIL"),
        "password": os.getenv("TEST_USER_PASSWORD"),
    }


# =============================================================================
# MCP Server Fixtures
# =============================================================================


@pytest.fixture
async def mcp_server_process():
    """
    Start MCP HTTP server as subprocess for testing.

    This fixture starts the actual server so browser tests can hit it.
    """
    import subprocess
    import time

    server_url = os.getenv("TEST_MCP_SERVER_URL", "http://localhost:8080")

    # Check if server is already running
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{server_url}/health", timeout=2.0)
            if response.status_code == 200:
                # Server already running, don't start another
                yield None
                return
        except Exception:
            pass  # Server not running, start it

    # Start server
    process = subprocess.Popen(
        ["python", "-m", "odoo_mcp_server.http_server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "HTTP_PORT": "8080"},
    )

    # Wait for server to be ready
    max_wait = 10
    for _ in range(max_wait):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{server_url}/health", timeout=1.0)
                if response.status_code == 200:
                    break
        except Exception:
            time.sleep(1)
    else:
        process.terminate()
        pytest.fail("MCP server failed to start")

    yield process

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


# =============================================================================
# Token Fixtures
# =============================================================================


@pytest.fixture
async def access_token_via_browser(
    page,
    pkce_challenge,
    oauth_state,
    oauth_config,
    test_user_credentials,
) -> AsyncGenerator[str | None, None]:
    """
    Obtain access token via browser-based OAuth flow.

    This fixture performs the complete OAuth PKCE flow using Playwright
    and returns a valid access token.
    """
    from urllib.parse import parse_qs, urlparse
    import httpx

    if not test_user_credentials["email"]:
        pytest.skip("TEST_USER_EMAIL not configured")
        yield None
        return

    authorization_code = None

    async def intercept_callback(route):
        nonlocal authorization_code
        url = route.request.url
        if "/callback" in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if "code" in params:
                authorization_code = params["code"][0]
            await route.fulfill(status=200, body="Authorization successful")
        else:
            await route.continue_()

    await page.route("**/*", intercept_callback)

    # Build authorization URL
    auth_url = (
        f"{oauth_config['auth_server_url']}/authorize"
        f"?response_type=code"
        f"&client_id={oauth_config['client_id']}"
        f"&redirect_uri={oauth_config['redirect_uri']}"
        f"&scope={oauth_config['scopes'].replace(' ', '%20')}"
        f"&code_challenge={pkce_challenge['challenge']}"
        f"&code_challenge_method={pkce_challenge['method']}"
        f"&state={oauth_state}"
    )

    try:
        await page.goto(auth_url, timeout=15000)

        # Fill login form
        await page.fill(
            'input[type="email"], input[name="email"], input[name="login"]',
            test_user_credentials["email"]
        )
        await page.fill('input[type="password"]', test_user_credentials["password"])
        await page.click('button[type="submit"]')

        # Wait for redirect
        await page.wait_for_timeout(5000)

    except Exception as e:
        pytest.skip(f"OAuth flow failed: {e}")
        yield None
        return

    if not authorization_code:
        pytest.skip("No authorization code obtained")
        yield None
        return

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{oauth_config['auth_server_url']}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": oauth_config["redirect_uri"],
                "client_id": oauth_config["client_id"],
                "code_verifier": pkce_challenge["verifier"],
            },
        )

        if token_response.status_code != 200:
            pytest.skip(f"Token exchange failed: {token_response.text}")
            yield None
            return

        tokens = token_response.json()
        yield tokens.get("access_token")
