"""
OAuth User to Odoo Employee Mapping

Maps authenticated OAuth users to their Odoo employee records.
Uses multiple strategies to find the correct employee.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EmployeeNotFoundError(Exception):
    """Raised when no employee record matches the OAuth user."""
    pass


class MultipleEmployeesFoundError(Exception):
    """Raised when multiple employee records match the OAuth user."""
    pass


async def get_employee_for_user(
    oauth_claims: dict[str, Any],
    odoo_client: Any,
) -> dict[str, Any]:
    """
    Map OAuth user to Odoo employee.

    Tries multiple strategies in order:
    1. Match by work_email in hr.employee
    2. Match via res.users login (which links to hr.employee)
    3. Match by odoo_employee_id claim (if present in token)

    Args:
        oauth_claims: Decoded JWT claims from OAuth token
        odoo_client: Odoo client instance

    Returns:
        Dict with employee info: {id, name, email, department_id}

    Raises:
        EmployeeNotFoundError: If no employee matches
    """
    user_email = oauth_claims.get("email") or oauth_claims.get("sub")
    odoo_employee_id = oauth_claims.get("odoo_employee_id")

    logger.info(f"Mapping OAuth user to employee: email={user_email}")

    # Strategy 0: If token contains employee ID directly (trusted claim)
    if odoo_employee_id:
        employees = await odoo_client.search_read(
            model="hr.employee",
            domain=[["id", "=", odoo_employee_id]],
            fields=["id", "name", "work_email", "department_id"],
            limit=1,
        )
        if employees:
            logger.info(f"Found employee by token claim: {employees[0]['name']}")
            return _normalize_employee(employees[0])

    if not user_email:
        raise EmployeeNotFoundError("No email in OAuth token to map to employee")

    # Strategy 1: Match by work_email in hr.employee
    employees = await odoo_client.search_read(
        model="hr.employee",
        domain=[["work_email", "=ilike", user_email]],
        fields=["id", "name", "work_email", "department_id"],
        limit=2,  # Get 2 to detect duplicates
    )

    if len(employees) > 1:
        logger.warning(f"Multiple employees found for email {user_email}")
        # Use first one but log warning
        return _normalize_employee(employees[0])

    if employees:
        logger.info(f"Found employee by work_email: {employees[0]['name']}")
        return _normalize_employee(employees[0])

    # Strategy 2: Match via res.users (login -> employee_id)
    users = await odoo_client.search_read(
        model="res.users",
        domain=[["login", "=ilike", user_email]],
        fields=["id", "employee_id", "employee_ids"],
        limit=1,
    )

    if users:
        user = users[0]
        # Check employee_id (single linked employee)
        if user.get("employee_id"):
            emp_id = user["employee_id"][0]
            employees = await odoo_client.read(
                model="hr.employee",
                ids=[emp_id],
                fields=["id", "name", "work_email", "department_id"],
            )
            if employees:
                logger.info(f"Found employee via res.users: {employees[0]['name']}")
                return _normalize_employee(employees[0])

        # Check employee_ids (multiple linked employees - rare)
        if user.get("employee_ids") and len(user["employee_ids"]) > 0:
            emp_id = user["employee_ids"][0]
            employees = await odoo_client.read(
                model="hr.employee",
                ids=[emp_id],
                fields=["id", "name", "work_email", "department_id"],
            )
            if employees:
                logger.info(f"Found employee via res.users employee_ids: {employees[0]['name']}")
                return _normalize_employee(employees[0])

    # Strategy 3: Fuzzy match on name if email has name part (last resort)
    # e.g., "john.doe@company.com" -> search for "john doe"
    email_name = user_email.split("@")[0].replace(".", " ").replace("_", " ")
    if len(email_name) > 3:
        employees = await odoo_client.search_read(
            model="hr.employee",
            domain=[["name", "ilike", email_name]],
            fields=["id", "name", "work_email", "department_id"],
            limit=1,
        )
        if employees:
            logger.warning(
                f"Found employee by fuzzy name match: {employees[0]['name']} for {user_email}"
            )
            return _normalize_employee(employees[0])

    raise EmployeeNotFoundError(f"No employee found for email: {user_email}")


def _normalize_employee(employee: dict) -> dict:
    """Normalize employee record to standard format."""
    return {
        "id": employee["id"],
        "name": employee.get("name"),
        "email": employee.get("work_email"),
        "department_id": employee["department_id"][0] if employee.get("department_id") else None,
        "department_name": employee["department_id"][1] if employee.get("department_id") else None,
    }


async def validate_employee_access(
    employee_id: int,
    odoo_client: Any,
) -> bool:
    """
    Validate that an employee ID exists and is active.

    Args:
        employee_id: Employee ID to validate
        odoo_client: Odoo client instance

    Returns:
        True if employee exists and is active
    """
    employees = await odoo_client.search_read(
        model="hr.employee",
        domain=[["id", "=", employee_id], ["active", "=", True]],
        fields=["id"],
        limit=1,
    )
    return len(employees) > 0
