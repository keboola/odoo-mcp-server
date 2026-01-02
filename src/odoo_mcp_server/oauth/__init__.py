"""OAuth 2.1 Resource Server implementation."""

from .resource_server import OAuthResourceServer, OAuthMiddleware, extract_user_context
from .token_validator import TokenValidator
from .metadata import ProtectedResourceMetadata
from .user_mapping import get_employee_for_user, EmployeeNotFoundError

__all__ = [
    "OAuthResourceServer",
    "OAuthMiddleware",
    "TokenValidator",
    "ProtectedResourceMetadata",
    "extract_user_context",
    "get_employee_for_user",
    "EmployeeNotFoundError",
]
