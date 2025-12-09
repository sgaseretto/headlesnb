# HeadlesNB API Documentation

This document provides the complete API reference for HeadlesNB. For design rationale and architectural decisions, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Table of Contents

- [API Design Principles](#api-design-principles)
- [NotebookManager](#notebookmanager)
- [DialogManager](#dialogmanager)
- [LLM Clients](#llm-clients)

---

## API Design Principles

Understanding these principles helps you use the API effectively and anticipate behavior:

### 1. Active Item Pattern

Both NotebookManager and DialogManager use an "active item" pattern:
- One notebook/dialog is "active" at a time
- Operations without explicit target use the active item
- **Why**: Simplifies API for sequential operations, reduces parameter repetition

```python
manager.set_active_notebook("nb1")
manager.insert_cell(0, "code", "x = 1")  # Applies to nb1
```

### 2. String Returns for Status, Dict/List for Data

- Status messages return formatted strings (TSV tables, success messages)
- Data queries return dicts or lists
- **Why**: Strings are human-readable for MCP/CLI output; structured data enables programmatic use

### 3. Index-Based vs ID-Based

- **NotebookManager**: Uses integer indices (0-based)
- **DialogManager**: Uses string IDs (e.g., `_a1b2c3d4`)
- **Why**: Notebooks are edited sequentially (indices natural); dialogs need stable references (LLM, pinned messages)

### 4. Operation History

Only structure-modifying operations are tracked for undo/redo:
- Tracked: insert, delete, update, move, swap
- Not tracked: execute, read, list
- **Why**: Execution is re-runnable; reads don't change state

---

## NotebookManager

The main class for managing notebooks programmatically. Wraps execnb with multi-notebook support, undo/redo, and MCP compatibility.

### Initialization

```python
from headlesnb import NotebookManager

manager = NotebookManager(root_path=".")
```

**Parameters:**
- `root_path` (str): Root path for file operations (default: ".")

---

## Server Management Tools

### list_files

List all files and directories recursively in the file system.

```python
result = manager.list_files(
    path="",
    max_depth=1,
    start_index=0,
    limit=25,
    pattern=""
)
```

**Parameters:**
- `path` (str): Starting path to list from (empty string means root directory)
- `max_depth` (int): Maximum depth to recurse (default: 1, max: 3)
- `start_index` (int): Starting index for pagination (default: 0)
- `limit` (int): Maximum items to return (0 means no limit, default: 25)
- `pattern` (str): Glob pattern to filter files (default: "")

**Returns:** Tab-separated table with columns: Path, Type, Size, Last_Modified

---

### list_kernels

List all available kernels (managed notebooks).

```python
result = manager.list_kernels()
```

**Returns:** Tab-separated table with kernel information

---

## Multi-Notebook Management Tools

### use_notebook

Use a notebook and activate it for cell operations.

```python
result = manager.use_notebook(
    notebook_name="my_notebook",
    notebook_path="path/to/notebook.ipynb",
    mode="connect",
    kernel_id=None
)
```

**Parameters:**
- `notebook_name` (str): Unique identifier for the notebook
- `notebook_path` (str): Path to the notebook file
- `mode` (str): "connect" to use existing, "create" to create new (default: "connect")
- `kernel_id` (str, optional): Specific kernel ID to use

**Returns:** Success message with notebook information

---

### list_notebooks

List all notebooks currently in use.

```python
result = manager.list_notebooks()
```

**Returns:** TSV formatted table with notebook information

---

### restart_notebook

Restart the kernel for a specific notebook.

```python
result = manager.restart_notebook(notebook_name="my_notebook")
```

**Parameters:**
- `notebook_name` (str): Notebook identifier to restart

**Returns:** Success message

---

### unuse_notebook

Disconnect from a notebook and release its resources.

```python
result = manager.unuse_notebook(notebook_name="my_notebook")
```

**Parameters:**
- `notebook_name` (str): Notebook identifier to disconnect

**Returns:** Success message

---

### read_notebook

Read a notebook and return cell information.

```python
result = manager.read_notebook(
    notebook_name="my_notebook",
    response_format="brief",
    start_index=0,
    limit=20
)
```

**Parameters:**
- `notebook_name` (str): Notebook identifier to read
- `response_format` (str): "brief" or "detailed" (default: "brief")
- `start_index` (int): Starting index for pagination (default: 0)
- `limit` (int): Maximum items to return (default: 20)

**Returns:** Notebook content in requested format

---

## Cell Tools

### insert_cell

Insert a cell at specified position in the active notebook.

```python
result = manager.insert_cell(
    cell_index=0,
    cell_type="code",
    cell_source="print('Hello')"
)
```

**Parameters:**
- `cell_index` (int): Target index for insertion (0-based), use -1 to append
- `cell_type` (str): "code" or "markdown"
- `cell_source` (str): Source content for the cell

**Returns:** Success message with surrounding cell structure

---

### overwrite_cell_source

Overwrite the source of a specific cell.

```python
result = manager.overwrite_cell_source(
    cell_index=0,
    cell_source="print('Updated')"
)
```

**Parameters:**
- `cell_index` (int): Index of cell to overwrite (0-based)
- `cell_source` (str): New complete cell source

**Returns:** Success message with diff-style comparison

---

### execute_cell

Execute a cell from the active notebook.

```python
outputs = manager.execute_cell(
    cell_index=0,
    timeout=90,
    stream=False,
    progress_interval=5
)
```

**Parameters:**
- `cell_index` (int): Index of cell to execute (0-based)
- `timeout` (int): Maximum seconds to wait (default: 90)
- `stream` (bool): Enable streaming progress (default: False)
- `progress_interval` (int): Seconds between updates (default: 5)

**Returns:** List of outputs from the executed cell

---

### insert_execute_code_cell

Insert a code cell and execute it immediately.

```python
outputs = manager.insert_execute_code_cell(
    cell_index=0,
    cell_source="x = 42\nprint(x)",
    timeout=90
)
```

**Parameters:**
- `cell_index` (int): Index to insert the cell (0-based)
- `cell_source` (str): Code source for the cell
- `timeout` (int): Maximum seconds to wait (default: 90)

**Returns:** List of outputs including insertion confirmation

---

### read_cell

Read a specific cell from the active notebook.

```python
outputs = manager.read_cell(
    cell_index=0,
    include_outputs=True
)
```

**Parameters:**
- `cell_index` (int): Index of cell to read (0-based)
- `include_outputs` (bool): Include outputs in response (default: True)

**Returns:** List containing cell metadata, source, and outputs

---

### delete_cell

Delete specific cells from the active notebook.

```python
result = manager.delete_cell(
    cell_indices=[0, 2],
    include_source=True
)
```

**Parameters:**
- `cell_indices` (list[int]): List of indices to delete (0-based)
- `include_source` (bool): Include source of deleted cells (default: True)

**Returns:** Success message with deleted cell sources

**Important:** When deleting many cells, delete them in descending order to avoid index shifting.

---

### execute_code

Execute code directly in the kernel without saving to notebook.

```python
outputs = manager.execute_code(
    code="print('Hello')",
    timeout=30
)
```

**Parameters:**
- `code` (str): Code to execute (supports magic commands and shell commands)
- `timeout` (int): Execution timeout in seconds (max: 60, default: 30)

**Returns:** List of outputs from the executed code

**Recommended for:**
1. Jupyter magic commands (e.g., %timeit, %pip install)
2. Performance profiling and debugging
3. Viewing intermediate variable values
4. Temporary calculations and quick tests
5. Shell commands (e.g., !git status)

---

### move_cell

Move a cell from one position to another in the active notebook.

```python
result = manager.move_cell(
    from_index=1,
    to_index=0
)
```

**Parameters:**
- `from_index` (int): Current index of the cell to move (0-based)
- `to_index` (int): Target index to move the cell to (0-based)

**Returns:** Success message with notebook structure around the moved cell

**Example:**
```python
# Move imports cell to the top
manager.move_cell(from_index=3, to_index=0)

# Move conclusion to the end
manager.move_cell(from_index=0, to_index=-1)  # Note: use actual last index, not -1
```

---

### swap_cells

Swap two cells in the active notebook.

```python
result = manager.swap_cells(
    index1=0,
    index2=2
)
```

**Parameters:**
- `index1` (int): Index of first cell (0-based)
- `index2` (int): Index of second cell (0-based)

**Returns:** Success message with information about swapped cells

**Example:**
```python
# Swap adjacent cells
manager.swap_cells(index1=0, index2=1)

# Swap distant cells
manager.swap_cells(index1=0, index2=5)
```

---

### reorder_cells

Reorder all cells according to a new sequence of indices.

```python
result = manager.reorder_cells(
    new_order=[2, 0, 3, 1]
)
```

**Parameters:**
- `new_order` (list[int]): List of cell indices in the desired order. Must contain all indices from 0 to len(cells)-1 exactly once.

**Returns:** Success message with summary of changes

**Example:**
```python
# Reverse all cells
nb_info = manager.notebooks[manager.active_notebook]
cell_count = len(nb_info.notebook.cells)
manager.reorder_cells(list(range(cell_count-1, -1, -1)))

# Specific reordering: move cell 2 to start, then 0, then 3, then 1
manager.reorder_cells([2, 0, 3, 1])

# Organize notebook sections logically
# If you have: [Results, Code, Setup, Imports, Analysis, Conclusion]
# Indices:     [0,       1,    2,     3,       4,        5]
# Reorder to:  [Setup, Imports, Analysis, Code, Results, Conclusion]
manager.reorder_cells([2, 3, 4, 1, 0, 5])
```

**Note:** The `new_order` list must include every cell index exactly once. For example, if you have 4 cells (indices 0, 1, 2, 3), `new_order` must be a permutation of [0, 1, 2, 3].

---

## Undo/Redo Operations (NotebookManager)

### undo

Undo the last operation(s) on the active notebook.

```python
result = manager.undo(steps=1)
```

**Parameters:**
- `steps` (int): Number of operations to undo (default: 1)

**Returns:** Success message

---

### redo

Redo previously undone operation(s).

```python
result = manager.redo(steps=1)
```

**Parameters:**
- `steps` (int): Number of operations to redo (default: 1)

**Returns:** Success message

---

### get_history

Get the operation history for the active notebook.

```python
history = manager.get_history()
```

**Returns:** Dictionary with undo_stack and redo_stack information

---

### clear_history

Clear the operation history for the active notebook.

```python
manager.clear_history()
```

---

## Additional Tools

### stop_execution

Stop the current cell execution in the active notebook.

```python
result = manager.stop_execution()
```

**Returns:** Success message

---

### set_active_notebook

Set a different notebook as active.

```python
result = manager.set_active_notebook(notebook_name="my_notebook")
```

**Parameters:**
- `notebook_name` (str): Name of notebook to activate

**Returns:** Success message

---

### get_active_notebook

Get the name of the currently active notebook.

```python
name = manager.get_active_notebook()
```

**Returns:** Name of active notebook or None

---

## DialogManager

The DialogManager class provides AI-assisted dialog conversations stored as Jupyter notebooks with extended metadata.

### Initialization

```python
from headlesnb import DialogManager
from headlesnb.dialogmanager.llm import MockLLMClient

# Create manager with mock LLM for testing
manager = DialogManager(
    root_path=".",
    default_llm_client=MockLLMClient(responses=["Hello!", "Here's my response."])
)
```

**Parameters:**
- `root_path` (str): Root path for file operations (default: ".")
- `default_llm_client` (LLMClient, optional): Default LLM client for prompts

---

## Dialog Management Tools

### use_dialog

Create or connect to a dialog.

```python
result = manager.use_dialog(
    dialog_name="my_dialog",
    dialog_path="path/to/dialog.ipynb",
    mode="create",
    llm_client=None
)
```

**Parameters:**
- `dialog_name` (str): Unique identifier for the dialog
- `dialog_path` (str): Path to the dialog file
- `mode` (str): "create" for new, "connect" for existing (default: "connect")
- `llm_client` (LLMClient, optional): Dialog-specific LLM client

**Returns:** Success message with dialog information

---

### unuse_dialog

Disconnect from a dialog and release resources.

```python
result = manager.unuse_dialog(dialog_name="my_dialog")
```

**Parameters:**
- `dialog_name` (str): Dialog identifier to disconnect

**Returns:** Success message

---

### list_dialogs

List all dialogs currently in use.

```python
result = manager.list_dialogs()
```

**Returns:** TSV formatted table with dialog information

---

### set_active_dialog

Set a different dialog as active.

```python
result = manager.set_active_dialog(dialog_name="my_dialog")
```

**Parameters:**
- `dialog_name` (str): Name of dialog to activate

**Returns:** Success message

---

### get_active_dialog

Get the name of the currently active dialog.

```python
name = manager.get_active_dialog()
```

**Returns:** Name of active dialog or None

---

### restart_kernel

Restart the kernel for a specific dialog.

```python
result = manager.restart_kernel(dialog_name="my_dialog")
```

**Parameters:**
- `dialog_name` (str): Dialog identifier to restart

**Returns:** Success message

---

## Message Management Tools

### add_message

Add a message to the active dialog.

```python
msg_id = manager.add_message(
    content="import pandas as pd",
    msg_type="code",
    pinned=0,
    skipped=0
)
```

**Parameters:**
- `content` (str): Message content
- `msg_type` (str): "code", "note", "prompt", or "raw" (default: "note")
- `pinned` (int): 1 to always include in LLM context (default: 0)
- `skipped` (int): 1 to exclude from LLM context (default: 0)

**Returns:** Message ID (string)

**Message Types:**
- `code` - Executable Python code
- `note` - Markdown documentation/context
- `prompt` - Questions for the LLM
- `raw` - Unprocessed content

---

### read_message

Read a specific message from the active dialog.

```python
msg_data = manager.read_message(
    msg_id="abc123",
    include_output=True
)
```

**Parameters:**
- `msg_id` (str): Message identifier
- `include_output` (bool): Include message output (default: True)

**Returns:** Dictionary with message data

---

### update_message

Update a message's content or attributes.

```python
result = manager.update_message(
    msg_id="abc123",
    content="Updated content",
    pinned=1
)
```

**Parameters:**
- `msg_id` (str): Message identifier
- `content` (str, optional): New content
- `pinned` (int, optional): New pinned status
- `skipped` (int, optional): New skipped status
- `output` (str, optional): New output

**Returns:** Success message

---

### delete_message

Delete a message from the active dialog.

```python
result = manager.delete_message(msg_id="abc123")
```

**Parameters:**
- `msg_id` (str): Message identifier

**Returns:** Success message

---

### list_messages

List all messages in the active dialog.

```python
messages = manager.list_messages(
    include_content=True,
    include_output=False
)
```

**Parameters:**
- `include_content` (bool): Include message content (default: True)
- `include_output` (bool): Include message outputs (default: False)

**Returns:** List of message dictionaries

---

### move_message

Move a message to a new position.

```python
result = manager.move_message(
    msg_id="abc123",
    new_index=0
)
```

**Parameters:**
- `msg_id` (str): Message identifier
- `new_index` (int): Target position (0-based)

**Returns:** Success message

---

### swap_messages

Swap two messages in the dialog.

```python
result = manager.swap_messages(
    msg_id1="abc123",
    msg_id2="def456"
)
```

**Parameters:**
- `msg_id1` (str): First message identifier
- `msg_id2` (str): Second message identifier

**Returns:** Success message

---

## Execution Tools

### execute_code (DialogManager)

Execute code in the dialog's kernel.

```python
outputs = manager.execute_code(
    code="print('Hello')",
    timeout=30,
    save_to_dialog=False
)
```

**Parameters:**
- `code` (str): Code to execute
- `timeout` (int): Execution timeout in seconds (default: 30)
- `save_to_dialog` (bool): Save as a code message (default: False)

**Returns:** List of execution outputs

---

### execute_prompt

Execute the most recent prompt message with the LLM.

```python
response = manager.execute_prompt(
    system_prompt="You are a helpful assistant.",
    include_context=True,
    llm_client=None
)
```

**Parameters:**
- `system_prompt` (str): System prompt for the LLM (default: "")
- `include_context` (bool): Include prior messages as context (default: True)
- `llm_client` (LLMClient, optional): Override LLM client for this call

**Returns:** LLMResponse object with content, tool_calls, usage, model, stop_reason

---

## Undo/Redo Operations (DialogManager)

### undo

Undo the last operation(s) on the active dialog.

```python
result = manager.undo(steps=1)
```

**Parameters:**
- `steps` (int): Number of operations to undo (default: 1)

**Returns:** Success message

---

### redo

Redo previously undone operation(s).

```python
result = manager.redo(steps=1)
```

**Parameters:**
- `steps` (int): Number of operations to redo (default: 1)

**Returns:** Success message

---

### get_history

Get the operation history for the active dialog.

```python
history = manager.get_history()
```

**Returns:** Dictionary with undo_stack and redo_stack information

---

### clear_history

Clear the operation history for the active dialog.

```python
manager.clear_history()
```

---

## LLM Clients

HeadlesNB provides an abstract `LLMClient` interface and a `MockLLMClient` for testing.

### LLMClient Interface

```python
from headlesnb.dialogmanager.llm import LLMClient, LLMResponse

class MyLLMClient(LLMClient):
    def chat(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        **kwargs
    ) -> LLMResponse:
        # Implement chat functionality
        pass

    def count_tokens(self, text: str) -> int:
        # Implement token counting
        pass
```

### LLMResponse

```python
from headlesnb.dialogmanager.llm import LLMResponse

@dataclass
class LLMResponse:
    content: str                              # Response text
    tool_calls: Optional[List[Dict]] = None   # Tool/function calls
    usage: Optional[Dict[str, int]] = None    # Token usage stats
    model: Optional[str] = None               # Model used
    stop_reason: Optional[str] = None         # Why generation stopped
```

### MockLLMClient

Mock client for testing without API calls.

```python
from headlesnb.dialogmanager.llm import MockLLMClient, MockLLMResponse

# Simple mock with predefined responses
client = MockLLMClient(responses=[
    "First response",
    "Second response"
])

# Mock with tool calls
from headlesnb.dialogmanager.llm import create_mock_for_tool_use

client = create_mock_for_tool_use(
    tool_name="search",
    tool_input={"query": "test"},
    final_response="Found 5 results"
)
```

**Parameters:**
- `responses` (list): List of response strings or MockLLMResponse objects
- `default_response` (str): Fallback response when responses exhausted

---

### ContextBuilder

Build LLM context windows with token budget management.

```python
from headlesnb.dialogmanager.llm import ContextBuilder

builder = ContextBuilder(
    llm_client=client,  # Optional, for token counting
    max_tokens=200000
)

messages = builder.build_context(
    dialog_messages=dialog.messages,
    current_prompt="What does this code do?",
    include_outputs=True,
    system_prompt="You are helpful.",
    reserved_tokens=4096
)
```

**Features:**
- Pinned messages always included
- Skipped messages never included
- Token budget management
- Maintains message order
- Proper user/assistant pairing

---

## Message Dataclass

```python
from headlesnb.dialogmanager import Message

@dataclass
class Message:
    content: str = ""
    msg_type: Optional[str] = "note"  # 'code', 'note', 'prompt', 'raw'
    output: str = ""
    time_run: Optional[str] = None
    is_exported: int = 0
    skipped: int = 0                  # Exclude from LLM context
    pinned: int = 0                   # Always include in LLM context
    i_collapsed: int = 0
    o_collapsed: int = 0
    heading_collapsed: int = 0
    use_thinking: bool = False
    id: str = field(default_factory=generate_msg_id)
```

---

## Output Formats

### Text Outputs

Simple text outputs are returned as strings:

```python
"Hello, World!"
```

### Image Outputs

Images are returned as dictionaries:

```python
{
    'type': 'image',
    'format': 'png',  # or 'jpeg'
    'data': 'base64-encoded-data'
}
```

### HTML Outputs

HTML content is returned as dictionaries:

```python
{
    'type': 'html',
    'content': '<div>HTML content</div>'
}
```

### Error Outputs

Errors are formatted with traceback:

```python
"[ERROR] ValueError: error message\ntraceback..."
```

---

## Examples

See the `examples/` directory for complete usage examples:

- `basic_usage.py` - Basic notebook operations
- `multi_notebook.py` - Managing multiple notebooks
- `file_operations.py` - File system operations

See the QUICKSTART.md for DialogManager patterns and examples.
