"""Configuration management for Odoo MCP Server."""

from pydantic_settings import BaseSettings

# =============================================================================
# OAuth Scope Definitions (Feedback 4.1 - Granular Scopes)
# =============================================================================

OAUTH_SCOPES = {
    # Standard OpenID scopes
    "openid": "OpenID Connect authentication",
    "profile": "User profile information",
    "email": "User email address",

    # Generic Odoo scopes (read/write any model)
    "odoo.read": "Read any Odoo data",
    "odoo.write": "Write any Odoo data",

    # HR/Employee-specific scopes (granular access)
    "odoo.hr.profile": "Read own employee profile",
    "odoo.hr.profile.write": "Update own employee contact information",
    "odoo.hr.team": "Read team/department members",
    "odoo.hr.directory": "Search employee directory",

    # Leave management scopes
    "odoo.leave.read": "Read own leave balance and requests",
    "odoo.leave.write": "Create/cancel leave requests",
    "odoo.leave.approve": "Approve team leave requests (managers)",

    # Document management scopes
    "odoo.documents.read": "Read own HR documents",
    "odoo.documents.write": "Upload identity documents",
}

# Scope requirements for each tool
TOOL_SCOPE_REQUIREMENTS = {
    # Profile tools (Employee Self-Service)
    "get_my_profile": ["odoo.hr.profile", "odoo.read"],
    "get_my_manager": ["odoo.hr.profile", "odoo.read"],
    "get_my_team": ["odoo.hr.team", "odoo.read"],
    "find_colleague": ["odoo.hr.directory", "odoo.read"],
    "get_direct_reports": ["odoo.hr.team", "odoo.read"],
    "update_my_contact": ["odoo.hr.profile.write", "odoo.write"],

    # Leave tools (Employee Self-Service)
    "get_my_leave_balance": ["odoo.leave.read", "odoo.read"],
    "get_my_leave_requests": ["odoo.leave.read", "odoo.read"],
    "request_leave": ["odoo.leave.write", "odoo.write"],
    "cancel_leave_request": ["odoo.leave.write", "odoo.write"],
    "get_public_holidays": ["odoo.leave.read", "odoo.read"],

    # Document tools (Employee Self-Service)
    "get_my_documents": ["odoo.documents.read", "odoo.read"],
    "get_document_categories": ["odoo.documents.read", "odoo.read"],
    "upload_identity_document": ["odoo.documents.write", "odoo.write"],
    "download_document": ["odoo.documents.read", "odoo.read"],
    "get_document_details": ["odoo.documents.read", "odoo.read"],

    # Generic CRUD tools (Admin only - requires odoo.write for most operations)
    "search_records": ["odoo.read"],
    "get_record": ["odoo.read"],
    "create_record": ["odoo.write"],
    "update_record": ["odoo.write"],
    "delete_record": ["odoo.write"],
    "count_records": ["odoo.read"],
    "list_models": ["odoo.read"],
}

# =============================================================================
# Rate Limiting Configuration
# =============================================================================

RATE_LIMITS = {
    "read_operations_per_minute": 30,
    "write_operations_per_hour": 10,
    "document_uploads_per_day": 5,
}

# Tools classified by operation type for rate limiting
WRITE_TOOLS = [
    "request_leave",
    "cancel_leave_request",
    "upload_identity_document",
    "update_my_contact",
    "create_record",
    "update_record",
    "delete_record",
]

UPLOAD_TOOLS = [
    "upload_identity_document",
]


def check_scope_access(required_scopes: list[str], granted_scopes: list[str]) -> bool:
    """
    Check if any of the required scopes are in the granted scopes.

    Args:
        required_scopes: List of scopes that would grant access (any one is sufficient)
        granted_scopes: List of scopes the user has

    Returns:
        True if user has at least one required scope
    """
    return any(scope in granted_scopes for scope in required_scopes)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Odoo connection
    odoo_url: str = "https://erp.internal.keboola.com"
    odoo_db: str = "keboola-community"
    odoo_api_key: str | None = None
    odoo_username: str | None = None
    odoo_password: str | None = None

    # OAuth 2.1 Configuration (Google OAuth)
    # Provider: "google" or "custom"
    oauth_provider: str = "google"

    # Google OAuth settings (default)
    oauth_client_id: str | None = None  # Google Client ID
    oauth_client_secret: str | None = None  # Google Client Secret

    # Google OAuth endpoints (defaults for Google)
    oauth_authorization_server: str = "https://accounts.google.com"
    oauth_authorization_endpoint: str = "https://accounts.google.com/o/oauth2/v2/auth"
    oauth_token_endpoint: str = "https://oauth2.googleapis.com/token"
    oauth_jwks_uri: str = "https://www.googleapis.com/oauth2/v3/certs"
    oauth_issuer: str = "https://accounts.google.com"

    # Resource Server settings
    oauth_resource_identifier: str = "https://odoo-mcp.keboola.com"
    oauth_redirect_uri: str | None = None  # Set by deployment URL

    # OAuth scopes requested
    oauth_scopes: str = "openid email profile"

    # Token Storage (Feedback 4.1)
    # Options: "memory" (default), "redis", "encrypted_file"
    token_storage_backend: str = "memory"
    token_encryption_key: str | None = None  # For encrypted storage

    # HTTP Server
    http_host: str = "0.0.0.0"
    http_port: int = 8080

    # Development
    debug: bool = False
    oauth_dev_mode: bool = False  # Skip OAuth validation in dev
    yolo_mode: str | None = None  # "read" for read-only, "true" for full access

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
    }

    @property
    def effective_issuer(self) -> str:
        """Return effective OAuth issuer."""
        return self.oauth_issuer or self.oauth_authorization_server

    @property
    def is_google_oauth(self) -> bool:
        """Check if using Google OAuth."""
        return self.oauth_provider.lower() == "google"
