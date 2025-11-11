"""Unit tests for tools module"""

import pytest
from headlesnb.tools import TOOL_SCHEMAS, get_all_tool_schemas


class TestToolSchemas:
    """Test cases for tool schemas"""

    def test_all_tools_present(self):
        """Test that all expected tools are present"""
        expected_tools = [
            "list_files",
            "list_kernels",
            "use_notebook",
            "list_notebooks",
            "restart_notebook",
            "unuse_notebook",
            "read_notebook",
            "insert_cell",
            "overwrite_cell_source",
            "execute_cell",
            "insert_execute_code_cell",
            "read_cell",
            "delete_cell",
            "execute_code",
            "stop_execution",
            "set_active_notebook"
        ]

        for tool in expected_tools:
            assert tool in TOOL_SCHEMAS, f"Tool '{tool}' not found in schemas"

    def test_get_all_tool_schemas(self):
        """Test getting all tool schemas as a list"""
        schemas = get_all_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) == len(TOOL_SCHEMAS)

    def test_tool_schema_structure(self):
        """Test that each tool schema has required fields"""
        for tool_name, schema in TOOL_SCHEMAS.items():
            assert "name" in schema, f"Tool '{tool_name}' missing 'name' field"
            assert "description" in schema, f"Tool '{tool_name}' missing 'description' field"
            assert "inputSchema" in schema, f"Tool '{tool_name}' missing 'inputSchema' field"

            # Check inputSchema structure
            input_schema = schema["inputSchema"]
            assert "type" in input_schema
            assert input_schema["type"] == "object"
            assert "properties" in input_schema

    def test_list_files_schema(self):
        """Test list_files schema"""
        schema = TOOL_SCHEMAS["list_files"]
        assert schema["name"] == "list_files"
        assert "file" in schema["description"].lower()

        props = schema["inputSchema"]["properties"]
        assert "path" in props
        assert "max_depth" in props
        assert "start_index" in props
        assert "limit" in props
        assert "pattern" in props

    def test_use_notebook_schema(self):
        """Test use_notebook schema"""
        schema = TOOL_SCHEMAS["use_notebook"]
        assert schema["name"] == "use_notebook"

        props = schema["inputSchema"]["properties"]
        assert "notebook_name" in props
        assert "notebook_path" in props
        assert "mode" in props

        # Check required fields
        required = schema["inputSchema"]["required"]
        assert "notebook_name" in required
        assert "notebook_path" in required

        # Check mode enum
        assert props["mode"]["enum"] == ["connect", "create"]

    def test_execute_cell_schema(self):
        """Test execute_cell schema"""
        schema = TOOL_SCHEMAS["execute_cell"]
        assert schema["name"] == "execute_cell"

        props = schema["inputSchema"]["properties"]
        assert "cell_index" in props
        assert "timeout" in props
        assert "stream" in props
        assert "progress_interval" in props

        # Check required fields
        required = schema["inputSchema"]["required"]
        assert "cell_index" in required

    def test_delete_cell_schema(self):
        """Test delete_cell schema"""
        schema = TOOL_SCHEMAS["delete_cell"]
        assert schema["name"] == "delete_cell"

        props = schema["inputSchema"]["properties"]
        assert "cell_indices" in props
        assert "include_source" in props

        # Check array type for cell_indices
        assert props["cell_indices"]["type"] == "array"
        assert props["cell_indices"]["items"]["type"] == "integer"

    def test_execute_code_schema(self):
        """Test execute_code schema"""
        schema = TOOL_SCHEMAS["execute_code"]
        assert schema["name"] == "execute_code"

        props = schema["inputSchema"]["properties"]
        assert "code" in props
        assert "timeout" in props

        # Check timeout constraints
        assert props["timeout"]["minimum"] == 1
        assert props["timeout"]["maximum"] == 60

    def test_read_notebook_schema(self):
        """Test read_notebook schema"""
        schema = TOOL_SCHEMAS["read_notebook"]
        assert schema["name"] == "read_notebook"

        props = schema["inputSchema"]["properties"]
        assert "notebook_name" in props
        assert "response_format" in props

        # Check format enum
        assert props["response_format"]["enum"] == ["brief", "detailed"]

    def test_insert_cell_schema(self):
        """Test insert_cell schema"""
        schema = TOOL_SCHEMAS["insert_cell"]
        assert schema["name"] == "insert_cell"

        props = schema["inputSchema"]["properties"]
        assert "cell_index" in props
        assert "cell_type" in props
        assert "cell_source" in props

        # Check cell_type enum
        assert props["cell_type"]["enum"] == ["code", "markdown"]

        # Check required fields
        required = schema["inputSchema"]["required"]
        assert "cell_index" in required
        assert "cell_type" in required
        assert "cell_source" in required
