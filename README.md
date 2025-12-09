# HeadlesNB - Headless Notebook Server with MCP Support

A headless notebook execution server built on top of `execnb` with Model Context Protocol (MCP) support for programmatic notebook manipulation and stateful execution. Now with **DialogManager** for AI-assisted conversations.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why HeadlesNB?

### The Problem

Traditional Jupyter notebooks require a running Jupyter server, which adds complexity:
- Heavy dependencies and resource usage
- Network overhead for local operations
- Complex multi-user coordination
- Not designed for programmatic/AI-assisted access

### Our Solution

HeadlesNB uses IPython's `InteractiveShell` directly (via `execnb`), giving you:
- **Same execution capabilities** as Jupyter without the server
- **Direct programmatic control** via Python API, MCP, or HTTP
- **Multiple independent kernels** for parallel notebook execution
- **Full undo/redo support** using the Command Pattern

### Who Is This For?

| Use Case | Why HeadlesNB? |
|----------|----------------|
| AI assistants | MCP protocol support, structured tool interface |
| Automation scripts | Direct Python API, no server setup |
| Testing pipelines | Fast, isolated execution environments |
| Dialog-based AI apps | DialogManager with LLM integration |
| Notebook preprocessing | Read/modify notebooks without execution overhead |

> **For Architecture & Design Decisions**: See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed explanations of what each component does, how it works, and why it was designed that way.

## Features

### Core Capabilities

- **Server Management**: List files and kernels with pagination and filtering
- **Multi-Notebook Management**: Manage multiple notebooks simultaneously with independent kernels
- **Cell Operations**: Insert, execute, read, modify, and delete cells programmatically
- **Kernel Control**: Restart kernels and stop cell execution on demand
- **State Management**: Maintain execution state across multiple notebooks
- **MCP Server**: Full Model Context Protocol support for AI assistant integration
- **Undo/Redo**: Full operation history with Command Pattern implementation

### DialogManager (NEW)

- **AI-Assisted Dialogs**: Manage conversational AI interactions as notebooks
- **Multiple Message Types**: Code, Notes, Prompts, and Raw messages
- **LLM Integration**: Abstract LLM client interface with mock implementation for testing
- **Context Window Management**: Smart context building with pinned/skipped messages
- **Serialization**: Full roundtrip between Dialog format and `.ipynb` files

### DialogHelper Server (NEW)

- **FastHTML Backend**: HTTP server compatible with dialoghelper client library
- **Full API Support**: All dialoghelper endpoints including message CRUD, text editing, SSE
- **Real-time Updates**: Server-Sent Events (SSE) for HTML OOB swaps
- **Async Data Exchange**: Blocking data pop with timeout for event-driven patterns

### Key Advantages

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

### NotebookManager - Python Library Usage

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

### DialogManager - AI-Assisted Conversations

```python
from headlesnb import DialogManager
from headlesnb.dialogmanager.llm import MockLLMClient

# Create manager with mock LLM for testing
manager = DialogManager(
    root_path=".",
    default_llm_client=MockLLMClient(responses=["This is a test response."])
)

# Create a new dialog
manager.use_dialog("chat", "chat.ipynb", mode="create")

# Add messages of different types
manager.add_message("# Analysis Session", msg_type='note')
manager.add_message("import pandas as pd\ndf = pd.DataFrame()", msg_type='code')
manager.add_message("What does this code do?", msg_type='prompt')

# Execute code
manager.execute_code(msg_id=None, code="print('Hello')")

# Execute prompt via LLM
response = manager.execute_prompt()
print(response.content)  # "This is a test response."

# Clean up
manager.unuse_dialog("chat")
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

### DialogHelper Server (NEW)

The DialogHelper server is a FastHTML-based HTTP server that provides a backend compatible with the [dialoghelper](https://github.com/AnswerDotAI/dialoghelper) client library. This allows you to use dialoghelper's Python client functions to interact with dialogs over HTTP.

#### Starting the Server

```bash
# Start with default settings (port 5001, creates demo dialog)
python -m headlesnb.dialoghelper_server

# Or use the example script with options
python examples/dialoghelper_server_example.py --port 5001 --root-path ./dialogs

# Without demo dialog
python examples/dialoghelper_server_example.py --no-demo
```

#### Using with DialogHelper Client

In a Jupyter notebook or Python script:

```python
# Required setup variables
__dialog_name = 'demo'
__msg_id = '_startup00'

# Import dialoghelper functions
from dialoghelper.core import (
    curr_dialog, find_msgs, read_msg, add_msg,
    update_msg, del_msg, msg_idx, msg_str_replace
)

# Get current dialog info
info = curr_dialog()
print(info)  # {'name': 'demo', 'mode': 'default'}

# Find all messages
msgs = find_msgs()

# Add a new note
new_id = add_msg("This is a new note", msg_type='note', placement='at_end')

# Read with line numbers
result = read_msg(n=0, relative=False, nums=True)
print(result['msg']['content'])

# Text editing
msg_str_replace(new_id, old_str='note', new_str='message')
```

#### Server Endpoints

The server implements all endpoints expected by the dialoghelper client:

| Endpoint | Description |
|----------|-------------|
| `POST /curr_dialog_` | Get current dialog info |
| `POST /find_msgs_` | Find messages by pattern/type |
| `POST /read_msg_` | Read a message |
| `POST /add_relative_` | Add message relative to another |
| `POST /update_msg_` | Update message content/attributes |
| `POST /rm_msg_` | Delete a message |
| `POST /msg_idx_` | Get message index |
| `POST /msg_str_replace_` | String replace in message |
| `POST /msg_insert_line_` | Insert line in message |
| `POST /msg_replace_lines_` | Replace line range |
| `POST /add_runq_` | Add to execution queue |
| `GET /html_stream_` | SSE endpoint for HTML updates |

#### Programmatic Usage

```python
from headlesnb.dialoghelper_server import app, init_manager, serve

# Initialize with custom root path
manager = init_manager(root_path="/path/to/dialogs")

# Create a dialog
manager.use_dialog("my_dialog", "dialog.ipynb", mode="create")

# Start the server
serve(port=5001, host="0.0.0.0")
```

## Available Tools

### NotebookManager Tools (25 tools)

#### Server Management (2 tools)
1. **list_files** - List files and directories with pagination and filtering
2. **list_kernels** - List all active kernels and their status

#### Multi-Notebook Management (6 tools)
3. **use_notebook** - Connect to or create a notebook
4. **list_notebooks** - List all notebooks currently in use
5. **restart_notebook** - Restart a notebook's kernel (clears state)
6. **unuse_notebook** - Disconnect and save a notebook
7. **read_notebook** - Read notebook contents (brief or detailed)
8. **set_active_notebook** - Switch the active notebook

#### Cell Operations (11 tools)
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

#### Undo/Redo Operations (4 tools)
20. **undo** - Undo the last N operations
21. **redo** - Redo the last N undone operations
22. **get_history** - View operation history
23. **clear_history** - Clear all undo/redo history

### DialogManager Tools

#### Dialog Management
- **use_dialog** - Create or connect to a dialog
- **unuse_dialog** - Release a dialog
- **list_dialogs** - List all active dialogs
- **set_active_dialog** - Switch active dialog

#### Message Operations
- **add_message** - Add a message (code, note, prompt, raw)
- **update_message** - Update message content or attributes
- **delete_message** - Delete messages by ID
- **read_message** - Read a specific message
- **list_messages** - List messages with filtering

#### Execution
- **execute_code** - Execute code directly or by message ID
- **execute_prompt** - Send prompt to LLM and get response

#### History
- **undo/redo** - Full undo/redo support
- **get_history** - View operation history
- **clear_history** - Clear history

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Guide](docs/ARCHITECTURE.md) | **Start here for understanding the codebase** - explains what, how, and why for each component |
| [API Reference](docs/API.md) | Complete API documentation for all tools |
| [DialogManager Guide](docs/DIALOGMANAGER.md) | Deep dive into AI dialog management |
| [DialogHelper Server](docs/DIALOGHELPER_SERVER.md) | HTTP server for dialoghelper client |
| [MCP Server Guide](docs/MCP_SERVER.md) | MCP protocol server setup and usage |
| [Examples](examples/) | Complete usage examples |

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

### DialogManager with Mock LLM

```python
from headlesnb import DialogManager
from headlesnb.dialogmanager.llm import MockLLMClient, MockLLMResponse

# Create mock with tool use simulation
client = MockLLMClient(responses=[
    MockLLMResponse(
        content="I'll analyze that code.",
        tool_calls=[{"name": "analyze", "input": {"code": "..."}}],
        stop_reason="tool_use"
    ),
    "The code creates a DataFrame with columns A and B."
])

manager = DialogManager(default_llm_client=client)
manager.use_dialog("analysis", "analysis.ipynb", mode="create")

# Add context
manager.add_message("import pandas as pd", msg_type='code')
manager.add_message("df = pd.DataFrame({'A': [1,2], 'B': [3,4]})", msg_type='code')
manager.add_message("What does this code do?", msg_type='prompt')

# Execute prompt
response = manager.execute_prompt()
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

### Undo/Redo Operations

```python
# Perform operations
manager.insert_cell(0, "code", "x = 1")
manager.insert_cell(1, "code", "y = 2")

# Undo the last operation
manager.undo()

# Undo multiple operations
manager.undo(steps=2)

# Redo operations
manager.redo(steps=2)

# View history
print(manager.get_history())
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
pytest tests/test_dialogmanager.py -v
```

## Project Structure

```
headlesnb/
├── headlesnb/                     # Main package
│   ├── __init__.py
│   ├── base.py                    # Abstract base classes (BaseManager, ManagedItemInfo)
│   │                              # WHY: Shared infrastructure for notebooks & dialogs
│   ├── nb_manager.py              # NotebookManager - notebook CRUD and execution
│   │                              # WHY: High-level API wrapping low-level execnb
│   ├── history.py                 # Command Pattern undo/redo for notebooks
│   │                              # WHY: Reversible operations require stored commands
│   ├── tools.py                   # MCP tool schema definitions (JSON Schema)
│   ├── mcp_server.py              # MCP server implementation
│   ├── dialoghelper_server.py     # FastHTML HTTP server for dialoghelper client
│   │                              # WHY: HTTP API enables web UIs and remote access
│   └── dialogmanager/             # DialogManager package
│       ├── __init__.py
│       ├── message.py             # Message dataclass with ID, type, pinned/skipped
│       │                          # WHY: Dialogs need stable IDs (unlike cell indices)
│       ├── dialog_info.py         # DialogInfo - dialog state container
│       ├── manager.py             # DialogManager - dialog and LLM operations
│       ├── serialization.py       # Dialog <-> .ipynb conversion
│       │                          # WHY: Reuse Jupyter format for interoperability
│       ├── dialog_history.py      # Command Pattern undo/redo for dialogs
│       └── llm/                   # LLM client implementations
│           ├── base.py            # Abstract LLMClient, LLMResponse dataclass
│           │                      # WHY: Pluggable LLM backends
│           ├── mock.py            # MockLLMClient for testing without API calls
│           └── context.py         # ContextBuilder - token-aware context assembly
│                                  # WHY: LLM context windows are limited
├── tests/                         # Unit and integration tests
│   ├── test_manager.py            # NotebookManager tests (103 cases)
│   ├── test_dialogmanager.py      # DialogManager tests (46 cases)
│   ├── test_dialoghelper_server.py # HTTP server tests (28 cases)
│   ├── test_integration_dialoghelper.py # Client compatibility tests (19 cases)
│   ├── test_execnb.py             # execnb foundation tests
│   └── test_tools.py              # MCP tool schema tests
├── examples/                      # Usage examples
│   ├── basic_usage.py
│   ├── multi_notebook.py
│   ├── dialoghelper_server_example.py  # HTTP server startup script
│   ├── dialoghelper_client_demo.ipynb  # Client usage notebook
│   └── ...
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md            # Design decisions and rationale (START HERE)
│   ├── API.md                     # Complete API reference
│   ├── DIALOGMANAGER.md           # Dialog management deep dive
│   ├── DIALOGHELPER_SERVER.md     # HTTP server documentation
│   └── MCP_SERVER.md              # MCP protocol guide
├── pyproject.toml                 # Project configuration and dependencies
└── README.md
```

## Architecture

HeadlesNB is built on five main components. For detailed design rationale, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Component Overview

| Component | What It Does | Why This Way |
|-----------|--------------|--------------|
| **execnb** | Wraps IPython's InteractiveShell for code execution | Reuses IPython's battle-tested execution engine instead of reimplementing |
| **NotebookManager** | Manages multiple notebooks with independent kernels | Each notebook needs isolated state; one shell per notebook ensures no variable leakage |
| **DialogManager** | Manages AI conversations with LLM integration | Dialogs have different semantics than notebooks (message types, pinned/skipped, prompt/response) |
| **MCP Server** | Exposes functionality via Model Context Protocol | Standard protocol for AI assistant integration |
| **DialogHelper Server** | HTTP server for dialoghelper client compatibility | Enables web-based UIs and remote access |

### Key Design Decisions

- **Command Pattern for Undo/Redo**: Each operation is a reversible command. Trade-off: memory for history vs full undo capability.
- **Notebooks as Persistence Format**: `.ipynb` files are interoperable with Jupyter. Trade-off: JSON overhead vs ecosystem compatibility.
- **Separate Notebook/Dialog Managers**: Different semantics justify separate implementations sharing common base classes.

> **Deep Dive**: See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full explanations of what, how, and why.

## Use Cases

- **AI-Assisted Development**: Integrate with Claude or other AI assistants
- **Conversational AI**: Build dialog-based AI applications
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
