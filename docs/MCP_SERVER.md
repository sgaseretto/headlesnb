# MCP Server Documentation

HeadlesNB includes a Model Context Protocol (MCP) server that exposes all notebook management functionality through a standardized interface.

For overall system architecture and design philosophy, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Why MCP?

### The Problem

AI assistants like Claude need a way to interact with notebooks:
- Direct Python imports don't work across process boundaries
- Custom HTTP APIs require client implementation for each assistant
- No standard way for assistants to discover available capabilities

### Our Solution

MCP (Model Context Protocol) provides:
- **Standardized interface**: Any MCP-compatible assistant can use HeadlesNB
- **Tool discovery**: Assistants can list available tools and their schemas
- **Structured I/O**: Well-defined JSON schemas for inputs and outputs
- **No custom client needed**: Works with Claude Desktop, custom MCP clients, etc.

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| All tools return text | MCP results are displayed to users; text is readable |
| No authentication | MCP is for local assistant use; auth is handled externally |
| Async implementation | MCP protocol is async; matches server requirements |
| One manager instance | Shared state enables multi-tool workflows |

## Running the MCP Server

### Command Line

```bash
# Run with current directory as root
python -m headlesnb.mcp_server

# Run with specific root path
python -m headlesnb.mcp_server /path/to/notebooks
```

### Programmatically

```python
import asyncio
from headlesnb.mcp_server import HeadlesNBMCPServer

async def main():
    server = HeadlesNBMCPServer(root_path=".")
    await server.run()

asyncio.run(main())
```

## Available Tools

The MCP server exposes 16 tools organized into 3 categories:

### Server Management Tools (2 tools)

1. **list_files** - List files and directories
2. **list_kernels** - List available kernels

### Multi-Notebook Management Tools (6 tools)

3. **use_notebook** - Use and activate a notebook
4. **list_notebooks** - List all notebooks in use
5. **restart_notebook** - Restart a notebook's kernel
6. **unuse_notebook** - Disconnect from a notebook
7. **read_notebook** - Read notebook contents
8. **set_active_notebook** - Set active notebook

### Cell Tools (8 tools)

9. **insert_cell** - Insert a cell
10. **overwrite_cell_source** - Overwrite cell source
11. **execute_cell** - Execute a cell
12. **insert_execute_code_cell** - Insert and execute a cell
13. **read_cell** - Read a specific cell
14. **delete_cell** - Delete cells
15. **execute_code** - Execute code without saving
16. **stop_execution** - Stop current execution

## Tool Schemas

All tools follow the MCP protocol with well-defined schemas. See `headlesnb/tools.py` for complete schema definitions.

### Example Tool Call

```json
{
  "name": "use_notebook",
  "arguments": {
    "notebook_name": "my_analysis",
    "notebook_path": "notebooks/analysis.ipynb",
    "mode": "connect"
  }
}
```

## Integration with MCP Clients

The server can be integrated with any MCP-compatible client:

### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "headlesnb": {
      "command": "python",
      "args": ["-m", "headlesnb.mcp_server", "/path/to/notebooks"]
    }
  }
}
```

### Custom Client

```python
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

async def use_headlesnb():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "headlesnb.mcp_server", "."]
    )

    async with stdio_client(server_params) as (read, write):
        async with Client(read, write) as client:
            # List available tools
            tools = await client.list_tools()

            # Call a tool
            result = await client.call_tool(
                "use_notebook",
                {
                    "notebook_name": "test",
                    "notebook_path": "test.ipynb",
                    "mode": "create"
                }
            )
            print(result)
```

## Error Handling

The server returns errors as text content:

```python
{
  "type": "text",
  "text": "Error: Notebook 'xyz' not found"
}
```

## Logging

The server logs all operations:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Logs include:
- Tool calls with arguments
- Execution errors
- Server lifecycle events

## Security Considerations

1. **File System Access**: The server has access to files within the configured root path
2. **Code Execution**: Notebooks can execute arbitrary Python code
3. **Resource Limits**: Consider setting appropriate timeouts for cell execution
4. **Authentication**: The server doesn't include built-in authentication - use external mechanisms if needed

## Performance Tips

1. **Timeouts**: Set appropriate timeouts for long-running cells
2. **Multiple Notebooks**: Use multiple notebooks for parallel operations
3. **Kernel Restart**: Restart kernels periodically to free memory
4. **Pagination**: Use pagination when listing large numbers of files or cells

## Troubleshooting

### Server Won't Start

Check that all dependencies are installed:
```bash
pip install -e .
```

### Tool Execution Fails

Check the logs for detailed error messages:
```bash
python -m headlesnb.mcp_server 2>&1 | tee server.log
```

### Kernel Issues

Restart the kernel:
```python
await client.call_tool("restart_notebook", {"notebook_name": "my_notebook"})
```

## Examples

See `examples/` directory for usage examples that can be adapted for MCP client use.
