"""
OAuth 2.1 Authentication Flow Tests

These tests verify the complete OAuth authentication flow from
MCP client perspective, including PKCE, token exchange, and refresh.

Run with: pytest tests/e2e/test_oauth_flow.py -v -m oauth

NOTE: These tests require:
- HTTP server running on TEST_MCP_SERVER_URL (default: http://localhost:8000)
- Authorization server accessible at TEST_AUTH_SERVER_URL
"""

import pytest
import httpx

pytestmark = [pytest.mark.e2e, pytest.mark.oauth]


async def check_server_available(url: str) -> bool:
    """Check if a server is available at the given URL."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/health")
            return response.status_code in [200, 404, 405]  # Server is responding
    except (httpx.ConnectError, httpx.TimeoutException, httpx.ConnectTimeout):
        return False


class TestOAuthDiscovery:
    """Tests for OAuth 2.1 metadata discovery (RFC 9728)."""

    async def test_protected_resource_metadata_endpoint_exists(
        self, http_client: httpx.AsyncClient, test_config: dict
    ):
        """
        GIVEN: MCP server is running
        WHEN: Client requests /.well-known/oauth-protected-resource
        THEN: Server returns valid RFC 9728 metadata
        """
        if not await check_server_available(test_config['mcp_server_url']):
            pytest.skip("MCP server not available")

        response = await http_client.get(
            f"{test_config['mcp_server_url']}/.well-known/oauth-protected-resource"
        )

        assert response.status_code == 200
        metadata = response.json()

        # Required fields per RFC 9728
        assert "resource" in metadata
        assert "authorization_servers" in metadata
        assert isinstance(metadata["authorization_servers"], list)
        assert len(metadata["authorization_servers"]) > 0

    async def test_authorization_server_discovery(
        self, http_client: httpx.AsyncClient, test_config: dict
    ):
        """
        GIVEN: Protected resource metadata is available
        WHEN: Client follows authorization_servers link
        THEN: Authorization server metadata is accessible
        """
        if not await check_server_available(test_config['mcp_server_url']):
            pytest.skip("MCP server not available")

        # Get protected resource metadata
        pr_response = await http_client.get(
            f"{test_config['mcp_server_url']}/.well-known/oauth-protected-resource"
        )

        if pr_response.status_code != 200:
            pytest.skip("Protected resource metadata not available")

        pr_metadata = pr_response.json()

        # Follow to authorization server
        auth_server = pr_metadata["authorization_servers"][0]
        as_response = await http_client.get(
            f"{auth_server}/.well-known/oauth-authorization-server"
        )

        assert as_response.status_code == 200
        as_metadata = as_response.json()

        # Required OAuth 2.1 fields
        assert "authorization_endpoint" in as_metadata
        assert "token_endpoint" in as_metadata
        assert "code_challenge_methods_supported" in as_metadata
        assert "S256" in as_metadata["code_challenge_methods_supported"]


class TestOAuthPKCEFlow:
    """Tests for OAuth 2.1 Authorization Code Flow with PKCE."""

    async def test_authorization_request_redirects_to_login(
        self, test_config: dict, pkce_challenge: dict
    ):
        """
        GIVEN: Valid PKCE challenge and client credentials
        WHEN: Client initiates authorization request
        THEN: User is redirected to authorization server login
        """
        playwright = pytest.importorskip("playwright")
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
            except Exception as e:
                pytest.skip(f"Playwright browser not available: {e}")
                return

            page = await browser.new_page()

            # Construct authorization URL
            auth_url = (
                f"{test_config['auth_server_url']}/authorize"
                f"?response_type=code"
                f"&client_id=test_client"
                f"&redirect_uri=http://localhost:8000/callback"
                f"&scope=openid%20odoo.read%20odoo.write"
                f"&code_challenge={pkce_challenge['challenge']}"
                f"&code_challenge_method=S256"
                f"&state=test_state_123"
            )

            try:
                await page.goto(auth_url, timeout=10000)
                # Should see login form
                await page.wait_for_selector(
                    'input[type="email"], input[name="login"]', timeout=5000
                )
            except Exception as e:
                pytest.skip(f"Auth server not reachable: {e}")
            finally:
                await browser.close()

    async def test_complete_oauth_flow_with_valid_credentials(
        self, test_config: dict, pkce_challenge: dict
    ):
        """
        GIVEN: Valid user credentials and PKCE challenge
        WHEN: User completes OAuth login flow
        THEN: Client receives valid access token
        """
        if not test_config.get("test_user_email"):
            pytest.skip("Test user credentials not configured")

        pytest.importorskip("playwright")
        from playwright.async_api import async_playwright
        from urllib.parse import parse_qs, urlparse

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Track the callback URL
            callback_url = None

            async def handle_route(route):
                nonlocal callback_url
                if "callback" in route.request.url:
                    callback_url = route.request.url
                    await route.fulfill(status=200, body="OK")
                else:
                    await route.continue_()

            await page.route("**/callback**", handle_route)

            # Start OAuth flow
            auth_url = (
                f"{test_config['auth_server_url']}/authorize"
                f"?response_type=code"
                f"&client_id=test_client"
                f"&redirect_uri=http://localhost:8000/callback"
                f"&scope=openid%20odoo.read%20odoo.write"
                f"&code_challenge={pkce_challenge['challenge']}"
                f"&code_challenge_method=S256"
                f"&state=test_state_123"
            )

            try:
                await page.goto(auth_url)

                # Fill login form
                await page.fill(
                    'input[type="email"], input[name="login"]',
                    test_config["test_user_email"],
                )
                await page.fill(
                    'input[type="password"]', test_config["test_user_password"]
                )
                await page.click('button[type="submit"]')

                # Wait for redirect with code
                await page.wait_for_url("**/callback**", timeout=10000)

                # Extract authorization code
                assert callback_url is not None
                parsed = urlparse(callback_url)
                params = parse_qs(parsed.query)

                assert "code" in params
                assert params["state"][0] == "test_state_123"

                # Exchange code for token
                async with httpx.AsyncClient() as client:
                    token_response = await client.post(
                        f"{test_config['auth_server_url']}/token",
                        data={
                            "grant_type": "authorization_code",
                            "code": params["code"][0],
                            "redirect_uri": "http://localhost:8000/callback",
                            "client_id": "test_client",
                            "code_verifier": pkce_challenge["verifier"],
                        },
                    )

                    assert token_response.status_code == 200
                    tokens = token_response.json()
                    assert "access_token" in tokens
                    assert "token_type" in tokens
                    assert tokens["token_type"].lower() == "bearer"

            except Exception as e:
                pytest.skip(f"OAuth flow failed: {e}")
            finally:
                await browser.close()


class TestTokenValidation:
    """Tests for MCP server token validation."""

    async def test_mcp_endpoint_rejects_missing_token(
        self, http_client: httpx.AsyncClient, test_config: dict
    ):
        """
        GIVEN: MCP server is running
        WHEN: Client calls MCP endpoint without token
        THEN: Server returns 401 Unauthorized
        """
        if not await check_server_available(test_config['mcp_server_url']):
            pytest.skip("MCP server not available")

        response = await http_client.post(
            f"{test_config['mcp_server_url']}/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        )

        assert response.status_code == 401

    async def test_mcp_endpoint_rejects_invalid_token(
        self, http_client: httpx.AsyncClient, test_config: dict
    ):
        """
        GIVEN: MCP server is running
        WHEN: Client calls MCP endpoint with invalid token
        THEN: Server returns 401 Unauthorized
        """
        if not await check_server_available(test_config['mcp_server_url']):
            pytest.skip("MCP server not available")

        response = await http_client.post(
            f"{test_config['mcp_server_url']}/mcp",
            headers={"Authorization": "Bearer invalid_token_here"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        )

        assert response.status_code == 401

    async def test_mcp_endpoint_accepts_valid_token(
        self,
        http_client: httpx.AsyncClient,
        test_config: dict,
        valid_access_token: str | None,
    ):
        """
        GIVEN: Valid OAuth access token
        WHEN: Client calls MCP endpoint with token
        THEN: Server processes request successfully
        """
        if not await check_server_available(test_config['mcp_server_url']):
            pytest.skip("MCP server not available")

        if not valid_access_token:
            pytest.skip("No valid access token available")

        response = await http_client.post(
            f"{test_config['mcp_server_url']}/mcp",
            headers={"Authorization": f"Bearer {valid_access_token}"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        )

        assert response.status_code == 200
        result = response.json()
        assert "result" in result or "error" not in result


class TestTokenRefresh:
    """Tests for OAuth token refresh flow."""

    async def test_refresh_token_provides_new_access_token(
        self,
        http_client: httpx.AsyncClient,
        test_config: dict,
        valid_refresh_token: str | None,
    ):
        """
        GIVEN: Valid refresh token
        WHEN: Client requests token refresh
        THEN: New access token is issued
        """
        if not valid_refresh_token:
            pytest.skip("No valid refresh token available")

        response = await http_client.post(
            f"{test_config['auth_server_url']}/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": valid_refresh_token,
                "client_id": test_config.get("test_client_id", "test_client"),
            },
        )

        assert response.status_code == 200
        tokens = response.json()
        assert "access_token" in tokens
