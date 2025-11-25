# HeadlesNB - Headless Notebook Server with MCP Support

A headless notebook execution server built on top of `execnb` with Model Context Protocol (MCP) support for programmatic notebook manipulation and stateful execution.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

### 🎯 Core Capabilities

- **Server Management**: List files and kernels with pagination and filtering
- **Multi-Notebook Management**: Manage multiple notebooks simultaneously with independent kernels
- **Cell Operations**: Insert, execute, read, modify, and delete cells programmatically
- **Kernel Control**: Restart kernels and stop cell execution on demand
- **State Management**: Maintain execution state across multiple notebooks
- **MCP Server**: Full Model Context Protocol support for AI assistant integration

### 🚀 Key Advantages

- **No Jupyter Server Required**: Run notebooks without the overhead of a full Jupyter server
- **Programmatic Control**: Full API for notebook manipulation
- **Multiple Notebooks**: Work with multiple notebooks in parallel
- **Fast Execution**: Lightweight execution based on IPython's InteractiveShell
- **State Preservation**: Keep variables and imports across cell executions
- **MCP Integration**: Ready for integration with Claude and other AI assistants

## Installation

### From Source

```bash
git clone <repository-url>
cd headlesnb
pip install -e .
```

### Dependencies

- Python 3.8+
- fastcore >= 1.5.29
- ipython >= 8.0.0
- matplotlib-inline >= 0.1.6
- mcp >= 0.1.0 (for MCP server)

## Quick Start

### Python Library Usage

```python
from headlesnb import NotebookManager

# Create a notebook manager
manager = NotebookManager(root_path=".")

# Create a new notebook
manager.use_notebook("analysis", "analysis.ipynb", mode="create")

# Insert some cells
manager.insert_cell(0, "code", "import pandas as pd")
manager.insert_cell(1, "code", "data = {'x': [1,2,3], 'y': [4,5,6]}")
manager.insert_cell(2, "code", "df = pd.DataFrame(data)\nprint(df)")

# Execute cells
manager.execute_cell(0)
manager.execute_cell(1)
outputs = manager.execute_cell(2)
print(outputs)

# Execute code without saving
outputs = manager.execute_code("df.describe()")
print(outputs)

# Clean up
manager.unuse_notebook("analysis")
```

### MCP Server Usage

Start the server:

```bash
python -m headlesnb.mcp_server /path/to/notebooks
```

Or integrate with Claude Desktop by adding to your configuration:

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

## Available Tools

### Server Management (2 tools)

1. **list_files** - List files and directories with pagination and filtering
2. **list_kernels** - List all active kernels and their status

### Multi-Notebook Management (6 tools)

3. **use_notebook** - Connect to or create a notebook
4. **list_notebooks** - List all notebooks currently in use
5. **restart_notebook** - Restart a notebook's kernel (clears state)
6. **unuse_notebook** - Disconnect and save a notebook
7. **read_notebook** - Read notebook contents (brief or detailed)
8. **set_active_notebook** - Switch the active notebook

### Cell Operations (11 tools)

9. **insert_cell** - Insert a code or markdown cell
10. **overwrite_cell_source** - Modify a cell's source code
11. **execute_cell** - Execute a cell and return outputs
12. **insert_execute_code_cell** - Insert and execute in one step
13. **read_cell** - Read a specific cell with outputs
14. **delete_cell** - Delete one or more cells
15. **execute_code** - Execute code without saving to notebook
16. **stop_execution** - Stop the currently running cell
17. **move_cell** - Move a cell from one position to another
18. **swap_cells** - Swap two cells
19. **reorder_cells** - Reorder all cells in a notebook

## Documentation

- [API Reference](docs/API.md) - Complete API documentation
- [MCP Server Guide](docs/MCP_SERVER.md) - MCP server setup and usage
- [Examples](examples/) - Complete usage examples

## Examples

### Basic Notebook Operations

```python
from headlesnb import NotebookManager

manager = NotebookManager()
manager.use_notebook("test", "test.ipynb", mode="create")

# Add and execute cells
manager.insert_cell(-1, "code", "x = 42")
manager.insert_cell(-1, "code", "print(f'Answer: {x}')")
manager.execute_cell(0)
outputs = manager.execute_cell(1)
print(outputs)  # ['Answer: 42']
```

### Multiple Notebooks

```python
# Work with two notebooks simultaneously
manager.use_notebook("data", "data.ipynb", mode="create")
manager.use_notebook("viz", "viz.ipynb", mode="create")

# Work in first notebook
manager.set_active_notebook("data")
manager.execute_code("data = [1, 2, 3, 4, 5]")

# Switch to second notebook
manager.set_active_notebook("viz")
manager.execute_code("import matplotlib.pyplot as plt")

# List all active notebooks
print(manager.list_notebooks())
```

### File Operations

```python
# List all notebook files
files = manager.list_files(pattern="*.ipynb", max_depth=2)
print(files)

# List with pagination
files = manager.list_files(limit=10, start_index=0)
print(files)
```

### Cell Reordering

```python
# Create a notebook with cells
manager.use_notebook("demo", "demo.ipynb", mode="create")
manager.insert_cell(0, "markdown", "# Header")
manager.insert_cell(1, "code", "import pandas as pd")
manager.insert_cell(2, "code", "df = pd.DataFrame()")

# Move a single cell
manager.move_cell(from_index=1, to_index=0)  # Move imports to top

# Swap two cells
manager.swap_cells(index1=0, index2=2)

# Reorder all cells at once
manager.reorder_cells([2, 0, 1])  # Rearrange to [cell2, cell0, cell1]
```

## Testing

Run all tests:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=headlesnb --cov-report=html
```

Run specific test file:

```bash
pytest tests/test_manager.py -v
```

## Project Structure

```
headlesnb/
├── execnb/              # Core notebook execution library
│   ├── __init__.py
│   ├── nbio.py          # Notebook I/O operations
│   └── shell.py         # IPython shell wrapper
├── headlesnb/           # Main package
│   ├── __init__.py
│   ├── manager.py       # NotebookManager class
│   ├── tools.py         # MCP tool definitions
│   └── mcp_server.py    # MCP server implementation
├── tests/               # Unit tests
│   ├── test_manager.py
│   ├── test_execnb.py
│   └── test_tools.py
├── examples/            # Usage examples
│   ├── basic_usage.py
│   ├── multi_notebook.py
│   └── file_operations.py
├── docs/                # Documentation
│   ├── API.md
│   └── MCP_SERVER.md
├── pyproject.toml       # Project configuration
└── README.md
```

## Architecture

HeadlesNB is built on three main components:

1. **execnb**: A lightweight library for executing notebooks without a Jupyter server
   - Based on IPython's InteractiveShell
   - Supports magic commands and shell commands
   - Maintains execution state

2. **NotebookManager**: High-level API for notebook manipulation
   - Manages multiple notebooks simultaneously
   - Tracks active notebook and kernel state
   - Provides comprehensive cell operations

3. **MCP Server**: Model Context Protocol server
   - Exposes all functionality via MCP
   - Ready for AI assistant integration
   - Follows MCP protocol specifications

## Use Cases

- **AI-Assisted Development**: Integrate with Claude or other AI assistants
- **Notebook Automation**: Programmatically create and execute notebooks
- **Testing**: Test notebook code in CI/CD pipelines
- **Batch Processing**: Run multiple notebooks in parallel
- **Interactive Analysis**: Build custom notebook interfaces
- **Education**: Create interactive learning environments

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built on top of:
- [execnb](https://github.com/fastai/execnb) - Fast notebook execution
- [IPython](https://ipython.org/) - Interactive Python shell
- [fastcore](https://github.com/fastai/fastcore) - Core utilities

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/headlesnb/issues)
- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)
