"""
Odoo XML-RPC Client

Handles communication with Odoo ERP instance.
Includes async-safe operations and error handling.
"""
import asyncio
import xmlrpc.client
from functools import partial
from typing import Any
from xmlrpc.client import Fault

from .exceptions import (
    OdooAuthenticationError,
    map_connection_error,
    map_odoo_fault,
)


class OdooClient:
    """
    Async wrapper for Odoo XML-RPC API.

    Thread/task-safe: Uses asyncio.Lock for UID caching to prevent
    race conditions in concurrent async operations.

    Error Handling: All XML-RPC faults are mapped to typed exceptions
    for clean error responses in MCP tools.
    """

    def __init__(
        self,
        url: str,
        database: str | None = None,
        db: str | None = None,  # Alias for database
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.url = url.rstrip("/")
        self.db = database or db  # Support both parameter names
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

        # Async lock for thread-safe UID caching (Feedback 4.3)
        self._uid_lock = asyncio.Lock()

    async def _run_in_executor(self, func, *args) -> Any:
        """
        Run blocking XML-RPC call in executor.

        Wraps XML-RPC errors in typed exceptions.
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None, partial(func, *args)
            )
        except Fault as e:
            raise map_odoo_fault(e) from e
        except (TimeoutError, ConnectionError, OSError) as e:
            raise map_connection_error(e) from e

    async def get_version(self) -> dict:
        """Get Odoo server version"""
        return await self._run_in_executor(self._common.version)

    async def authenticate(self) -> int:
        """
        Authenticate and return user ID.

        Thread-safe: Uses async lock to prevent race conditions
        when multiple coroutines try to authenticate simultaneously.
        """
        # Fast path: already authenticated
        if self._uid:
            return self._uid

        # Acquire lock to prevent concurrent authentication attempts
        async with self._uid_lock:
            # Double-check after acquiring lock
            if self._uid:
                return self._uid

            if self.api_key:
                # API key authentication
                self._uid = await self._run_in_executor(
                    self._common.authenticate,
                    self.db, self.username or "admin", self.api_key, {}
                )
            else:
                self._uid = await self._run_in_executor(
                    self._common.authenticate,
                    self.db, self.username, self.password, {}
                )

            if not self._uid:
                raise OdooAuthenticationError(
                    "Authentication failed - check credentials",
                    username=self.username,
                )

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

        # Decide what to use as password/key
        password_or_key = self.api_key or self.password

        return await self._run_in_executor(
            self._models.execute_kw,
            self.db,
            uid,
            password_or_key,
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
