"""MCP tools for Odoo operations."""

from .records import TOOLS as CRUD_TOOLS
from .records import execute_tool as execute_crud_tool
from .employee import EMPLOYEE_TOOLS
from .employee import execute_employee_tool

__all__ = [
    "CRUD_TOOLS",
    "EMPLOYEE_TOOLS",
    "execute_crud_tool",
    "execute_employee_tool",
    "register_tools",
    "register_employee_tools",
    "execute_tool",
]


def register_tools():
    """Return list of all available tools."""
    return CRUD_TOOLS + EMPLOYEE_TOOLS


def register_employee_tools():
    """Return list of employee self-service tools."""
    return EMPLOYEE_TOOLS


async def execute_tool(name: str, arguments: dict, odoo_client):
    """
    Execute a tool by name.

    Dispatches to the appropriate tool executor based on tool name.
    """
    # Check employee tools first
    employee_tool_names = [t.name for t in EMPLOYEE_TOOLS]
    if name in employee_tool_names:
        return await execute_employee_tool(name, arguments, odoo_client)

    # Fall back to CRUD tools
    crud_tool_names = [t.name for t in CRUD_TOOLS]
    if name in crud_tool_names:
        return await execute_crud_tool(name, arguments, odoo_client)

    raise ValueError(f"Unknown tool: {name}")
