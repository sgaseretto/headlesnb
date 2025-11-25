"""MCP Server implementation for headless notebook management"""

import asyncio
import logging
from typing import Any, Dict, Optional
from pathlib import Path

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP library not installed. Install with: pip install mcp")
    raise

from .manager import NotebookManager
from .tools import get_all_tool_schemas

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("headlesnb-mcp")


class HeadlesNBMCPServer:
    """MCP Server for headless notebook management"""

    def __init__(self, root_path: str = "."):
        """
        Initialize the MCP server

        Args:
            root_path: Root path for notebook operations
        """
        self.manager = NotebookManager(root_path=root_path)
        self.server = Server("headlesnb")
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP server handlers"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools"""
            tools = []
            for schema in get_all_tool_schemas():
                tools.append(Tool(
                    name=schema["name"],
                    description=schema["description"],
                    inputSchema=schema["inputSchema"]
                ))
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent | ImageContent | EmbeddedResource]:
            """Handle tool calls"""
            logger.info(f"Tool called: {name} with arguments: {arguments}")

            try:
                # Server management tools
                if name == "list_files":
                    result = self.manager.list_files(
                        path=arguments.get("path", ""),
                        max_depth=arguments.get("max_depth", 1),
                        start_index=arguments.get("start_index", 0),
                        limit=arguments.get("limit", 25),
                        pattern=arguments.get("pattern", "")
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "list_kernels":
                    result = self.manager.list_kernels()
                    return [TextContent(type="text", text=result)]

                # Multi-notebook management tools
                elif name == "use_notebook":
                    result = self.manager.use_notebook(
                        notebook_name=arguments["notebook_name"],
                        notebook_path=arguments["notebook_path"],
                        mode=arguments.get("mode", "connect"),
                        kernel_id=arguments.get("kernel_id")
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "list_notebooks":
                    result = self.manager.list_notebooks()
                    return [TextContent(type="text", text=result)]

                elif name == "restart_notebook":
                    result = self.manager.restart_notebook(
                        notebook_name=arguments["notebook_name"]
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "unuse_notebook":
                    result = self.manager.unuse_notebook(
                        notebook_name=arguments["notebook_name"]
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "read_notebook":
                    result = self.manager.read_notebook(
                        notebook_name=arguments["notebook_name"],
                        response_format=arguments.get("response_format", "brief"),
                        start_index=arguments.get("start_index", 0),
                        limit=arguments.get("limit", 20)
                    )
                    return [TextContent(type="text", text=result)]

                # Cell tools
                elif name == "insert_cell":
                    result = self.manager.insert_cell(
                        cell_index=arguments["cell_index"],
                        cell_type=arguments["cell_type"],
                        cell_source=arguments["cell_source"]
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "overwrite_cell_source":
                    result = self.manager.overwrite_cell_source(
                        cell_index=arguments["cell_index"],
                        cell_source=arguments["cell_source"]
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "execute_cell":
                    outputs = self.manager.execute_cell(
                        cell_index=arguments["cell_index"],
                        timeout=arguments.get("timeout", 90),
                        stream=arguments.get("stream", False),
                        progress_interval=arguments.get("progress_interval", 5)
                    )
                    return self._format_tool_outputs(outputs)

                elif name == "insert_execute_code_cell":
                    outputs = self.manager.insert_execute_code_cell(
                        cell_index=arguments["cell_index"],
                        cell_source=arguments["cell_source"],
                        timeout=arguments.get("timeout", 90)
                    )
                    return self._format_tool_outputs(outputs)

                elif name == "read_cell":
                    outputs = self.manager.read_cell(
                        cell_index=arguments["cell_index"],
                        include_outputs=arguments.get("include_outputs", True)
                    )
                    return self._format_tool_outputs(outputs)

                elif name == "delete_cell":
                    result = self.manager.delete_cell(
                        cell_indices=arguments["cell_indices"],
                        include_source=arguments.get("include_source", True)
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "execute_code":
                    outputs = self.manager.execute_code(
                        code=arguments["code"],
                        timeout=arguments.get("timeout", 30)
                    )
                    return self._format_tool_outputs(outputs)

                # Additional tools
                elif name == "stop_execution":
                    result = self.manager.stop_execution()
                    return [TextContent(type="text", text=result)]

                elif name == "set_active_notebook":
                    result = self.manager.set_active_notebook(
                        notebook_name=arguments["notebook_name"]
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "move_cell":
                    result = self.manager.move_cell(
                        from_index=arguments["from_index"],
                        to_index=arguments["to_index"]
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "swap_cells":
                    result = self.manager.swap_cells(
                        index1=arguments["index1"],
                        index2=arguments["index2"]
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "reorder_cells":
                    result = self.manager.reorder_cells(
                        new_order=arguments["new_order"]
                    )
                    return [TextContent(type="text", text=result)]

                # History tools
                elif name == "undo":
                    result = self.manager.undo(
                        steps=arguments.get("steps", 1)
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "redo":
                    result = self.manager.redo(
                        steps=arguments.get("steps", 1)
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "get_history":
                    result = self.manager.get_history()
                    return [TextContent(type="text", text=result)]

                elif name == "clear_history":
                    result = self.manager.clear_history()
                    return [TextContent(type="text", text=result)]

                else:
                    error_msg = f"Unknown tool: {name}"
                    logger.error(error_msg)
                    return [TextContent(type="text", text=error_msg)]

            except Exception as e:
                error_msg = f"Error executing {name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]

    def _format_tool_outputs(self, outputs: list) -> list[TextContent | ImageContent]:
        """Format tool outputs for MCP response"""
        result = []

        for output in outputs:
            if isinstance(output, str):
                result.append(TextContent(type="text", text=output))
            elif isinstance(output, dict):
                if output.get('type') == 'image':
                    result.append(ImageContent(
                        type="image",
                        data=output['data'],
                        mimeType=f"image/{output['format']}"
                    ))
                elif output.get('type') == 'html':
                    # For now, convert HTML to text
                    result.append(TextContent(type="text", text=output['content']))
                else:
                    result.append(TextContent(type="text", text=str(output)))

        return result if result else [TextContent(type="text", text="(no output)")]

    async def run(self):
        """Run the MCP server"""
        logger.info("Starting HeadlesNB MCP Server...")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main(root_path: Optional[str] = None):
    """Main entry point for the MCP server"""
    if root_path is None:
        root_path = Path.cwd()

    server = HeadlesNBMCPServer(root_path=str(root_path))
    await server.run()


def cli():
    """CLI entry point"""
    import sys

    root_path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(root_path))


if __name__ == "__main__":
    cli()
