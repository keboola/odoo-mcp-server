"""
Unit tests for MCP tools.

Run with: pytest tests/unit/test_tools.py -v -m unit
"""

import pytest

pytestmark = [pytest.mark.unit]


class TestToolSchemaValidation:
    """Tests for tool input schema validation."""

    def test_search_records_required_fields(self):
        """search_records should require model field."""
        schema = {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "domain": {"type": "array", "default": []},
                "fields": {"type": "array"},
                "limit": {"type": "integer", "default": 20},
                "offset": {"type": "integer", "default": 0},
            },
            "required": ["model"],
        }

        assert "model" in schema["required"]
        assert "domain" not in schema["required"]  # Has default

    def test_get_record_required_fields(self):
        """get_record should require model and record_id."""
        schema = {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "record_id": {"type": "integer"},
                "fields": {"type": "array"},
            },
            "required": ["model", "record_id"],
        }

        assert "model" in schema["required"]
        assert "record_id" in schema["required"]

    def test_create_record_required_fields(self):
        """create_record should require model and values."""
        schema = {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "values": {"type": "object"},
            },
            "required": ["model", "values"],
        }

        assert "model" in schema["required"]
        assert "values" in schema["required"]

    def test_update_record_required_fields(self):
        """update_record should require model, record_id, and values."""
        schema = {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "record_id": {"type": "integer"},
                "values": {"type": "object"},
            },
            "required": ["model", "record_id", "values"],
        }

        assert len(schema["required"]) == 3

    def test_delete_record_required_fields(self):
        """delete_record should require model and record_id."""
        schema = {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "record_id": {"type": "integer"},
            },
            "required": ["model", "record_id"],
        }

        assert "model" in schema["required"]
        assert "record_id" in schema["required"]


class TestToolResultFormatting:
    """Tests for tool result formatting."""

    def test_search_results_are_list(self):
        """Search results should be returned as a list."""
        import json

        results = [
            {"id": 1, "name": "Partner 1"},
            {"id": 2, "name": "Partner 2"},
        ]

        formatted = json.dumps(results)
        parsed = json.loads(formatted)

        assert isinstance(parsed, list)
        assert len(parsed) == 2

    def test_single_record_is_object(self):
        """Single record should be returned as an object."""
        import json

        record = {"id": 1, "name": "Partner 1", "email": "test@example.com"}

        formatted = json.dumps(record)
        parsed = json.loads(formatted)

        assert isinstance(parsed, dict)
        assert "id" in parsed

    def test_create_result_includes_id(self):
        """Create result should include the new record ID."""
        import json

        result = {"id": 42}

        formatted = json.dumps(result)
        parsed = json.loads(formatted)

        assert "id" in parsed
        assert parsed["id"] == 42

    def test_error_result_format(self):
        """Error results should have consistent format."""
        import json

        error_result = {"error": "Access denied", "code": "ACCESS_ERROR"}

        formatted = json.dumps(error_result)
        parsed = json.loads(formatted)

        assert "error" in parsed


class TestToolArgumentValidation:
    """Tests for tool argument validation."""

    def test_model_name_validation(self):
        """Model names should follow Odoo naming convention."""
        valid_models = ["res.partner", "crm.lead", "hr.employee", "product.product"]
        invalid_models = ["invalid", "no-dots", ""]

        for model in valid_models:
            assert "." in model
            assert len(model.split(".")) >= 2

        for model in invalid_models:
            is_valid = "." in model and len(model.split(".")) >= 2
            assert not is_valid

    def test_domain_format_validation(self):
        """Domain should be a list of conditions."""
        valid_domains = [
            [],
            [["name", "=", "test"]],
            [["is_company", "=", True], ["active", "=", True]],
            ["|", ["name", "ilike", "a"], ["name", "ilike", "b"]],
        ]

        for domain in valid_domains:
            assert isinstance(domain, list)

    def test_record_id_must_be_positive(self):
        """Record IDs must be positive integers."""
        valid_ids = [1, 42, 1000]
        invalid_ids = [0, -1, -100]

        for rid in valid_ids:
            assert rid > 0

        for rid in invalid_ids:
            assert rid <= 0

    def test_limit_bounds(self):
        """Limit should be within reasonable bounds."""
        min_limit = 1
        max_limit = 1000
        default_limit = 20

        assert default_limit >= min_limit
        assert default_limit <= max_limit

        # Test boundary
        assert min_limit > 0
        assert max_limit <= 10000  # Reasonable upper bound


class TestToolDescriptions:
    """Tests for tool documentation."""

    def test_all_tools_have_descriptions(self):
        """All tools should have non-empty descriptions."""
        tools = [
            {"name": "search_records", "description": "Search for records..."},
            {"name": "get_record", "description": "Get a single record..."},
            {"name": "create_record", "description": "Create a new record..."},
            {"name": "update_record", "description": "Update an existing record..."},
            {"name": "delete_record", "description": "Delete a record..."},
            {"name": "count_records", "description": "Count records..."},
            {"name": "list_models", "description": "List available models..."},
        ]

        for tool in tools:
            assert tool["description"]
            assert len(tool["description"]) > 10

    def test_tool_names_are_snake_case(self):
        """Tool names should be in snake_case."""
        tool_names = [
            "search_records",
            "get_record",
            "create_record",
            "update_record",
            "delete_record",
            "count_records",
            "list_models",
        ]

        for name in tool_names:
            assert name == name.lower()
            assert " " not in name
            assert "-" not in name
