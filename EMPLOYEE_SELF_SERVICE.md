# Employee Self-Service MCP Server

## Overview

This document focuses the MCP server on **employee self-service** scenarios - the primary use case where employees use Claude or Slack to access their own HR information in Odoo.

## Key Employee Scenarios

Based on research, these are the most common employee self-service queries:

| Category | Example Questions |
|----------|-------------------|
| **Organization** | "Who is my manager?", "What department am I in?", "Who is in my team?" |
| **Time Off** | "How many vacation days do I have left?", "What's my sick leave balance?", "Show my pending leave requests" |
| **Documents** | "Show my documents", "What document folders do I have?", "Upload my passport" |
| **Directory** | "What's John's email?", "Who works in Engineering?" |

## Odoo 18 HR Models Reference

### Core Employee Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `hr.employee` | Employee records | `name`, `work_email`, `mobile_phone`, `department_id`, `parent_id` (manager), `coach_id`, `job_id`, `user_id`, `x_preferred_name`, `x_division` |
| `hr.employee.public` | Public employee info (limited fields) | Subset of hr.employee for security |
| `hr.department` | Departments | `name`, `manager_id`, `parent_id`, `member_ids` |
| `hr.job` | Job positions | `name`, `department_id`, `description` |

### Custom Fields (hr_employee_custom_fields module)

| Field | Purpose | Synced From |
|-------|---------|-------------|
| `x_preferred_name` | Employee's preferred name | BambooHR |
| `x_division` | Business division | BambooHR |

### Time Off Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `hr.leave` | Leave requests | `employee_id`, `holiday_status_id`, `date_from`, `date_to`, `number_of_days`, `state` |
| `hr.leave.type` | Leave types (Vacation, Sick, etc.) | `name`, `allocation_type`, `max_leaves` |
| `hr.leave.allocation` | Leave allocations | `employee_id`, `holiday_status_id`, `number_of_days`, `leaves_taken` |

### Document Management (OCA DMS)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `dms.directory` | Document folders | `name`, `parent_id`, `is_root_directory`, `group_ids` |
| `dms.file` | Document files | `name`, `directory_id`, `content`, `mimetype`, `size`, `create_date` |

**DMS Folder Structure per Employee:**
```
Employee Name (root)
├── Contracts
├── Identity (employees can upload)
├── Background Checks (RESTRICTED - hidden from employees)
└── Offboarding Documents (RESTRICTED - hidden from employees)
```

---

## Architecture Approaches

### Approach 1: User-Context MCP (Recommended)

**How it works**: The OAuth token identifies the user, and the MCP server automatically filters all queries to that user's data.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Employee (via Claude/Slack)                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OAuth 2.1 Authentication                      │
│                (User identified by access token)                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Server (Employee Mode)                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  User Context Injection:                                │    │
│  │  - Extract user_id from OAuth token                     │    │
│  │  - Find employee_id for user                            │    │
│  │  - Auto-filter all queries to user's own data           │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Odoo 18 ERP                              │
│              (Returns only user's own records)                   │
└─────────────────────────────────────────────────────────────────┘
```

**Pros**:
- Most secure - users can only see their own data
- Simple for end users - no need to specify "my" in queries
- Follows principle of least privilege

**Cons**:
- Each user needs Odoo user account linked to employee
- Manager views require additional logic

### Approach 2: Role-Based Access with Configurable Scopes

**How it works**: OAuth scopes define what data categories the user can access.

```json
{
  "scopes": {
    "employee.self": "Read own employee profile",
    "employee.team": "Read team members (for managers)",
    "leave.self": "Read/write own leave requests",
    "leave.team": "Approve team leave requests",
    "documents.self": "Read/upload own HR documents",
    "directory.read": "Read employee directory (limited fields)"
  }
}
```

**Pros**:
- Fine-grained control
- Can support manager scenarios
- Configurable per user/role

**Cons**:
- More complex to implement
- Requires scope management in auth server

### Approach 3: Service Account with User Impersonation

**How it works**: MCP server uses a service account, but queries on behalf of the authenticated user.

```
User Token → MCP Server → Extract user email →
Find Odoo employee → Query as that employee's context
```

**Pros**:
- Single Odoo API key for MCP server
- Users don't need individual Odoo credentials
- Can map Slack/Google users to Odoo employees

**Cons**:
- Service account has elevated permissions
- Must carefully enforce row-level security

---

## Recommended: Approach 1 with Employee Tools

### Tool Design for Employee Self-Service

```python
# Employee-focused tools (not generic CRUD)

EMPLOYEE_TOOLS = [
    # Profile & Organization
    Tool(
        name="get_my_profile",
        description="Get your employee profile information",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="get_my_manager",
        description="Get information about your manager",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="get_my_team",
        description="Get list of people in your team/department",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="find_colleague",
        description="Find a colleague by name and get their contact info",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to search for"}
            },
            "required": ["name"]
        }
    ),

    # Time Off / Leave
    Tool(
        name="get_my_leave_balance",
        description="Get your remaining leave balance for all leave types",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="get_my_leave_requests",
        description="Get your leave requests (pending, approved, rejected)",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["all", "pending", "approved", "rejected"],
                    "default": "all"
                }
            }
        }
    ),
    Tool(
        name="request_leave",
        description="Submit a new leave request",
        inputSchema={
            "type": "object",
            "properties": {
                "leave_type": {"type": "string", "description": "Type of leave (e.g., 'Vacation', 'Sick Leave')"},
                "start_date": {"type": "string", "format": "date", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "format": "date", "description": "End date (YYYY-MM-DD)"},
                "reason": {"type": "string", "description": "Reason for leave"}
            },
            "required": ["leave_type", "start_date", "end_date"]
        }
    ),

    # Documents (DMS)
    Tool(
        name="get_my_documents",
        description="Get your personal HR documents (contracts, identity docs)",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["all", "Contracts", "Identity"],
                    "default": "all"
                }
            }
        }
    ),
    Tool(
        name="get_document_categories",
        description="Get list of your available document folders",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="upload_identity_document",
        description="Upload an identity document to your personal folder",
        inputSchema={
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content_base64": {"type": "string"},
                "document_type": {
                    "type": "string",
                    "enum": ["passport", "id_card", "driving_license", "other"]
                }
            },
            "required": ["filename", "content_base64", "document_type"]
        }
    ),
    Tool(
        name="download_document",
        description="Download a document from your personal folder",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer"}
            },
            "required": ["document_id"]
        }
    ),

]
```

---

## Configuration File

### `config/employee_mcp_config.json`

```json
{
  "mode": "employee_self_service",
  "version": "1.1",

  "features": {
    "profile": {
      "enabled": true,
      "fields": ["name", "work_email", "mobile_phone", "department_id", "job_id", "parent_id", "coach_id", "x_preferred_name", "x_division"]
    },
    "directory": {
      "enabled": true,
      "searchable_fields": ["name", "work_email", "department_id"],
      "visible_fields": ["name", "work_email", "mobile_phone", "department_id", "job_title", "x_preferred_name"]
    },
    "leave": {
      "enabled": true,
      "allow_requests": true,
      "allow_cancellation": true,
      "visible_leave_types": ["all"]
    },
    "documents": {
      "enabled": true,
      "dms_integration": true,
      "allowed_folders": ["Contracts", "Identity"],
      "restricted_folders": ["Background Checks", "Offboarding Documents"],
      "upload_allowed": ["Identity"]
    }
  },

  "security": {
    "user_context_required": true,
    "manager_features": false,
    "admin_features": false,
    "rate_limit": {
      "requests_per_minute": 30,
      "write_operations_per_hour": 10,
      "document_uploads_per_day": 5
    }
  },

  "odoo": {
    "url": "https://erp.internal.keboola.com",
    "database": "keboola-community",
    "user_mapping": "oauth_email_to_work_email"
  }
}
```

---

## User-to-Employee Mapping

### How users are identified

```python
async def get_employee_for_user(oauth_claims: dict, odoo_client: OdooClient) -> int:
    """
    Map OAuth user to Odoo employee.

    Strategies:
    1. Match by email (work_email in hr.employee)
    2. Match by linked res.users record
    3. Match by custom field (e.g., slack_user_id)
    """

    user_email = oauth_claims.get("email")

    # Strategy 1: Match by work email
    employees = await odoo_client.search_read(
        model="hr.employee",
        domain=[["work_email", "=", user_email]],
        fields=["id", "name"],
        limit=1
    )

    if employees:
        return employees[0]["id"]

    # Strategy 2: Match via res.users
    users = await odoo_client.search_read(
        model="res.users",
        domain=[["login", "=", user_email]],
        fields=["id", "employee_id"],
        limit=1
    )

    if users and users[0].get("employee_id"):
        return users[0]["employee_id"][0]

    raise EmployeeNotFoundError(f"No employee found for {user_email}")
```

---

## Test Scenarios for Employee Self-Service

### `tests/e2e/test_employee_scenarios.py`

```python
"""
Employee Self-Service Test Scenarios

Tests real-world employee queries through the MCP server.
"""
import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.employee]


class TestProfileQueries:
    """Tests for employee profile queries."""

    async def test_get_my_profile(self, authenticated_employee_client):
        """
        Scenario: Employee asks "What's my profile?"
        Expected: Returns their name, email, department, manager, and custom fields
        """
        result = await authenticated_employee_client.call_tool(
            "get_my_profile",
            arguments={}
        )

        profile = json.loads(result.content[0].text)

        assert "name" in profile
        assert "work_email" in profile
        assert "department" in profile
        assert "manager" in profile
        # Custom fields from hr_employee_custom_fields
        assert "preferred_name" in profile  # x_preferred_name
        assert "division" in profile  # x_division

    async def test_get_my_manager(self, authenticated_employee_client):
        """
        Scenario: Employee asks "Who is my manager?"
        Expected: Returns manager's name and contact info
        """
        result = await authenticated_employee_client.call_tool(
            "get_my_manager",
            arguments={}
        )

        manager = json.loads(result.content[0].text)

        assert "name" in manager
        assert "email" in manager

    async def test_get_my_team(self, authenticated_employee_client):
        """
        Scenario: Employee asks "Who's in my team?"
        Expected: Returns list of team members in same department
        """
        result = await authenticated_employee_client.call_tool(
            "get_my_team",
            arguments={}
        )

        team = json.loads(result.content[0].text)

        assert isinstance(team, list)
        for member in team:
            assert "name" in member


class TestLeaveQueries:
    """Tests for leave/time-off queries."""

    async def test_get_leave_balance(self, authenticated_employee_client):
        """
        Scenario: Employee asks "How many vacation days do I have?"
        Expected: Returns balance for each leave type
        """
        result = await authenticated_employee_client.call_tool(
            "get_my_leave_balance",
            arguments={}
        )

        balances = json.loads(result.content[0].text)

        assert isinstance(balances, list)
        for balance in balances:
            assert "leave_type" in balance
            assert "allocated" in balance
            assert "taken" in balance
            assert "remaining" in balance

    async def test_request_leave(self, authenticated_employee_client):
        """
        Scenario: Employee says "I want to take vacation next Monday"
        Expected: Creates leave request, returns confirmation
        """
        result = await authenticated_employee_client.call_tool(
            "request_leave",
            arguments={
                "leave_type": "Paid Time Off",
                "start_date": "2025-02-10",
                "end_date": "2025-02-10",
                "reason": "Personal day"
            }
        )

        response = json.loads(result.content[0].text)

        assert "request_id" in response
        assert response["status"] == "submitted"

        # Cleanup: Cancel the test request
        await authenticated_employee_client.call_tool(
            "cancel_leave_request",
            arguments={"request_id": response["request_id"]}
        )

    async def test_get_pending_requests(self, authenticated_employee_client):
        """
        Scenario: Employee asks "What leave requests are pending?"
        Expected: Returns list of pending requests
        """
        result = await authenticated_employee_client.call_tool(
            "get_my_leave_requests",
            arguments={"status": "pending"}
        )

        requests = json.loads(result.content[0].text)

        assert isinstance(requests, list)


class TestDocumentQueries:
    """Tests for DMS document queries."""

    async def test_get_my_documents(self, authenticated_employee_client):
        """
        Scenario: Employee asks "Show my documents"
        Expected: Returns list of documents from allowed folders
        """
        result = await authenticated_employee_client.call_tool(
            "get_my_documents",
            arguments={}
        )

        response = json.loads(result.content[0].text)

        assert "documents" in response
        assert isinstance(response["documents"], list)

    async def test_get_document_categories(self, authenticated_employee_client):
        """
        Scenario: Employee asks "What document folders do I have?"
        Expected: Returns accessible categories (not restricted ones)
        """
        result = await authenticated_employee_client.call_tool(
            "get_document_categories",
            arguments={}
        )

        response = json.loads(result.content[0].text)

        assert "categories" in response
        # Restricted folders should NOT appear
        for cat in response["categories"]:
            assert cat["name"] not in ["Background Checks", "Offboarding Documents"]


class TestDirectoryQueries:
    """Tests for employee directory queries."""

    async def test_find_colleague_by_name(self, authenticated_employee_client):
        """
        Scenario: Employee asks "What's John's email?"
        Expected: Returns matching colleagues with contact info
        """
        result = await authenticated_employee_client.call_tool(
            "find_colleague",
            arguments={"name": "John"}
        )

        colleagues = json.loads(result.content[0].text)

        assert isinstance(colleagues, list)
        for colleague in colleagues:
            assert "name" in colleague
            assert "work_email" in colleague

    async def test_cannot_see_sensitive_data(self, authenticated_employee_client):
        """
        Security: Employee should not see sensitive fields of others
        Expected: Salary, bank info, personal phone not returned
        """
        result = await authenticated_employee_client.call_tool(
            "find_colleague",
            arguments={"name": "Admin"}
        )

        colleagues = json.loads(result.content[0].text)

        if colleagues:
            colleague = colleagues[0]
            assert "bank_account_id" not in colleague
            assert "private_phone" not in colleague
            # Salary info should never be exposed
```

---

## Security Considerations

### 1. Data Isolation
```python
# All queries automatically filtered to user's own data
async def get_my_leave_balance(employee_id: int, client: OdooClient):
    # employee_id comes from OAuth token, NOT from user input
    return await client.search_read(
        model="hr.leave.allocation",
        domain=[["employee_id", "=", employee_id]],  # Auto-filtered
        fields=["holiday_status_id", "number_of_days", "leaves_taken"]
    )
```

### 2. Field-Level Security
```python
# Public vs Private fields
PUBLIC_EMPLOYEE_FIELDS = [
    "name", "work_email", "mobile_phone", "department_id",
    "job_id", "parent_id", "coach_id", "image_128"
]

PRIVATE_EMPLOYEE_FIELDS = [
    "private_phone", "private_email", "bank_account_id",
    "identification_id", "passport_id", "emergency_contact"
]

# Only return public fields when viewing other employees
```

### 3. Rate Limiting
```python
# Prevent abuse
RATE_LIMITS = {
    "read_operations": 30,      # per minute
    "write_operations": 10,     # per hour (leave requests, etc.)
    "document_uploads": 5,      # per day
}
```

### 4. Audit Logging
```python
# Log all operations for compliance
async def log_operation(
    employee_id: int,
    operation: str,
    model: str,
    record_ids: list[int],
    success: bool
):
    await audit_client.log({
        "timestamp": datetime.utcnow().isoformat(),
        "employee_id": employee_id,
        "operation": operation,
        "model": model,
        "record_ids": record_ids,
        "success": success
    })
```

---

## Alternative Approaches Considered

### 1. Full CRUD Access (Rejected)
- **Why not**: Too risky, users could access others' data
- **When appropriate**: Admin tools, not self-service

### 2. Odoo Portal Integration
- **What**: Use Odoo's built-in portal instead of custom MCP
- **Why not chosen**: Less conversational, Claude/Slack UX preferred
- **Could combine**: MCP could link to portal for complex actions

### 3. Slack-First Bot (Without MCP)
- **What**: Direct Slack bot → Odoo integration
- **Why not chosen**: MCP provides Claude Desktop + Slack + future clients
- **Could combine**: MCP server can power both Claude and Slack

### 4. Read-Only MCP + Portal for Actions
- **What**: MCP only reads data, links to portal for actions
- **Pros**: Lower risk, familiar Odoo UI for actions
- **Cons**: Breaks conversational flow

---

## Recommended Implementation Order

1. **Phase 1**: Profile & Directory (read-only)
   - `get_my_profile` (with custom fields: x_preferred_name, x_division)
   - `get_my_manager`
   - `get_my_team`
   - `find_colleague`

2. **Phase 2**: Leave Management
   - `get_my_leave_balance`
   - `get_my_leave_requests`
   - `request_leave`
   - `cancel_leave_request`

3. **Phase 3**: Documents (DMS Integration)
   - `get_my_documents`
   - `get_document_categories`
   - `upload_identity_document`
   - `download_document`

---

## Sources

- [Odoo 18 Employees Documentation](https://www.odoo.com/documentation/18.0/applications/hr/employees.html)
- [Odoo 18 Attendances Documentation](https://www.odoo.com/documentation/18.0/applications/hr/attendances.html)
- [Odoo 18 Time Off/Leave Management](https://www.technaureus.com/blog-detail/leave-management-in-odoo18)
- [Odoo Employee Self-Service Portal](https://apps.odoo.com/apps/modules/18.0/odoo_ess_portal)
- [Leave Balance in Odoo](https://www.cybrosys.com/blog/how-to-manage-leave-allocation-and-accrual-plans-in-odoo-18-time-off)
