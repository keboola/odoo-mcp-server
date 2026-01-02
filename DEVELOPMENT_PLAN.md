# Odoo MCP Server Development Plan

## Executive Summary

This document outlines the comprehensive plan for developing an MCP (Model Context Protocol) server that enables AI assistants (Claude, Slack integrations) to securely access Keboola's Odoo 18 ERP instance at `erp.internel.keboola.com` using OAuth 2.1 authentication.

## Research Findings

### Existing MCP Solutions for Odoo

Several MCP servers for Odoo already exist:

| Solution | Features | OAuth Support | Maturity |
|----------|----------|---------------|----------|
| [mcp-server-odoo](https://github.com/ivnvxd/mcp-server-odoo) | Full CRUD, Odoo 17+, model inspection | No (API key/password only) | High |
| [odoo-mcp](https://github.com/tuanle96/mcp-odoo) | XML-RPC, flexible config | No | Medium |
| [Odoo Apps Store MCP](https://apps.odoo.com/apps/modules/17.0/mcp_server) | Odoo module-based | No | Medium |

**Key Gap**: None of the existing solutions support OAuth 2.1 authentication required for multi-user access through Claude or Slack.

### MCP OAuth 2.1 Specification (June 2025)

The MCP specification now mandates:
- **OAuth 2.1 with PKCE** for all authentication flows
- **Dynamic Client Registration (DCR)** per RFC 7591
- **Protected Resource Metadata** per RFC 9728
- **Resource Indicators** per RFC 8707
- **MCP servers as OAuth Resource Servers** (not Authorization Servers)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              End Users                                       │
│                     (Claude Desktop / Slack / API)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MCP Client Layer                                     │
│              (Claude Desktop, Claude Code, Slack Bot)                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  - OAuth 2.1 Client with PKCE                                       │    │
│  │  - Dynamic Client Registration                                      │    │
│  │  - Token Management & Refresh                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────────────┐
│    Authorization Server        │   │         MCP Resource Server           │
│    (OAuth 2.1 Provider)        │   │      (Odoo MCP Server - NEW)          │
│ ┌───────────────────────────┐  │   │ ┌───────────────────────────────────┐ │
│ │ Options:                  │  │   │ │  - Token Validation                │ │
│ │ - Auth0                   │  │   │ │  - Protected Resource Metadata     │ │
│ │ - Google Identity         │  │   │ │  - MCP Tools & Resources           │ │
│ │ - Odoo OAuth Provider     │  │   │ │  - Rate Limiting                   │ │
│ │ - Custom (Keycloak)       │  │   │ │  - Audit Logging                   │ │
│ └───────────────────────────┘  │   │ └───────────────────────────────────┘ │
│ Endpoints:                     │   │ Endpoints:                            │
│ - /.well-known/oauth-authz-svr │   │ - /.well-known/oauth-protected-rsrc   │
│ - /authorize                   │   │ - /mcp (streamable-http)              │
│ - /token                       │   │ - /tools/*                            │
│ - /register (DCR)              │   │ - /resources/*                        │
└───────────────────────────────┘   └───────────────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────────────┐
                                    │         Odoo 18 ERP Instance          │
                                    │      erp.internel.keboola.com         │
                                    │ ┌───────────────────────────────────┐ │
                                    │ │  - XML-RPC / JSON-RPC API         │ │
                                    │ │  - API Keys per User              │ │
                                    │ │  - User-specific Permissions      │ │
                                    │ └───────────────────────────────────┘ │
                                    └───────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| MCP Server | Python 3.12+ | MCP SDK maturity, Odoo XML-RPC support |
| MCP Framework | `mcp` library v1.9.4+ | Official MCP SDK with streamable-http |
| OAuth Library | `authlib` | Full OAuth 2.1 support with PKCE |
| HTTP Framework | FastAPI / Starlette | Async, OpenAPI, OAuth integration |
| Testing | Playwright + pytest | E2E browser testing for OAuth flows |
| Odoo Client | `xmlrpc.client` | Native Odoo API support |
| Auth Server | Auth0 / Google Identity | Managed OAuth 2.1 with DCR support |

## Project Structure

```
odoo-mcp-server/
├── src/
│   └── odoo_mcp_server/
│       ├── __init__.py
│       ├── server.py              # Main MCP server
│       ├── oauth/
│       │   ├── __init__.py
│       │   ├── resource_server.py # OAuth Resource Server logic
│       │   ├── token_validator.py # Token validation
│       │   └── metadata.py        # RFC 9728 metadata
│       ├── odoo/
│       │   ├── __init__.py
│       │   ├── client.py          # Odoo XML-RPC client
│       │   ├── models.py          # Odoo model definitions
│       │   └── permissions.py     # Permission mapping
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── records.py         # CRUD operations
│       │   ├── search.py          # Search operations
│       │   └── reports.py         # Report generation
│       └── resources/
│           ├── __init__.py
│           └── odoo_resources.py  # MCP Resources
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/
│   │   ├── test_oauth.py
│   │   ├── test_odoo_client.py
│   │   └── test_tools.py
│   ├── integration/
│   │   ├── test_mcp_protocol.py
│   │   └── test_odoo_integration.py
│   └── e2e/
│       ├── test_oauth_flow.py     # Playwright OAuth tests
│       ├── test_claude_integration.py
│       └── test_slack_integration.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── config/
│   ├── oauth_config.example.json
│   └── odoo_config.example.json
├── pyproject.toml
├── README.md
└── DEVELOPMENT_PLAN.md
```

---

# Phase 1: Test Infrastructure Setup

## 1.1 Testing Strategy Overview

We employ **Test-Driven Development (TDD)** with three testing layers:

| Layer | Tool | Purpose | Coverage Target |
|-------|------|---------|-----------------|
| Unit | pytest | Individual functions, OAuth logic | 90% |
| Integration | pytest + mcp-test | MCP protocol compliance | 100% protocol |
| E2E | Playwright | OAuth flows, Claude/Slack integration | Critical paths |

## 1.2 Test Environment Setup

### Prerequisites
```bash
# Python environment
python -m venv .venv
source .venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov playwright httpx respx
playwright install chromium

# Install MCP testing utilities
pip install mcp[testing]
```

### Test Configuration (`pytest.ini`)
```ini
[pytest]
testpaths = tests
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    oauth: OAuth-related tests
    odoo: Odoo-related tests
```

---

# Phase 2: Test Scenarios

## 2.1 OAuth Authentication Tests (Playwright E2E)

### Test File: `tests/e2e/test_oauth_flow.py`

```python
"""
OAuth 2.1 Authentication Flow Tests

These tests verify the complete OAuth authentication flow from
MCP client perspective, including PKCE, token exchange, and refresh.
"""
import pytest
from playwright.async_api import async_playwright, Page, Browser
import httpx
import secrets
import hashlib
import base64

# Test Configuration
TEST_CONFIG = {
    "mcp_server_url": "http://localhost:8000",
    "auth_server_url": "https://auth.example.com",  # Auth0 or similar
    "test_user": {
        "email": "test@keboola.com",
        "password": "test_password"  # From environment/secrets
    }
}


class TestOAuthDiscovery:
    """Tests for OAuth 2.1 metadata discovery (RFC 9728)"""

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_protected_resource_metadata_endpoint_exists(self):
        """
        GIVEN: MCP server is running
        WHEN: Client requests /.well-known/oauth-protected-resource
        THEN: Server returns valid RFC 9728 metadata
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TEST_CONFIG['mcp_server_url']}/.well-known/oauth-protected-resource"
            )

            assert response.status_code == 200
            metadata = response.json()

            # Required fields per RFC 9728
            assert "resource" in metadata
            assert "authorization_servers" in metadata
            assert isinstance(metadata["authorization_servers"], list)
            assert len(metadata["authorization_servers"]) > 0

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_authorization_server_discovery(self):
        """
        GIVEN: Protected resource metadata is available
        WHEN: Client follows authorization_servers link
        THEN: Authorization server metadata is accessible
        """
        async with httpx.AsyncClient() as client:
            # Get protected resource metadata
            pr_response = await client.get(
                f"{TEST_CONFIG['mcp_server_url']}/.well-known/oauth-protected-resource"
            )
            pr_metadata = pr_response.json()

            # Follow to authorization server
            auth_server = pr_metadata["authorization_servers"][0]
            as_response = await client.get(
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
    """Tests for OAuth 2.1 Authorization Code Flow with PKCE"""

    @pytest.fixture
    def pkce_challenge(self):
        """Generate PKCE code verifier and challenge"""
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return {"verifier": code_verifier, "challenge": code_challenge}

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_authorization_request_redirects_to_login(
        self, pkce_challenge
    ):
        """
        GIVEN: Valid PKCE challenge and client credentials
        WHEN: Client initiates authorization request
        THEN: User is redirected to authorization server login
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Construct authorization URL
            auth_url = (
                f"{TEST_CONFIG['auth_server_url']}/authorize"
                f"?response_type=code"
                f"&client_id=test_client"
                f"&redirect_uri=http://localhost:8000/callback"
                f"&scope=openid%20odoo.read%20odoo.write"
                f"&code_challenge={pkce_challenge['challenge']}"
                f"&code_challenge_method=S256"
                f"&state=test_state_123"
            )

            await page.goto(auth_url)

            # Should see login form
            await page.wait_for_selector('input[type="email"], input[name="login"]')

            await browser.close()

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_complete_oauth_flow_with_valid_credentials(
        self, pkce_challenge
    ):
        """
        GIVEN: Valid user credentials and PKCE challenge
        WHEN: User completes OAuth login flow
        THEN: Client receives valid access token
        """
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
                f"{TEST_CONFIG['auth_server_url']}/authorize"
                f"?response_type=code"
                f"&client_id=test_client"
                f"&redirect_uri=http://localhost:8000/callback"
                f"&scope=openid%20odoo.read%20odoo.write"
                f"&code_challenge={pkce_challenge['challenge']}"
                f"&code_challenge_method=S256"
                f"&state=test_state_123"
            )

            await page.goto(auth_url)

            # Fill login form
            await page.fill('input[type="email"], input[name="login"]',
                          TEST_CONFIG['test_user']['email'])
            await page.fill('input[type="password"]',
                          TEST_CONFIG['test_user']['password'])
            await page.click('button[type="submit"]')

            # Wait for redirect with code
            await page.wait_for_url("**/callback**", timeout=10000)

            # Extract authorization code
            assert callback_url is not None
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(callback_url)
            params = parse_qs(parsed.query)

            assert "code" in params
            assert params["state"][0] == "test_state_123"

            # Exchange code for token
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    f"{TEST_CONFIG['auth_server_url']}/token",
                    data={
                        "grant_type": "authorization_code",
                        "code": params["code"][0],
                        "redirect_uri": "http://localhost:8000/callback",
                        "client_id": "test_client",
                        "code_verifier": pkce_challenge["verifier"]
                    }
                )

                assert token_response.status_code == 200
                tokens = token_response.json()
                assert "access_token" in tokens
                assert "token_type" in tokens
                assert tokens["token_type"].lower() == "bearer"

            await browser.close()

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_invalid_pkce_verifier_rejected(self, pkce_challenge):
        """
        GIVEN: Valid authorization code
        WHEN: Client provides wrong PKCE verifier
        THEN: Token request is rejected
        """
        # This test requires a valid code - would be part of full flow test
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{TEST_CONFIG['auth_server_url']}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": "valid_code_here",
                    "redirect_uri": "http://localhost:8000/callback",
                    "client_id": "test_client",
                    "code_verifier": "wrong_verifier_intentionally"
                }
            )

            assert token_response.status_code in [400, 401]


class TestTokenValidation:
    """Tests for MCP server token validation"""

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_mcp_endpoint_rejects_missing_token(self):
        """
        GIVEN: MCP server is running
        WHEN: Client calls MCP endpoint without token
        THEN: Server returns 401 Unauthorized
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TEST_CONFIG['mcp_server_url']}/mcp",
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
            )

            assert response.status_code == 401

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_mcp_endpoint_rejects_invalid_token(self):
        """
        GIVEN: MCP server is running
        WHEN: Client calls MCP endpoint with invalid token
        THEN: Server returns 401 Unauthorized
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TEST_CONFIG['mcp_server_url']}/mcp",
                headers={"Authorization": "Bearer invalid_token_here"},
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
            )

            assert response.status_code == 401

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_mcp_endpoint_accepts_valid_token(self, valid_access_token):
        """
        GIVEN: Valid OAuth access token
        WHEN: Client calls MCP endpoint with token
        THEN: Server processes request successfully
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TEST_CONFIG['mcp_server_url']}/mcp",
                headers={"Authorization": f"Bearer {valid_access_token}"},
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
            )

            assert response.status_code == 200
            result = response.json()
            assert "result" in result
            assert "tools" in result["result"]


class TestTokenRefresh:
    """Tests for OAuth token refresh flow"""

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_refresh_token_provides_new_access_token(
        self, valid_refresh_token
    ):
        """
        GIVEN: Valid refresh token
        WHEN: Client requests token refresh
        THEN: New access token is issued
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TEST_CONFIG['auth_server_url']}/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": valid_refresh_token,
                    "client_id": "test_client"
                }
            )

            assert response.status_code == 200
            tokens = response.json()
            assert "access_token" in tokens

    @pytest.mark.e2e
    @pytest.mark.oauth
    async def test_expired_access_token_triggers_refresh(self):
        """
        GIVEN: Expired access token and valid refresh token
        WHEN: MCP client detects 401 response
        THEN: Client automatically refreshes and retries
        """
        # This tests the client-side refresh logic
        pass  # Implementation depends on MCP client library
```

## 2.2 MCP Protocol Compliance Tests

### Test File: `tests/integration/test_mcp_protocol.py`

```python
"""
MCP Protocol Compliance Tests

Verifies the MCP server correctly implements the Model Context Protocol
specification for tools, resources, and communication patterns.
"""
import pytest
import json
from mcp import ClientSession
from mcp.client.stdio import stdio_client


class TestMCPInitialization:
    """Tests for MCP server initialization"""

    @pytest.mark.integration
    async def test_server_responds_to_initialize(self, mcp_client):
        """
        GIVEN: MCP server is running
        WHEN: Client sends initialize request
        THEN: Server returns capabilities and protocol version
        """
        result = await mcp_client.initialize()

        assert result.protocolVersion is not None
        assert result.capabilities is not None
        assert result.serverInfo.name == "odoo-mcp-server"

    @pytest.mark.integration
    async def test_server_declares_tools_capability(self, mcp_client):
        """
        GIVEN: MCP server is initialized
        WHEN: Checking server capabilities
        THEN: Tools capability is declared
        """
        result = await mcp_client.initialize()

        assert result.capabilities.tools is not None

    @pytest.mark.integration
    async def test_server_declares_resources_capability(self, mcp_client):
        """
        GIVEN: MCP server is initialized
        WHEN: Checking server capabilities
        THEN: Resources capability is declared
        """
        result = await mcp_client.initialize()

        assert result.capabilities.resources is not None


class TestMCPTools:
    """Tests for MCP tools functionality"""

    @pytest.mark.integration
    async def test_list_tools_returns_odoo_tools(self, mcp_client):
        """
        GIVEN: MCP server is initialized
        WHEN: Client requests tools list
        THEN: Odoo-specific tools are returned
        """
        await mcp_client.initialize()
        tools = await mcp_client.list_tools()

        tool_names = [t.name for t in tools.tools]

        # Expected core tools
        assert "search_records" in tool_names
        assert "get_record" in tool_names
        assert "create_record" in tool_names
        assert "update_record" in tool_names
        assert "list_models" in tool_names

    @pytest.mark.integration
    async def test_tool_has_valid_schema(self, mcp_client):
        """
        GIVEN: MCP server provides tools
        WHEN: Examining tool definitions
        THEN: Each tool has valid JSON schema for inputs
        """
        await mcp_client.initialize()
        tools = await mcp_client.list_tools()

        for tool in tools.tools:
            assert tool.name is not None
            assert tool.description is not None
            assert tool.inputSchema is not None
            assert tool.inputSchema.get("type") == "object"

    @pytest.mark.integration
    async def test_search_records_tool_schema(self, mcp_client):
        """
        GIVEN: search_records tool is available
        WHEN: Examining its schema
        THEN: Required parameters are defined correctly
        """
        await mcp_client.initialize()
        tools = await mcp_client.list_tools()

        search_tool = next(
            t for t in tools.tools if t.name == "search_records"
        )

        schema = search_tool.inputSchema
        properties = schema.get("properties", {})

        assert "model" in properties
        assert "domain" in properties
        assert "fields" in properties
        assert "limit" in properties


class TestMCPResources:
    """Tests for MCP resources functionality"""

    @pytest.mark.integration
    async def test_list_resources_returns_odoo_resources(self, mcp_client):
        """
        GIVEN: MCP server is initialized
        WHEN: Client requests resources list
        THEN: Odoo resource URIs are returned
        """
        await mcp_client.initialize()
        resources = await mcp_client.list_resources()

        resource_uris = [r.uri for r in resources.resources]

        # Check for expected resource patterns
        assert any("odoo://" in uri for uri in resource_uris)

    @pytest.mark.integration
    async def test_read_models_resource(self, mcp_client):
        """
        GIVEN: Models resource is available
        WHEN: Client reads odoo://models resource
        THEN: List of available Odoo models is returned
        """
        await mcp_client.initialize()

        result = await mcp_client.read_resource("odoo://models")

        assert result.contents is not None
        assert len(result.contents) > 0


class TestMCPErrorHandling:
    """Tests for MCP error handling"""

    @pytest.mark.integration
    async def test_invalid_tool_returns_error(self, mcp_client):
        """
        GIVEN: MCP server is running
        WHEN: Client calls non-existent tool
        THEN: Server returns appropriate error
        """
        await mcp_client.initialize()

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "non_existent_tool",
                arguments={}
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.integration
    async def test_invalid_tool_arguments_returns_error(self, mcp_client):
        """
        GIVEN: Valid tool exists
        WHEN: Client provides invalid arguments
        THEN: Server returns validation error
        """
        await mcp_client.initialize()

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "search_records",
                arguments={"invalid_param": "value"}
            )

        # Should indicate missing required parameter
        assert "model" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()
```

## 2.3 Odoo Integration Tests

### Test File: `tests/integration/test_odoo_integration.py`

```python
"""
Odoo Integration Tests

Tests the MCP server's integration with Odoo ERP, including
record operations, permissions, and data handling.
"""
import pytest


class TestOdooConnection:
    """Tests for Odoo connection handling"""

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_connection_to_odoo_instance(self, odoo_client):
        """
        GIVEN: Valid Odoo credentials
        WHEN: Client attempts to connect
        THEN: Connection is established successfully
        """
        version = await odoo_client.get_version()

        assert version is not None
        assert "18" in version.get("server_version", "")

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_authentication_with_api_key(self, odoo_client):
        """
        GIVEN: Valid API key
        WHEN: Client authenticates
        THEN: User ID is returned
        """
        uid = await odoo_client.authenticate()

        assert uid is not None
        assert isinstance(uid, int)
        assert uid > 0


class TestOdooRecordOperations:
    """Tests for CRUD operations on Odoo records"""

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_search_partners(self, authenticated_mcp_client):
        """
        GIVEN: Authenticated MCP client
        WHEN: Searching for partners
        THEN: Partner records are returned
        """
        result = await authenticated_mcp_client.call_tool(
            "search_records",
            arguments={
                "model": "res.partner",
                "domain": [["is_company", "=", True]],
                "fields": ["name", "email", "phone"],
                "limit": 10
            }
        )

        assert result.content is not None
        records = json.loads(result.content[0].text)
        assert isinstance(records, list)

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_get_single_record(self, authenticated_mcp_client):
        """
        GIVEN: Known record ID
        WHEN: Requesting single record
        THEN: Complete record data is returned
        """
        result = await authenticated_mcp_client.call_tool(
            "get_record",
            arguments={
                "model": "res.partner",
                "record_id": 1,
                "fields": ["name", "email", "phone", "street"]
            }
        )

        assert result.content is not None
        record = json.loads(result.content[0].text)
        assert "name" in record

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_create_and_delete_record(self, authenticated_mcp_client):
        """
        GIVEN: Authenticated client with write permissions
        WHEN: Creating and then deleting a record
        THEN: Operations complete successfully
        """
        # Create
        create_result = await authenticated_mcp_client.call_tool(
            "create_record",
            arguments={
                "model": "res.partner",
                "values": {
                    "name": "MCP Test Partner",
                    "email": "mcp_test@example.com",
                    "is_company": False
                }
            }
        )

        created = json.loads(create_result.content[0].text)
        record_id = created["id"]
        assert record_id > 0

        # Delete (cleanup)
        delete_result = await authenticated_mcp_client.call_tool(
            "delete_record",
            arguments={
                "model": "res.partner",
                "record_id": record_id
            }
        )

        assert "success" in delete_result.content[0].text.lower()

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_update_record(self, authenticated_mcp_client, test_partner_id):
        """
        GIVEN: Existing partner record
        WHEN: Updating record fields
        THEN: Changes are persisted
        """
        # Update
        await authenticated_mcp_client.call_tool(
            "update_record",
            arguments={
                "model": "res.partner",
                "record_id": test_partner_id,
                "values": {"phone": "+1-555-0123"}
            }
        )

        # Verify
        result = await authenticated_mcp_client.call_tool(
            "get_record",
            arguments={
                "model": "res.partner",
                "record_id": test_partner_id,
                "fields": ["phone"]
            }
        )

        record = json.loads(result.content[0].text)
        assert record["phone"] == "+1-555-0123"


class TestOdooPermissions:
    """Tests for Odoo permission handling"""

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_user_can_only_access_permitted_models(
        self, authenticated_mcp_client
    ):
        """
        GIVEN: User with limited permissions
        WHEN: Accessing restricted model
        THEN: Access is denied with clear error
        """
        # Attempt to access a model the test user shouldn't have access to
        with pytest.raises(Exception) as exc_info:
            await authenticated_mcp_client.call_tool(
                "search_records",
                arguments={
                    "model": "ir.config_parameter",  # System model
                    "domain": [],
                    "limit": 1
                }
            )

        assert "access" in str(exc_info.value).lower() or "permission" in str(exc_info.value).lower()

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_list_models_respects_permissions(
        self, authenticated_mcp_client
    ):
        """
        GIVEN: Authenticated user
        WHEN: Listing available models
        THEN: Only accessible models are shown
        """
        result = await authenticated_mcp_client.call_tool(
            "list_models",
            arguments={}
        )

        models = json.loads(result.content[0].text)
        model_names = [m["model"] for m in models]

        # User-facing models should be available
        assert "res.partner" in model_names
        assert "product.product" in model_names

        # System models should not be listed
        # (depends on configuration)


class TestOdooDataFormatting:
    """Tests for data formatting and LLM optimization"""

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_large_result_pagination(self, authenticated_mcp_client):
        """
        GIVEN: Query matching many records
        WHEN: Limit is specified
        THEN: Results are paginated correctly
        """
        result = await authenticated_mcp_client.call_tool(
            "search_records",
            arguments={
                "model": "res.partner",
                "domain": [],
                "limit": 5,
                "offset": 0
            }
        )

        records = json.loads(result.content[0].text)
        assert len(records) <= 5

    @pytest.mark.integration
    @pytest.mark.odoo
    async def test_count_records(self, authenticated_mcp_client):
        """
        GIVEN: Search domain
        WHEN: Requesting count only
        THEN: Total count is returned without full records
        """
        result = await authenticated_mcp_client.call_tool(
            "count_records",
            arguments={
                "model": "res.partner",
                "domain": [["is_company", "=", True]]
            }
        )

        count_data = json.loads(result.content[0].text)
        assert "count" in count_data
        assert isinstance(count_data["count"], int)
```

## 2.4 End-to-End User Journey Tests

### Test File: `tests/e2e/test_user_journeys.py`

```python
"""
End-to-End User Journey Tests

Tests complete user workflows from OAuth login through
Odoo data operations, simulating real Claude/Slack usage.
"""
import pytest
from playwright.async_api import async_playwright


class TestEmployeeInformationJourney:
    """
    User Story: As an employee, I want to check my leave balance
    and submit a leave request through Claude.
    """

    @pytest.mark.e2e
    async def test_employee_views_leave_balance(
        self, authenticated_mcp_client, test_employee_id
    ):
        """
        Complete journey: Employee checks their leave balance
        """
        # Step 1: Get employee record
        employee_result = await authenticated_mcp_client.call_tool(
            "get_record",
            arguments={
                "model": "hr.employee",
                "record_id": test_employee_id,
                "fields": ["name", "department_id", "remaining_leaves"]
            }
        )

        employee = json.loads(employee_result.content[0].text)
        assert "remaining_leaves" in employee

        # Step 2: Get leave types available
        leave_types = await authenticated_mcp_client.call_tool(
            "search_records",
            arguments={
                "model": "hr.leave.type",
                "domain": [["active", "=", True]],
                "fields": ["name", "max_leaves"]
            }
        )

        types = json.loads(leave_types.content[0].text)
        assert len(types) > 0

    @pytest.mark.e2e
    async def test_employee_submits_leave_request(
        self, authenticated_mcp_client, test_employee_id
    ):
        """
        Complete journey: Employee submits a leave request
        """
        # Create leave request
        result = await authenticated_mcp_client.call_tool(
            "create_record",
            arguments={
                "model": "hr.leave",
                "values": {
                    "employee_id": test_employee_id,
                    "holiday_status_id": 1,  # Assumes leave type ID 1 exists
                    "date_from": "2025-02-01",
                    "date_to": "2025-02-03",
                    "name": "Family vacation (MCP test)"
                }
            }
        )

        leave = json.loads(result.content[0].text)
        assert leave["id"] > 0

        # Verify it was created
        verify_result = await authenticated_mcp_client.call_tool(
            "get_record",
            arguments={
                "model": "hr.leave",
                "record_id": leave["id"],
                "fields": ["state", "name"]
            }
        )

        verified = json.loads(verify_result.content[0].text)
        assert verified["state"] in ["draft", "confirm"]


class TestSalesInformationJourney:
    """
    User Story: As a sales person, I want to check my
    sales pipeline and create a new opportunity.
    """

    @pytest.mark.e2e
    async def test_salesperson_views_pipeline(self, authenticated_mcp_client):
        """
        Complete journey: Sales person checks their opportunities
        """
        # Get opportunities in pipeline
        result = await authenticated_mcp_client.call_tool(
            "search_records",
            arguments={
                "model": "crm.lead",
                "domain": [
                    ["type", "=", "opportunity"],
                    ["user_id", "=", 2]  # Test user
                ],
                "fields": ["name", "expected_revenue", "stage_id", "probability"],
                "limit": 20
            }
        )

        opportunities = json.loads(result.content[0].text)
        assert isinstance(opportunities, list)

        # Calculate pipeline value
        total_value = sum(
            opp.get("expected_revenue", 0) * opp.get("probability", 0) / 100
            for opp in opportunities
        )

        assert total_value >= 0  # Just verify calculation works

    @pytest.mark.e2e
    async def test_salesperson_creates_opportunity(
        self, authenticated_mcp_client
    ):
        """
        Complete journey: Sales person creates new opportunity
        """
        # Create opportunity
        result = await authenticated_mcp_client.call_tool(
            "create_record",
            arguments={
                "model": "crm.lead",
                "values": {
                    "name": "MCP Test Opportunity",
                    "type": "opportunity",
                    "expected_revenue": 50000,
                    "probability": 25,
                    "partner_id": 1  # Assumes partner exists
                }
            }
        )

        opp = json.loads(result.content[0].text)
        assert opp["id"] > 0

        # Cleanup
        await authenticated_mcp_client.call_tool(
            "delete_record",
            arguments={
                "model": "crm.lead",
                "record_id": opp["id"]
            }
        )


class TestInventoryCheckJourney:
    """
    User Story: As a warehouse manager, I want to check
    stock levels for specific products.
    """

    @pytest.mark.e2e
    async def test_check_product_stock(self, authenticated_mcp_client):
        """
        Complete journey: Check stock for a product
        """
        # Search for products
        products = await authenticated_mcp_client.call_tool(
            "search_records",
            arguments={
                "model": "product.product",
                "domain": [["type", "=", "product"]],
                "fields": ["name", "default_code", "qty_available"],
                "limit": 5
            }
        )

        product_list = json.loads(products.content[0].text)

        if len(product_list) > 0:
            # Get detailed stock info for first product
            product_id = product_list[0]["id"]

            stock_quants = await authenticated_mcp_client.call_tool(
                "search_records",
                arguments={
                    "model": "stock.quant",
                    "domain": [["product_id", "=", product_id]],
                    "fields": ["location_id", "quantity", "reserved_quantity"]
                }
            )

            quants = json.loads(stock_quants.content[0].text)
            assert isinstance(quants, list)
```

## 2.5 Test Fixtures

### Test File: `tests/conftest.py`

```python
"""
Pytest Fixtures for Odoo MCP Server Tests

Provides reusable fixtures for authentication, MCP clients,
and test data management.
"""
import pytest
import asyncio
import os
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# Configuration from environment
TEST_CONFIG = {
    "mcp_server_url": os.getenv("TEST_MCP_SERVER_URL", "http://localhost:8000"),
    "auth_server_url": os.getenv("TEST_AUTH_SERVER_URL", "https://auth.example.com"),
    "odoo_url": os.getenv("TEST_ODOO_URL", "https://erp.internel.keboola.com"),
    "odoo_db": os.getenv("TEST_ODOO_DB", "keboola"),
    "test_user_email": os.getenv("TEST_USER_EMAIL"),
    "test_user_password": os.getenv("TEST_USER_PASSWORD"),
    "test_api_key": os.getenv("TEST_ODOO_API_KEY"),
}


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def valid_access_token():
    """
    Obtain a valid OAuth access token for testing.

    In CI/CD, this could use a service account or test credentials.
    """
    async with httpx.AsyncClient() as client:
        # Use client credentials grant for testing
        # (requires appropriate OAuth app configuration)
        response = await client.post(
            f"{TEST_CONFIG['auth_server_url']}/token",
            data={
                "grant_type": "client_credentials",
                "client_id": os.getenv("TEST_CLIENT_ID"),
                "client_secret": os.getenv("TEST_CLIENT_SECRET"),
                "scope": "openid odoo.read odoo.write"
            }
        )

        if response.status_code != 200:
            pytest.skip("Could not obtain test access token")

        tokens = response.json()
        return tokens["access_token"]


@pytest.fixture(scope="session")
async def valid_refresh_token():
    """Obtain a valid refresh token for testing"""
    # Similar to access token, but returns refresh token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TEST_CONFIG['auth_server_url']}/token",
            data={
                "grant_type": "client_credentials",
                "client_id": os.getenv("TEST_CLIENT_ID"),
                "client_secret": os.getenv("TEST_CLIENT_SECRET"),
                "scope": "openid odoo.read odoo.write offline_access"
            }
        )

        if response.status_code != 200:
            pytest.skip("Could not obtain test refresh token")

        tokens = response.json()
        return tokens.get("refresh_token")


@pytest.fixture
async def mcp_client():
    """Create unauthenticated MCP client for protocol tests"""
    async with streamable_http_client(
        TEST_CONFIG["mcp_server_url"] + "/mcp"
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            yield session


@pytest.fixture
async def authenticated_mcp_client(valid_access_token):
    """Create authenticated MCP client"""
    headers = {"Authorization": f"Bearer {valid_access_token}"}

    async with streamable_http_client(
        TEST_CONFIG["mcp_server_url"] + "/mcp",
        headers=headers
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@pytest.fixture
async def odoo_client():
    """Create direct Odoo client for integration tests"""
    from odoo_mcp_server.odoo.client import OdooClient

    client = OdooClient(
        url=TEST_CONFIG["odoo_url"],
        db=TEST_CONFIG["odoo_db"],
        api_key=TEST_CONFIG["test_api_key"]
    )

    yield client

    await client.close()


@pytest.fixture
async def test_partner_id(authenticated_mcp_client):
    """Create a test partner and return its ID, cleanup after test"""
    result = await authenticated_mcp_client.call_tool(
        "create_record",
        arguments={
            "model": "res.partner",
            "values": {
                "name": f"Test Partner {asyncio.current_task().get_name()}",
                "email": "test_fixture@example.com"
            }
        }
    )

    import json
    record = json.loads(result.content[0].text)
    record_id = record["id"]

    yield record_id

    # Cleanup
    try:
        await authenticated_mcp_client.call_tool(
            "delete_record",
            arguments={
                "model": "res.partner",
                "record_id": record_id
            }
        )
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
async def test_employee_id(authenticated_mcp_client):
    """Get or create a test employee"""
    # Try to find existing test employee
    result = await authenticated_mcp_client.call_tool(
        "search_records",
        arguments={
            "model": "hr.employee",
            "domain": [["name", "=", "MCP Test Employee"]],
            "limit": 1
        }
    )

    import json
    employees = json.loads(result.content[0].text)

    if employees:
        return employees[0]["id"]

    # Create if not exists
    create_result = await authenticated_mcp_client.call_tool(
        "create_record",
        arguments={
            "model": "hr.employee",
            "values": {
                "name": "MCP Test Employee"
            }
        }
    )

    employee = json.loads(create_result.content[0].text)
    return employee["id"]
```

---

# Phase 3: Development Implementation Plan

## 3.1 Sprint Overview

| Sprint | Duration | Focus Area | Deliverables |
|--------|----------|------------|--------------|
| 1 | 1 sprint | Foundation | Project setup, CI/CD, basic MCP server |
| 2 | 1 sprint | Odoo Integration | Odoo client, CRUD tools, resources |
| 3 | 1 sprint | OAuth Implementation | Resource server, token validation |
| 4 | 1 sprint | Claude/Slack Integration | Remote MCP, production deployment |

## 3.2 Sprint 1: Foundation

### Goals
- Set up project infrastructure
- Implement basic MCP server skeleton
- Configure CI/CD pipeline
- Pass initial protocol compliance tests

### Tasks

#### 1.1 Project Setup
```bash
# Initialize project
cd /home/coder/Devel/keboola/odoo-mcp-server
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install mcp[cli] fastapi uvicorn authlib httpx pytest pytest-asyncio playwright
```

#### 1.2 Create `pyproject.toml`
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "keboola-odoo-mcp-server"
version = "0.1.0"
description = "MCP server for Keboola Odoo ERP with OAuth 2.1"
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
authors = [
    { name = "Keboola", email = "dev@keboola.com" }
]
dependencies = [
    "mcp>=1.9.4",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "authlib>=1.4.0",
    "httpx>=0.28.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "playwright>=1.49.0",
    "respx>=0.22.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[project.scripts]
odoo-mcp-server = "odoo_mcp_server.server:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "oauth: OAuth-related tests",
    "odoo: Odoo-related tests",
]

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.mypy]
python_version = "3.12"
strict = true
```

#### 1.3 Implement Basic MCP Server

```python
# src/odoo_mcp_server/server.py
"""
Keboola Odoo MCP Server

Main entry point for the MCP server with OAuth 2.1 support.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, Resource

from .config import Settings
from .odoo.client import OdooClient
from .tools import register_tools
from .resources import register_resources

logger = logging.getLogger(__name__)

# Initialize server
server = Server("odoo-mcp-server")
settings = Settings()
odoo_client: OdooClient | None = None


@asynccontextmanager
async def lifespan():
    """Manage server lifecycle"""
    global odoo_client

    odoo_client = OdooClient(
        url=settings.odoo_url,
        db=settings.odoo_db,
        api_key=settings.odoo_api_key
    )

    yield

    if odoo_client:
        await odoo_client.close()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return available tools"""
    return register_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool"""
    from .tools import execute_tool
    return await execute_tool(name, arguments, odoo_client)


@server.list_resources()
async def list_resources() -> list[Resource]:
    """Return available resources"""
    return register_resources()


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource"""
    from .resources import read_resource
    return await read_resource(uri, odoo_client)


def main():
    """Main entry point"""
    import mcp.server.stdio

    async def run():
        async with lifespan():
            async with mcp.server.stdio.stdio_server() as (read, write):
                await server.run(
                    read, write,
                    InitializationOptions(
                        server_name="odoo-mcp-server",
                        server_version="0.1.0"
                    )
                )

    asyncio.run(run())


if __name__ == "__main__":
    main()
```

#### 1.4 GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
          playwright install chromium

      - name: Lint
        run: ruff check .

      - name: Type check
        run: mypy src/

      - name: Unit tests
        run: pytest tests/unit -v --cov=src/

      - name: Integration tests
        run: pytest tests/integration -v
        env:
          TEST_ODOO_URL: ${{ secrets.TEST_ODOO_URL }}
          TEST_ODOO_API_KEY: ${{ secrets.TEST_ODOO_API_KEY }}
```

### Sprint 1 Acceptance Criteria
- [ ] All unit tests pass
- [ ] MCP protocol compliance tests pass
- [ ] CI pipeline runs successfully
- [ ] Code coverage > 80%

## 3.3 Sprint 2: Odoo Integration

### Goals
- Implement Odoo XML-RPC client
- Create CRUD tools for common models
- Implement resource endpoints
- Pass Odoo integration tests

### Tasks

#### 2.1 Odoo Client Implementation

```python
# src/odoo_mcp_server/odoo/client.py
"""
Odoo XML-RPC Client

Handles communication with Odoo ERP instance.
"""
import xmlrpc.client
from typing import Any
import asyncio
from functools import partial


class OdooClient:
    """Async wrapper for Odoo XML-RPC API"""

    def __init__(
        self,
        url: str,
        db: str,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None
    ):
        self.url = url.rstrip("/")
        self.db = db
        self.api_key = api_key
        self.username = username
        self.password = password

        self._common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common"
        )
        self._models = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object"
        )
        self._uid: int | None = None

    async def _run_in_executor(self, func, *args):
        """Run blocking XML-RPC call in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, partial(func, *args)
        )

    async def get_version(self) -> dict:
        """Get Odoo server version"""
        return await self._run_in_executor(self._common.version)

    async def authenticate(self) -> int:
        """Authenticate and return user ID"""
        if self._uid:
            return self._uid

        if self.api_key:
            # API key authentication
            self._uid = await self._run_in_executor(
                self._common.authenticate,
                self.db, self.username or "", self.api_key, {}
            )
        else:
            self._uid = await self._run_in_executor(
                self._common.authenticate,
                self.db, self.username, self.password, {}
            )

        if not self._uid:
            raise ValueError("Authentication failed")

        return self._uid

    async def execute(
        self,
        model: str,
        method: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute method on Odoo model"""
        uid = await self.authenticate()

        return await self._run_in_executor(
            self._models.execute_kw,
            self.db,
            uid,
            self.api_key or self.password,
            model,
            method,
            args,
            kwargs
        )

    async def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str | None = None
    ) -> list[dict]:
        """Search and read records"""
        kwargs = {"limit": limit, "offset": offset}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order

        return await self.execute(model, "search_read", domain, **kwargs)

    async def read(
        self,
        model: str,
        ids: list[int],
        fields: list[str] | None = None
    ) -> list[dict]:
        """Read specific records"""
        kwargs = {}
        if fields:
            kwargs["fields"] = fields

        return await self.execute(model, "read", ids, **kwargs)

    async def create(self, model: str, values: dict) -> int:
        """Create new record"""
        return await self.execute(model, "create", values)

    async def write(
        self,
        model: str,
        ids: list[int],
        values: dict
    ) -> bool:
        """Update records"""
        return await self.execute(model, "write", ids, values)

    async def unlink(self, model: str, ids: list[int]) -> bool:
        """Delete records"""
        return await self.execute(model, "unlink", ids)

    async def search_count(self, model: str, domain: list) -> int:
        """Count matching records"""
        return await self.execute(model, "search_count", domain)

    async def fields_get(
        self,
        model: str,
        attributes: list[str] | None = None
    ) -> dict:
        """Get model field definitions"""
        kwargs = {}
        if attributes:
            kwargs["attributes"] = attributes

        return await self.execute(model, "fields_get", **kwargs)

    async def close(self):
        """Cleanup resources"""
        pass  # XML-RPC is stateless
```

#### 2.2 MCP Tools Implementation

```python
# src/odoo_mcp_server/tools/records.py
"""
Odoo Record CRUD Tools

MCP tools for creating, reading, updating, and deleting Odoo records.
"""
import json
from typing import Any
from mcp.types import Tool, TextContent

from ..odoo.client import OdooClient


TOOLS = [
    Tool(
        name="search_records",
        description="Search for records in an Odoo model with filters",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Odoo model name (e.g., 'res.partner')"
                },
                "domain": {
                    "type": "array",
                    "description": "Search domain filters",
                    "default": []
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to return"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum records to return",
                    "default": 20
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of records to skip",
                    "default": 0
                }
            },
            "required": ["model"]
        }
    ),
    Tool(
        name="get_record",
        description="Get a single record by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Odoo model name"
                },
                "record_id": {
                    "type": "integer",
                    "description": "Record ID"
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to return"
                }
            },
            "required": ["model", "record_id"]
        }
    ),
    Tool(
        name="create_record",
        description="Create a new record in Odoo",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Odoo model name"
                },
                "values": {
                    "type": "object",
                    "description": "Field values for new record"
                }
            },
            "required": ["model", "values"]
        }
    ),
    Tool(
        name="update_record",
        description="Update an existing record",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Odoo model name"
                },
                "record_id": {
                    "type": "integer",
                    "description": "Record ID to update"
                },
                "values": {
                    "type": "object",
                    "description": "Field values to update"
                }
            },
            "required": ["model", "record_id", "values"]
        }
    ),
    Tool(
        name="delete_record",
        description="Delete a record",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Odoo model name"
                },
                "record_id": {
                    "type": "integer",
                    "description": "Record ID to delete"
                }
            },
            "required": ["model", "record_id"]
        }
    ),
    Tool(
        name="count_records",
        description="Count records matching criteria",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Odoo model name"
                },
                "domain": {
                    "type": "array",
                    "description": "Search domain filters",
                    "default": []
                }
            },
            "required": ["model"]
        }
    ),
    Tool(
        name="list_models",
        description="List available Odoo models",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    )
]


async def execute_tool(
    name: str,
    arguments: dict[str, Any],
    client: OdooClient
) -> list[TextContent]:
    """Execute a tool and return results"""

    if name == "search_records":
        records = await client.search_read(
            model=arguments["model"],
            domain=arguments.get("domain", []),
            fields=arguments.get("fields"),
            limit=arguments.get("limit", 20),
            offset=arguments.get("offset", 0)
        )
        return [TextContent(type="text", text=json.dumps(records, default=str))]

    elif name == "get_record":
        records = await client.read(
            model=arguments["model"],
            ids=[arguments["record_id"]],
            fields=arguments.get("fields")
        )
        if not records:
            return [TextContent(type="text", text=json.dumps({"error": "Record not found"}))]
        return [TextContent(type="text", text=json.dumps(records[0], default=str))]

    elif name == "create_record":
        record_id = await client.create(
            model=arguments["model"],
            values=arguments["values"]
        )
        return [TextContent(type="text", text=json.dumps({"id": record_id}))]

    elif name == "update_record":
        success = await client.write(
            model=arguments["model"],
            ids=[arguments["record_id"]],
            values=arguments["values"]
        )
        return [TextContent(type="text", text=json.dumps({"success": success}))]

    elif name == "delete_record":
        success = await client.unlink(
            model=arguments["model"],
            ids=[arguments["record_id"]]
        )
        return [TextContent(type="text", text=json.dumps({"success": success}))]

    elif name == "count_records":
        count = await client.search_count(
            model=arguments["model"],
            domain=arguments.get("domain", [])
        )
        return [TextContent(type="text", text=json.dumps({"count": count}))]

    elif name == "list_models":
        # Get accessible models
        models = await client.search_read(
            model="ir.model",
            domain=[["transient", "=", False]],
            fields=["model", "name"],
            limit=100
        )
        return [TextContent(type="text", text=json.dumps(models, default=str))]

    else:
        raise ValueError(f"Unknown tool: {name}")
```

### Sprint 2 Acceptance Criteria
- [ ] All Odoo integration tests pass
- [ ] CRUD operations work for res.partner, crm.lead, hr.leave
- [ ] Error handling covers common failure cases
- [ ] Connection pooling implemented

## 3.4 Sprint 3: OAuth Implementation

### Goals
- Implement OAuth 2.1 Resource Server
- Set up token validation
- Configure Protected Resource Metadata (RFC 9728)
- Pass OAuth authentication tests

### Tasks

#### 3.1 OAuth Resource Server

```python
# src/odoo_mcp_server/oauth/resource_server.py
"""
OAuth 2.1 Resource Server Implementation

Handles token validation and protected resource metadata.
"""
from typing import Any
import httpx
from authlib.oauth2.rfc9068 import JWTBearerTokenValidator
from authlib.jose import jwt
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class OAuthResourceServer:
    """OAuth 2.1 Resource Server for MCP"""

    def __init__(
        self,
        authorization_server: str,
        resource_identifier: str,
        issuer: str | None = None
    ):
        self.authorization_server = authorization_server
        self.resource_identifier = resource_identifier
        self.issuer = issuer or authorization_server

        self._jwks: dict | None = None
        self._as_metadata: dict | None = None

    async def fetch_authorization_server_metadata(self) -> dict:
        """Fetch OAuth Authorization Server Metadata"""
        if self._as_metadata:
            return self._as_metadata

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.authorization_server}/.well-known/oauth-authorization-server"
            )
            response.raise_for_status()
            self._as_metadata = response.json()
            return self._as_metadata

    async def fetch_jwks(self) -> dict:
        """Fetch JSON Web Key Set for token validation"""
        if self._jwks:
            return self._jwks

        metadata = await self.fetch_authorization_server_metadata()
        jwks_uri = metadata.get("jwks_uri")

        if not jwks_uri:
            raise ValueError("JWKS URI not found in AS metadata")

        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri)
            response.raise_for_status()
            self._jwks = response.json()
            return self._jwks

    async def validate_token(self, token: str) -> dict:
        """
        Validate access token and return claims.

        Validates:
        - Signature against JWKS
        - Expiration (exp)
        - Issuer (iss)
        - Audience (aud) matches resource identifier
        """
        jwks = await self.fetch_jwks()

        try:
            claims = jwt.decode(
                token,
                jwks
            )

            # Validate standard claims
            claims.validate()

            # Validate issuer
            if claims.get("iss") != self.issuer:
                raise ValueError("Invalid issuer")

            # Validate audience/resource indicator
            aud = claims.get("aud", [])
            if isinstance(aud, str):
                aud = [aud]

            if self.resource_identifier not in aud:
                raise ValueError("Invalid audience")

            return dict(claims)

        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )

    def get_protected_resource_metadata(self) -> dict:
        """
        Return Protected Resource Metadata per RFC 9728.

        This is served at /.well-known/oauth-protected-resource
        """
        return {
            "resource": self.resource_identifier,
            "authorization_servers": [self.authorization_server],
            "bearer_methods_supported": ["header"],
            "resource_documentation": "https://github.com/keboola/odoo-mcp-server"
        }


class OAuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for OAuth token validation"""

    def __init__(self, app, resource_server: OAuthResourceServer):
        super().__init__(app)
        self.resource_server = resource_server

        # Paths that don't require authentication
        self.public_paths = {
            "/.well-known/oauth-protected-resource",
            "/health",
            "/docs",
            "/openapi.json"
        }

    async def dispatch(self, request: Request, call_next):
        # Allow public paths
        if request.url.path in self.public_paths:
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header",
                headers={"WWW-Authenticate": "Bearer"}
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate token
        claims = await self.resource_server.validate_token(token)

        # Add claims to request state for downstream use
        request.state.oauth_claims = claims
        request.state.user_id = claims.get("sub")

        return await call_next(request)
```

#### 3.2 HTTP Transport with OAuth

```python
# src/odoo_mcp_server/http_server.py
"""
HTTP Server with OAuth 2.1 Support

Provides streamable-http transport for MCP with OAuth authentication.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from .oauth.resource_server import OAuthResourceServer, OAuthMiddleware
from .config import Settings
from .server import server as mcp_server

settings = Settings()

# Initialize OAuth Resource Server
oauth_rs = OAuthResourceServer(
    authorization_server=settings.oauth_authorization_server,
    resource_identifier=settings.oauth_resource_identifier,
    issuer=settings.oauth_issuer
)

# Create FastAPI app
app = FastAPI(
    title="Keboola Odoo MCP Server",
    version="0.1.0"
)

# Add OAuth middleware
app.add_middleware(OAuthMiddleware, resource_server=oauth_rs)


@app.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata():
    """RFC 9728 Protected Resource Metadata"""
    return JSONResponse(oauth_rs.get_protected_resource_metadata())


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    MCP over HTTP endpoint.

    Handles JSON-RPC requests for MCP protocol.
    """
    # Get user context from OAuth claims
    user_id = request.state.user_id

    # Process MCP request
    body = await request.json()

    # Route to MCP server
    # (Implementation depends on MCP library version)
    response = await mcp_server.handle_request(body, user_context={"user_id": user_id})

    return JSONResponse(response)


def main():
    """Run HTTP server"""
    uvicorn.run(
        app,
        host=settings.http_host,
        port=settings.http_port
    )


if __name__ == "__main__":
    main()
```

### Sprint 3 Acceptance Criteria
- [ ] All OAuth tests pass
- [ ] Protected Resource Metadata served correctly
- [ ] Token validation works with Auth0/Google
- [ ] User context propagated to Odoo queries

## 3.5 Sprint 4: Production & Integration

### Goals
- Deploy to GCP Cloud Run
- Configure Claude Desktop integration
- Set up Slack bot integration
- Complete E2E user journey tests

### Tasks

#### 4.1 Docker Configuration

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/

# Run server
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "odoo_mcp_server.http_server"]
```

#### 4.2 Cloud Run Deployment

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/odoo-mcp-server', '-f', 'docker/Dockerfile', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/odoo-mcp-server']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'odoo-mcp-server'
      - '--image=gcr.io/$PROJECT_ID/odoo-mcp-server'
      - '--region=europe-west1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--set-env-vars'
      - 'ODOO_URL=https://erp.internel.keboola.com'
```

#### 4.3 Claude Desktop Configuration

```json
{
  "mcpServers": {
    "keboola-odoo": {
      "url": "https://odoo-mcp-server-xxxxx.run.app/mcp",
      "transport": "streamable-http",
      "oauth": {
        "client_id": "claude-desktop",
        "authorization_server": "https://auth.keboola.com",
        "scopes": ["openid", "odoo.read", "odoo.write"]
      }
    }
  }
}
```

### Sprint 4 Acceptance Criteria
- [ ] All E2E tests pass
- [ ] Cloud Run deployment works
- [ ] Claude Desktop can authenticate and access Odoo
- [ ] Slack integration functional
- [ ] Documentation complete

---

# Appendix A: Test Commands Reference

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m e2e                     # End-to-end tests only
pytest -m oauth                   # OAuth tests only
pytest -m odoo                    # Odoo tests only

# Run with coverage
pytest --cov=src/ --cov-report=html

# Run Playwright tests with browser visible
pytest tests/e2e -m e2e --headed

# Run specific test file
pytest tests/e2e/test_oauth_flow.py -v

# Run with specific Odoo instance
TEST_ODOO_URL=https://erp.internel.keboola.com pytest -m odoo
```

# Appendix B: Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ODOO_URL` | Odoo instance URL | Yes |
| `ODOO_DB` | Odoo database name | Yes |
| `ODOO_API_KEY` | Odoo API key for authentication | Yes* |
| `ODOO_USERNAME` | Odoo username (if not using API key) | No |
| `ODOO_PASSWORD` | Odoo password (if not using API key) | No |
| `OAUTH_PROVIDER` | OAuth provider: "google" or "custom" | No (default: google) |
| `OAUTH_CLIENT_ID` | OAuth Client ID (Google client_id for Google OAuth) | Yes |
| `OAUTH_CLIENT_SECRET` | OAuth Client Secret | Yes |
| `OAUTH_AUTHORIZATION_SERVER` | OAuth 2.1 Authorization Server URL | No (default: https://accounts.google.com) |
| `OAUTH_AUTHORIZATION_ENDPOINT` | OAuth authorization endpoint | No (default: Google's endpoint) |
| `OAUTH_TOKEN_ENDPOINT` | OAuth token endpoint | No (default: Google's endpoint) |
| `OAUTH_JWKS_URI` | JWKS endpoint for token validation | No (default: Google's JWKS) |
| `OAUTH_ISSUER` | Token issuer | No (default: https://accounts.google.com) |
| `OAUTH_RESOURCE_IDENTIFIER` | Resource identifier for this server | Yes |
| `OAUTH_REDIRECT_URI` | OAuth callback URL | Yes |
| `OAUTH_SCOPES` | OAuth scopes to request | No (default: openid email profile) |
| `OAUTH_DEV_MODE` | Skip OAuth validation (dev only!) | No (default: false) |
| `HTTP_HOST` | HTTP server host | No (default: 0.0.0.0) |
| `HTTP_PORT` | HTTP server port | No (default: 8080) |

---

# Appendix C: Google OAuth Setup for Claude.ai Integration

## Overview

This MCP server is designed to integrate with Claude.ai using Google OAuth as the identity provider. This allows Claude.ai users to authenticate with their Google accounts and access Odoo resources based on their email domain.

## Architecture

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│   Claude.ai     │────▶│  Google OAuth 2.0   │     │  Odoo MCP       │
│   (MCP Client)  │     │  (Authorization     │────▶│  Server         │
│                 │◀────│   Server)           │     │  (Resource      │
└─────────────────┘     └─────────────────────┘     │   Server)       │
                                                     └────────┬────────┘
                                                              │
                                                              ▼
                                                     ┌─────────────────┐
                                                     │   Odoo 18 ERP   │
                                                     │   (XML-RPC)     │
                                                     └─────────────────┘
```

## Google Cloud Console Setup

### 1. Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select existing
3. Go to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application"
6. Configure:
   - **Name**: "Odoo MCP Server"
   - **Authorized redirect URIs**:
     ```
     https://claude.ai/oauth/callback
     https://claude.ai/api/auth/callback
     https://api.claude.ai/oauth/callback
     https://claude.ai/auth/callback
     https://claude.ai/api/mcp/auth_callback
     https://<your-mcp-server-url>/oauth/callback
     ```

### 2. Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select "Internal" (for organization) or "External" (for public)
3. Configure:
   - **App name**: "Keboola Odoo MCP Server"
   - **User support email**: Your support email
   - **Scopes**:
     - `openid`
     - `email`
     - `profile`
   - **Authorized domains**: Your domain (e.g., keboola.com)

## MCP Server Configuration

### Environment Variables (.env)

```bash
# Google OAuth
OAUTH_PROVIDER=google
OAUTH_CLIENT_ID=<your-google-client-id>.apps.googleusercontent.com
OAUTH_CLIENT_SECRET=<your-google-client-secret>

# Google OAuth endpoints (defaults - usually don't need to change)
OAUTH_AUTHORIZATION_SERVER=https://accounts.google.com
OAUTH_AUTHORIZATION_ENDPOINT=https://accounts.google.com/o/oauth2/v2/auth
OAUTH_TOKEN_ENDPOINT=https://oauth2.googleapis.com/token
OAUTH_JWKS_URI=https://www.googleapis.com/oauth2/v3/certs
OAUTH_ISSUER=https://accounts.google.com

# Your MCP server URL
OAUTH_RESOURCE_IDENTIFIER=https://your-mcp-server.example.com
OAUTH_REDIRECT_URI=https://your-mcp-server.example.com/oauth/callback

# Odoo connection
ODOO_URL=https://erp.internal.keboola.com
ODOO_DB=keboola-community
ODOO_API_KEY=<your-odoo-api-key>
```

## Token Validation

Google ID tokens are validated using:
1. **JWKS Verification**: Tokens are verified using Google's public JWKS at `https://www.googleapis.com/oauth2/v3/certs`
2. **Issuer Check**: Must be `https://accounts.google.com`
3. **Audience Check**: Must match your OAuth client_id
4. **Expiration Check**: Token must not be expired
5. **Email Verification**: `email_verified` claim should be true

## Scope Mapping

Since Google ID tokens don't include custom scopes, the MCP server grants default scopes based on the authenticated user's email:

| User Type | Email Domain | Granted Scopes |
|-----------|--------------|----------------|
| Internal | @keboola.com | Full access: `odoo.read`, `odoo.write`, `odoo.hr.*`, `odoo.leave.*`, `odoo.documents.*` |
| External | Any verified | Read-only: `odoo.read`, `odoo.hr.profile`, `odoo.hr.directory`, `odoo.leave.read`, `odoo.documents.read` |

## Claude.ai MCP Server Configuration

To add this MCP server to Claude.ai:

1. Go to Claude.ai Settings > MCP Servers
2. Click "Add Server"
3. Configure:
   - **Name**: "Keboola Odoo"
   - **URL**: `https://your-mcp-server.example.com/mcp`
   - **Transport**: `streamable-http`
   - **Authentication**: OAuth 2.0 (will use Google sign-in)

## Troubleshooting

### Common Issues

1. **"Invalid audience" error**
   - Ensure `OAUTH_CLIENT_ID` matches the client ID in Google Console
   - The audience in Google ID tokens is the client_id, not the resource identifier

2. **"Email not verified" warning**
   - User's Google account email is not verified
   - User can still authenticate but with limited functionality

3. **"Token expired" error**
   - Google ID tokens expire after 1 hour
   - Claude.ai should automatically refresh tokens

4. **CORS errors**
   - Ensure your MCP server allows CORS from Claude.ai domains
   - Check the `allow_origins` setting in the HTTP server configuration

---

# Sources

## Existing MCP Solutions
- [mcp-server-odoo (ivnvxd)](https://github.com/ivnvxd/mcp-server-odoo)
- [odoo-mcp (tuanle96)](https://github.com/tuanle96/mcp-odoo)
- [mcp-server-odoo on PyPI](https://pypi.org/project/mcp-server-odoo/)

## OAuth & MCP Specification
- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [Auth0 MCP Specs Update (June 2025)](https://auth0.com/blog/mcp-specs-update-all-about-auth/)
- [MCP OAuth 2.1 and PKCE](https://aembit.io/blog/mcp-oauth-2-1-pkce-and-the-future-of-ai-authorization/)
- [Descope MCP Auth Spec Analysis](https://www.descope.com/blog/post/mcp-auth-spec)

## Odoo Authentication
- [API OAuth2 Authentication (Odoo 18)](https://apps.odoo.com/apps/modules/18.0/api_auth_oauth2)
- [Odoo 18 External API Documentation](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)

## Claude Integration
- [Building Custom Connectors via Remote MCP Servers](https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers)
- [MCP Server Setup with OAuth and Claude.ai](https://medium.com/neural-engineer/mcp-server-setup-with-oauth-authentication-using-auth0-and-claude-ai-remote-mcp-integration-8329b65e6664)
