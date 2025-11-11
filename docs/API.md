# HeadlesNB API Documentation

## NotebookManager

The main class for managing notebooks programmatically.

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
