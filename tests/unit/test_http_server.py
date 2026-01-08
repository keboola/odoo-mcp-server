"""
TDD Tests for HTTP MCP Server

These tests define the expected behavior of the HTTP MCP server.
They WILL FAIL until the implementation is complete.

Run with: pytest tests/unit/test_http_server.py -v
"""

import pytest

pytestmark = [pytest.mark.unit]


class TestHTTPServerExists:
    """Tests that verify the HTTP server module exists and can be imported."""

    def test_http_server_module_exists(self):
        """
        EXPECTED: http_server.py module should exist and be importable.
        FAILS UNTIL: src/odoo_mcp_server/http_server.py is created.
        """
        from odoo_mcp_server import http_server

        assert http_server is not None

    def test_http_server_has_app(self):
        """
        EXPECTED: HTTP server should expose a FastAPI app instance.
        FAILS UNTIL: FastAPI app is created in http_server.py.
        """
        from odoo_mcp_server.http_server import app

        assert app is not None
        assert hasattr(app, "routes")

    def test_http_server_has_main_function(self):
        """
        EXPECTED: HTTP server should have a main() entry point.
        FAILS UNTIL: main() function is implemented.
        """
        from odoo_mcp_server.http_server import main

        assert callable(main)


class TestHTTPServerEndpoints:
    """Tests for required HTTP endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for HTTP server."""
        from fastapi.testclient import TestClient

        from odoo_mcp_server.http_server import app

        return TestClient(app)

    def test_health_endpoint(self, client):
        """
        EXPECTED: GET /health returns 200 with status.
        FAILS UNTIL: Health endpoint is implemented.
        """
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_oauth_protected_resource_metadata(self, client):
        """
        EXPECTED: GET /.well-known/oauth-protected-resource returns RFC 9728 metadata.
        FAILS UNTIL: OAuth metadata endpoint is implemented.
        """
        response = client.get("/.well-known/oauth-protected-resource")

        assert response.status_code == 200
        metadata = response.json()

        # RFC 9728 required fields
        assert "resource" in metadata
        assert "authorization_servers" in metadata
        assert isinstance(metadata["authorization_servers"], list)
        # Default is Google OAuth
        assert "https://accounts.google.com" in metadata["authorization_servers"]

    def test_mcp_endpoint_exists(self, client):
        """
        EXPECTED: POST /mcp endpoint exists for MCP JSON-RPC.
        FAILS UNTIL: MCP endpoint is implemented.
        """
        # Without auth, should get 401
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )

        # 401 means endpoint exists but requires auth
        assert response.status_code == 401

    def test_mcp_endpoint_requires_bearer_token(self, client):
        """
        EXPECTED: /mcp endpoint requires Bearer token in Authorization header.
        FAILS UNTIL: OAuth middleware is implemented.
        """
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert "Bearer" in response.headers["WWW-Authenticate"]

    def test_callback_endpoint_for_oauth(self, client):
        """
        EXPECTED: GET /callback handles OAuth authorization code callback.
        FAILS UNTIL: OAuth callback is implemented.
        """
        response = client.get("/callback?code=test&state=test")

        # Should handle the callback (might redirect or return HTML)
        assert response.status_code in [200, 302, 303]


class TestHTTPServerMCPProtocol:
    """Tests for MCP protocol over HTTP."""

    @pytest.fixture
    def authenticated_client(self):
        """Create test client with mocked authentication."""
        from fastapi.testclient import TestClient

        from odoo_mcp_server.http_server import app

        client = TestClient(app)
        # TODO: Mock authentication middleware to allow requests
        return client

    def test_mcp_tools_list(self, authenticated_client):
        """
        EXPECTED: tools/list returns available MCP tools.
        FAILS UNTIL: MCP protocol handler is implemented.
        """
        response = authenticated_client.post(
            "/mcp",
            headers={"Authorization": "Bearer test_token"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )

        assert response.status_code == 200
        result = response.json()
        assert "result" in result
        assert "tools" in result["result"]

    def test_mcp_tools_call(self, authenticated_client):
        """
        EXPECTED: tools/call executes a tool and returns result.
        FAILS UNTIL: Tool execution over HTTP is implemented.
        """
        response = authenticated_client.post(
            "/mcp",
            headers={"Authorization": "Bearer test_token"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_my_profile",
                    "arguments": {}
                },
                "id": 1
            }
        )

        assert response.status_code == 200
        result = response.json()
        assert "result" in result

    def test_mcp_resources_list(self, authenticated_client):
        """
        EXPECTED: resources/list returns available MCP resources.
        FAILS UNTIL: Resource listing over HTTP is implemented.
        """
        response = authenticated_client.post(
            "/mcp",
            headers={"Authorization": "Bearer test_token"},
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )

        assert response.status_code == 200
        result = response.json()
        assert "result" in result


class TestHTTPServerConfiguration:
    """Tests for HTTP server configuration."""

    def test_server_uses_config_host(self):
        """
        EXPECTED: Server binds to HTTP_HOST from config.
        """
        from odoo_mcp_server.config import Settings

        settings = Settings()
        assert settings.http_host == "0.0.0.0"

    def test_server_uses_config_port(self):
        """
        EXPECTED: Server binds to HTTP_PORT from config.
        """
        from odoo_mcp_server.config import Settings

        settings = Settings()
        assert settings.http_port == 8080

    def test_server_cors_configuration(self):
        """
        EXPECTED: Server should have CORS configured for browser access.
        FAILS UNTIL: CORS middleware is added.
        """
        from odoo_mcp_server.http_server import app

        # Check if CORS middleware is configured
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware):
                cors_middleware = middleware
                break

        assert cors_middleware is not None
