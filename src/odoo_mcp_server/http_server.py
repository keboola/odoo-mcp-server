"""
HTTP MCP Server with OAuth 2.1 Support

Provides HTTP transport for MCP protocol with OAuth authentication.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

from .config import Settings, OAUTH_SCOPES, TOOL_SCOPE_REQUIREMENTS, check_scope_access
from .odoo.client import OdooClient
from .tools import register_tools, execute_tool
from .resources import register_resources, read_resource
from .oauth.resource_server import (
    OAuthResourceServer,
    OAuthMiddleware,
    extract_user_context,
    require_scopes,
)
from .oauth.metadata import ProtectedResourceMetadata
from .oauth.user_mapping import get_employee_for_user, EmployeeNotFoundError
from .tools.employee import execute_employee_tool, EMPLOYEE_TOOLS

logger = logging.getLogger(__name__)

# Global state
settings = Settings()
odoo_client: Optional[OdooClient] = None


def _get_oauth_audience() -> str:
    """
    Get the appropriate OAuth audience based on provider.

    For Google OAuth: audience is the client_id (Google ID tokens have aud=client_id)
    For custom OAuth: audience is the resource identifier
    """
    if settings.is_google_oauth and settings.oauth_client_id:
        return settings.oauth_client_id
    return settings.oauth_resource_identifier


def _get_advertised_scopes() -> list[str]:
    """
    Get scopes to advertise in OAuth metadata.

    For Google OAuth: only advertise standard OpenID scopes (Google doesn't understand custom scopes)
    For custom OAuth: advertise all Odoo scopes
    """
    if settings.is_google_oauth:
        # Only advertise scopes that Google understands
        return ["openid", "email", "profile"]
    return list(OAUTH_SCOPES.keys())


# Initialize resource server at module level (so it's available even without lifespan)
resource_server = OAuthResourceServer(
    resource=settings.oauth_resource_identifier,
    authorization_servers=[settings.oauth_authorization_server],
    audience=_get_oauth_audience(),
    scopes_supported=_get_advertised_scopes(),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global odoo_client, resource_server

    # Initialize Odoo client
    odoo_client = OdooClient(
        url=settings.odoo_url,
        db=settings.odoo_db,
        api_key=settings.odoo_api_key,
        username=settings.odoo_username,
        password=settings.odoo_password,
    )

    # Initialize OAuth resource server
    # For Google OAuth: audience is client_id; for custom OAuth: audience is resource_identifier
    resource_server = OAuthResourceServer(
        resource=settings.oauth_resource_identifier,
        authorization_servers=[settings.oauth_authorization_server],
        audience=_get_oauth_audience(),
        scopes_supported=_get_advertised_scopes(),
    )

    logger.info(f"OAuth provider: {settings.oauth_provider}")
    logger.info(f"OAuth issuer: {settings.oauth_issuer}")
    logger.info(f"OAuth audience: {_get_oauth_audience()}")

    logger.info(f"HTTP MCP Server started on {settings.http_host}:{settings.http_port}")

    yield

    # Cleanup
    if odoo_client:
        await odoo_client.close()


# Create FastAPI app
app = FastAPI(
    title="Odoo MCP Server",
    description="MCP server for Keboola Odoo with OAuth 2.1 authentication",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add OAuth middleware (after CORS so preflight requests work)
@app.middleware("http")
async def oauth_middleware(request: Request, call_next):
    """OAuth authentication middleware."""
    # Skip auth for certain paths
    skip_paths = ["/health", "/.well-known/oauth-protected-resource", "/callback", "/"]
    if request.url.path in skip_paths:
        return await call_next(request)

    # Extract token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "error_description": "Missing Bearer token"},
            headers={"WWW-Authenticate": 'Bearer realm="odoo-mcp"'},
        )

    token = auth_header[7:]

    # Log token info for debugging (first 20 chars only for security)
    token_preview = token[:20] + "..." if len(token) > 20 else token
    logger.info(f"Received token (preview): {token_preview}, length: {len(token)}")

    # In dev/test mode, skip validation for test tokens
    is_test_mode = settings.oauth_dev_mode or settings.debug or settings.yolo_mode or token == "test_token"
    if is_test_mode:
        import os
        dev_email = os.getenv("TEST_USER_EMAIL", "dev@example.com")
        logger.info(f"OAuth dev mode: using email {dev_email}")
        request.state.user = {
            "sub": "dev-user",
            "email": dev_email,
            "employee_id": None,
            "scopes": list(OAUTH_SCOPES.keys()),
            "claims": {},
        }
        return await call_next(request)

    # Validate token
    logger.info(f"Validating token with audience: {resource_server.audience if resource_server else 'N/A'}")
    if resource_server:
        try:
            claims = await resource_server.validate_token_async(token)
            request.state.user = extract_user_context(claims)
            return await call_next(request)
        except Exception as e:
            logger.warning(f"Token validation failed: {type(e).__name__}: {e}")
            logger.warning(f"Token was: {token[:50]}..." if len(token) > 50 else f"Token was: {token}")
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "error_description": str(e)},
                headers={"WWW-Authenticate": 'Bearer realm="odoo-mcp", error="invalid_token"'},
            )

    return await call_next(request)


# =============================================================================
# Health & Metadata Endpoints
# =============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "odoo-mcp-server"}


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """RFC 9728 Protected Resource Metadata endpoint."""
    if not resource_server:
        raise HTTPException(status_code=503, detail="OAuth not configured")

    return resource_server.metadata.to_dict()


@app.get("/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """OAuth authorization code callback."""
    if error:
        return HTMLResponse(
            content=f"<html><body><h1>OAuth Error</h1><p>{error}</p></body></html>",
            status_code=400,
        )

    if code:
        return HTMLResponse(
            content="""
            <html>
            <body>
            <h1>Authorization Successful</h1>
            <p>You can close this window and return to the application.</p>
            <script>
                if (window.opener) {
                    window.opener.postMessage({type: 'oauth_callback', code: '%s', state: '%s'}, '*');
                }
            </script>
            </body>
            </html>
            """ % (code, state or ""),
            status_code=200,
        )

    return HTMLResponse(
        content="<html><body><h1>OAuth Callback</h1></body></html>",
        status_code=200,
    )


# =============================================================================
# MCP Protocol Endpoint
# =============================================================================


class MCPRequest(BaseModel):
    """MCP JSON-RPC request."""

    jsonrpc: str = "2.0"
    method: str
    params: Optional[dict[str, Any]] = None
    id: Optional[int | str] = None


class MCPResponse(BaseModel):
    """MCP JSON-RPC response."""

    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None
    id: Optional[int | str] = None


@app.get("/mcp")
async def mcp_sse_endpoint(request: Request):
    """
    MCP Server-Sent Events endpoint for streamable-http transport.

    This endpoint is used by MCP clients to receive server-initiated messages.
    For now, we just keep the connection alive with periodic heartbeats.
    """
    from starlette.responses import StreamingResponse
    import asyncio

    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async def event_generator():
        """Generate SSE events."""
        # Send initial connection established event
        yield f"data: {{}}\n\n"

        # Keep connection alive with heartbeats
        while True:
            await asyncio.sleep(30)
            # Send heartbeat comment (not a data event)
            yield ": heartbeat\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/mcp")
async def mcp_endpoint(request: Request, mcp_request: MCPRequest):
    """
    MCP JSON-RPC endpoint.

    Handles MCP protocol methods:
    - tools/list: List available tools
    - tools/call: Execute a tool
    - resources/list: List available resources
    - resources/read: Read a resource
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    method = mcp_request.method
    params = mcp_request.params or {}

    try:
        if method == "initialize":
            # MCP protocol initialization
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {
                    "name": "odoo-mcp-server",
                    "version": "0.1.0",
                },
            }
        elif method == "notifications/initialized":
            # Client acknowledges initialization - no response needed
            return MCPResponse(id=mcp_request.id, result={})
        elif method == "tools/list":
            result = await handle_tools_list(user)
        elif method == "tools/call":
            result = await handle_tools_call(params, user)
        elif method == "resources/list":
            result = await handle_resources_list(user)
        elif method == "resources/read":
            result = await handle_resources_read(params, user)
        elif method == "ping":
            result = {}
        else:
            return MCPResponse(
                id=mcp_request.id,
                error={"code": -32601, "message": f"Method not found: {method}"},
            )

        return MCPResponse(id=mcp_request.id, result=result)

    except HTTPException as e:
        return MCPResponse(
            id=mcp_request.id,
            error={"code": -32000, "message": e.detail},
        )
    except Exception as e:
        logger.exception(f"Error handling MCP request: {e}")
        return MCPResponse(
            id=mcp_request.id,
            error={"code": -32603, "message": str(e)},
        )


async def handle_tools_list(user: dict) -> dict:
    """Handle tools/list MCP method."""
    all_tools = register_tools()
    user_scopes = user.get("scopes", [])

    # Filter tools based on user's scopes
    accessible_tools = []
    for tool in all_tools:
        required_scopes = TOOL_SCOPE_REQUIREMENTS.get(tool.name, ["odoo.read"])
        if check_scope_access(required_scopes, user_scopes):
            accessible_tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            })

    return {"tools": accessible_tools}


async def handle_tools_call(params: dict, user: dict) -> dict:
    """Handle tools/call MCP method."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if not tool_name:
        raise HTTPException(status_code=400, detail="Missing tool name")

    # Check scope access
    user_scopes = user.get("scopes", [])
    required_scopes = TOOL_SCOPE_REQUIREMENTS.get(tool_name, ["odoo.read"])

    if not check_scope_access(required_scopes, user_scopes):
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient scope for tool: {tool_name}",
        )

    if not odoo_client:
        raise HTTPException(status_code=503, detail="Odoo client not initialized")

    # Check if this is an employee self-service tool
    employee_tool_names = [t.name for t in EMPLOYEE_TOOLS]
    is_employee_tool = tool_name in employee_tool_names

    if is_employee_tool:
        # Resolve employee_id from OAuth user context
        employee_id = user.get("employee_id")

        if not employee_id:
            # Map OAuth claims to employee
            try:
                claims = user.get("claims", {})
                # Add email from user context if not in claims
                if "email" not in claims:
                    claims["email"] = user.get("email")

                employee_info = await get_employee_for_user(claims, odoo_client)
                employee_id = employee_info["id"]
                logger.info(f"Resolved employee {employee_id} for user {user.get('email')}")
            except EmployeeNotFoundError as e:
                raise HTTPException(
                    status_code=403,
                    detail=f"No Odoo employee found for your account: {e}",
                )

        # Execute employee tool with employee context
        result = await execute_employee_tool(tool_name, arguments, odoo_client, employee_id)
    else:
        # Execute generic tool (CRUD - only for admin users with odoo.write scope)
        result = await execute_tool(tool_name, arguments, odoo_client)

    return {
        "content": [{"type": "text", "text": r.text} for r in result],
    }


async def handle_resources_list(user: dict) -> dict:
    """Handle resources/list MCP method."""
    all_resources = register_resources()

    return {
        "resources": [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mimeType": r.mimeType,
            }
            for r in all_resources
        ]
    }


async def handle_resources_read(params: dict, user: dict) -> dict:
    """Handle resources/read MCP method."""
    uri = params.get("uri")
    if not uri:
        raise HTTPException(status_code=400, detail="Missing resource URI")

    if not odoo_client:
        raise HTTPException(status_code=503, detail="Odoo client not initialized")

    content = await read_resource(uri, odoo_client)

    return {
        "contents": [{"uri": uri, "text": content}],
    }


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run HTTP server."""
    import uvicorn

    uvicorn.run(
        "odoo_mcp_server.http_server:app",
        host=settings.http_host,
        port=settings.http_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
