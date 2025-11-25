"""Tool definitions for MCP server"""

from typing import Any, Dict, List

# Tool schemas for MCP server
TOOL_SCHEMAS = {
    "list_files": {
        "name": "list_files",
        "description": "List all files and directories recursively in the file system",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Starting path to list from (empty string means root directory)",
                    "default": ""
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth to recurse into subdirectories (default: 1, max: 3)",
                    "default": 1,
                    "minimum": 0,
                    "maximum": 3
                },
                "start_index": {
                    "type": "integer",
                    "description": "Starting index for pagination (0-based, default: 0)",
                    "default": 0,
                    "minimum": 0
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of items to return (0 means no limit, default: 25)",
                    "default": 25,
                    "minimum": 0
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter file paths (default: \"\")",
                    "default": ""
                }
            }
        }
    },
    "list_kernels": {
        "name": "list_kernels",
        "description": "List all available kernels (managed notebooks)",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "use_notebook": {
        "name": "use_notebook",
        "description": "Use a notebook and activate it for following cell operations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "notebook_name": {
                    "type": "string",
                    "description": "Unique identifier for the notebook"
                },
                "notebook_path": {
                    "type": "string",
                    "description": "Path to the notebook file"
                },
                "mode": {
                    "type": "string",
                    "description": "Notebook operation mode: 'connect' or 'create'",
                    "enum": ["connect", "create"],
                    "default": "connect"
                },
                "kernel_id": {
                    "type": "string",
                    "description": "Specific kernel ID to use (optional)"
                }
            },
            "required": ["notebook_name", "notebook_path"]
        }
    },
    "list_notebooks": {
        "name": "list_notebooks",
        "description": "List all notebooks that have been used via use_notebook tool",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "restart_notebook": {
        "name": "restart_notebook",
        "description": "Restart the kernel for a specific notebook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "notebook_name": {
                    "type": "string",
                    "description": "Notebook identifier to restart"
                }
            },
            "required": ["notebook_name"]
        }
    },
    "unuse_notebook": {
        "name": "unuse_notebook",
        "description": "Disconnect from a specific notebook and release its resources",
        "inputSchema": {
            "type": "object",
            "properties": {
                "notebook_name": {
                    "type": "string",
                    "description": "Notebook identifier to disconnect"
                }
            },
            "required": ["notebook_name"]
        }
    },
    "read_notebook": {
        "name": "read_notebook",
        "description": "Read a notebook and return cell information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "notebook_name": {
                    "type": "string",
                    "description": "Notebook identifier to read"
                },
                "response_format": {
                    "type": "string",
                    "description": "Response format: 'brief' or 'detailed'",
                    "enum": ["brief", "detailed"],
                    "default": "brief"
                },
                "start_index": {
                    "type": "integer",
                    "description": "Starting index for pagination (0-based)",
                    "default": 0,
                    "minimum": 0
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of items to return (0 means no limit)",
                    "default": 20,
                    "minimum": 0
                }
            },
            "required": ["notebook_name"]
        }
    },
    "insert_cell": {
        "name": "insert_cell",
        "description": "Insert a cell at specified position in the active notebook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cell_index": {
                    "type": "integer",
                    "description": "Target index for insertion (0-based), use -1 to append"
                },
                "cell_type": {
                    "type": "string",
                    "description": "Type of cell to insert",
                    "enum": ["code", "markdown"]
                },
                "cell_source": {
                    "type": "string",
                    "description": "Source content for the cell"
                }
            },
            "required": ["cell_index", "cell_type", "cell_source"]
        }
    },
    "overwrite_cell_source": {
        "name": "overwrite_cell_source",
        "description": "Overwrite the source of a specific cell in the active notebook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cell_index": {
                    "type": "integer",
                    "description": "Index of the cell to overwrite (0-based)"
                },
                "cell_source": {
                    "type": "string",
                    "description": "New complete cell source"
                }
            },
            "required": ["cell_index", "cell_source"]
        }
    },
    "execute_cell": {
        "name": "execute_cell",
        "description": "Execute a cell from the active notebook and return outputs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cell_index": {
                    "type": "integer",
                    "description": "Index of the cell to execute (0-based)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum seconds to wait for execution",
                    "default": 90,
                    "minimum": 1
                },
                "stream": {
                    "type": "boolean",
                    "description": "Enable streaming progress updates",
                    "default": False
                },
                "progress_interval": {
                    "type": "integer",
                    "description": "Seconds between progress updates when stream=true",
                    "default": 5,
                    "minimum": 1
                }
            },
            "required": ["cell_index"]
        }
    },
    "insert_execute_code_cell": {
        "name": "insert_execute_code_cell",
        "description": "Insert a code cell and execute it immediately",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cell_index": {
                    "type": "integer",
                    "description": "Index to insert the cell (0-based)"
                },
                "cell_source": {
                    "type": "string",
                    "description": "Code source for the cell"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum seconds to wait for execution",
                    "default": 90,
                    "minimum": 1
                }
            },
            "required": ["cell_index", "cell_source"]
        }
    },
    "read_cell": {
        "name": "read_cell",
        "description": "Read a specific cell from the active notebook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cell_index": {
                    "type": "integer",
                    "description": "Index of the cell to read (0-based)"
                },
                "include_outputs": {
                    "type": "boolean",
                    "description": "Include outputs in the response",
                    "default": True
                }
            },
            "required": ["cell_index"]
        }
    },
    "delete_cell": {
        "name": "delete_cell",
        "description": "Delete specific cells from the active notebook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cell_indices": {
                    "type": "array",
                    "description": "List of indices of cells to delete (0-based)",
                    "items": {"type": "integer"}
                },
                "include_source": {
                    "type": "boolean",
                    "description": "Whether to include source of deleted cells",
                    "default": True
                }
            },
            "required": ["cell_indices"]
        }
    },
    "execute_code": {
        "name": "execute_code",
        "description": "Execute code directly in the kernel without saving to notebook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code to execute (supports magic commands and shell commands)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (max: 60)",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 60
                }
            },
            "required": ["code"]
        }
    },
    "stop_execution": {
        "name": "stop_execution",
        "description": "Stop the current cell execution in the active notebook",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "set_active_notebook": {
        "name": "set_active_notebook",
        "description": "Set a different notebook as active",
        "inputSchema": {
            "type": "object",
            "properties": {
                "notebook_name": {
                    "type": "string",
                    "description": "Name of notebook to activate"
                }
            },
            "required": ["notebook_name"]
        }
    },
    "move_cell": {
        "name": "move_cell",
        "description": "Move a cell from one position to another in the active notebook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_index": {
                    "type": "integer",
                    "description": "Current index of the cell to move (0-based)"
                },
                "to_index": {
                    "type": "integer",
                    "description": "Target index to move the cell to (0-based)"
                }
            },
            "required": ["from_index", "to_index"]
        }
    },
    "swap_cells": {
        "name": "swap_cells",
        "description": "Swap two cells in the active notebook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index1": {
                    "type": "integer",
                    "description": "Index of first cell (0-based)"
                },
                "index2": {
                    "type": "integer",
                    "description": "Index of second cell (0-based)"
                }
            },
            "required": ["index1", "index2"]
        }
    },
    "reorder_cells": {
        "name": "reorder_cells",
        "description": "Reorder cells according to a new sequence of indices. The new_order list must contain all indices from 0 to len(cells)-1 exactly once.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "new_order": {
                    "type": "array",
                    "description": "List of cell indices in the desired order (e.g., [2, 0, 3, 1] moves cell 2 to position 0, cell 0 to position 1, etc.)",
                    "items": {"type": "integer"}
                }
            },
            "required": ["new_order"]
        }
    }
}


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas as a list"""
    return list(TOOL_SCHEMAS.values())
