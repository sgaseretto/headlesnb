# Quick Start Guide

Get started with HeadlesNB in 5 minutes!

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd headlesnb

# Install dependencies
pip install -e .
```

## Part 1: NotebookManager - Basic Usage

### 1. Create and Execute a Notebook

```python
from headlesnb import NotebookManager

# Initialize manager
manager = NotebookManager()

# Create a new notebook
manager.use_notebook("my_analysis", "analysis.ipynb", mode="create")

# Add cells
manager.insert_cell(0, "code", "import pandas as pd")
manager.insert_cell(1, "code", "data = {'x': [1,2,3], 'y': [4,5,6]}")
manager.insert_cell(2, "code", "df = pd.DataFrame(data)\nprint(df)")

# Execute cells
manager.execute_cell(0)
manager.execute_cell(1)
outputs = manager.execute_cell(2)

print("Output:", outputs)

# Clean up
manager.unuse_notebook("my_analysis")
```

### 2. Work with Existing Notebook

```python
# Connect to existing notebook
manager.use_notebook("existing", "existing.ipynb", mode="connect")

# Read notebook structure
print(manager.read_notebook("existing", response_format="brief"))

# Execute a specific cell
outputs = manager.execute_cell(0)

# Execute code without saving
outputs = manager.execute_code("print('Quick test')")
```

### 3. Manage Multiple Notebooks

```python
# Create two notebooks
manager.use_notebook("data", "data.ipynb", mode="create")
manager.use_notebook("viz", "viz.ipynb", mode="create")

# Work with first notebook
manager.set_active_notebook("data")
manager.execute_code("raw_data = [1, 2, 3, 4, 5]")

# Switch to second notebook
manager.set_active_notebook("viz")
manager.execute_code("import matplotlib.pyplot as plt")

# List all notebooks
print(manager.list_notebooks())
```

---

## Part 2: DialogManager - AI-Assisted Conversations

### 1. Basic Dialog Usage

```python
from headlesnb import DialogManager
from headlesnb.dialogmanager.llm import MockLLMClient

# Create manager with mock LLM for testing
manager = DialogManager(
    root_path=".",
    default_llm_client=MockLLMClient(responses=[
        "This is a helpful response about your code.",
        "Here's another helpful answer."
    ])
)

# Create a new dialog
manager.use_dialog("chat", "chat.ipynb", mode="create")

# Add different message types
manager.add_message("# Analysis Session", msg_type='note')
manager.add_message("import pandas as pd", msg_type='code')
manager.add_message("What does pandas do?", msg_type='prompt')

# Execute the prompt
response = manager.execute_prompt()
print(response.content)  # "This is a helpful response about your code."

# Clean up
manager.unuse_dialog("chat")
```

### 2. Message Types Explained

```python
# Create a dialog
manager.use_dialog("demo", "demo.ipynb", mode="create")

# NOTE messages - Markdown content for context/documentation
manager.add_message("# Data Analysis\nThis notebook analyzes sales data.", msg_type='note')

# CODE messages - Executable Python code
manager.add_message("import pandas as pd\ndf = pd.read_csv('sales.csv')", msg_type='code')

# PROMPT messages - Questions for the LLM
manager.add_message("Explain the structure of this DataFrame", msg_type='prompt')

# RAW messages - Unprocessed content
manager.add_message("Some raw content here", msg_type='raw')

# Execute code
manager.execute_code(code="print('Hello')")

# Execute prompt
response = manager.execute_prompt()
```

### 3. Message Attributes

```python
# Add message with attributes
msg_id = manager.add_message(
    content="Important context",
    msg_type='note',
    pinned=1,      # Always include in LLM context
    skipped=0      # Set to 1 to exclude from context
)

# Update message attributes
manager.update_message(msg_id, content="Updated content")
manager.update_message(msg_id, pinned=0)

# Read message
msg_data = manager.read_message(msg_id=msg_id)
print(msg_data)

# Delete message
manager.delete_message(msg_id)
```

### 4. Context-Aware LLM Calls

```python
# Create dialog with context
manager.use_dialog("analysis", "analysis.ipynb", mode="create")

# Add context that will be included in LLM calls
manager.add_message("import numpy as np", msg_type='code', pinned=1)  # Always included
manager.add_message("# Helper Functions", msg_type='note')
manager.add_message("def square(x): return x ** 2", msg_type='code')
manager.add_message("Old discussion to skip", msg_type='note', skipped=1)  # Excluded

# Add prompt - context is automatically built
manager.add_message("How can I use the square function with numpy?", msg_type='prompt')

# Execute - prior messages become context for LLM
response = manager.execute_prompt(
    system_prompt="You are a helpful Python assistant.",
    include_context=True  # Default is True
)
```

---

## Part 3: MCP Server Usage

### 1. Start the Server

```bash
# Start with current directory as root
python -m headlesnb.mcp_server

# Or specify a root directory
python -m headlesnb.mcp_server /path/to/notebooks
```

### 2. Configure Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "headlesnb": {
      "command": "python",
      "args": ["-m", "headlesnb.mcp_server", "/path/to/your/notebooks"]
    }
  }
}
```

### 3. Use with Claude

After restarting Claude Desktop, you can:

```
Create a new notebook called "analysis" in analysis.ipynb
```

```
Insert a code cell that imports pandas and numpy
```

```
Execute the first cell
```

```
Show me the contents of the notebook
```

---

## Common Operations

### File Operations

```python
# List all notebook files
files = manager.list_files(pattern="*.ipynb", max_depth=2)
print(files)

# List with pagination
files = manager.list_files(limit=10, start_index=0)
```

### Cell Operations (NotebookManager)

```python
# Insert at specific position
manager.insert_cell(0, "code", "x = 42")

# Insert at end
manager.insert_cell(-1, "markdown", "# Results")

# Modify existing cell
manager.overwrite_cell_source(0, "x = 100")

# Delete cells (descending order!)
manager.delete_cell([2, 1], include_source=True)

# Read specific cell
outputs = manager.read_cell(0, include_outputs=True)
```

### Kernel Management

```python
# Restart kernel (clears state)
manager.restart_notebook("my_notebook")  # NotebookManager
manager.restart_kernel("my_dialog")       # DialogManager

# Stop running execution
manager.stop_execution()

# List all kernels
print(manager.list_kernels())
```

### Undo/Redo Operations

```python
# Perform some operations
manager.insert_cell(0, "code", "x = 1")
manager.insert_cell(1, "code", "y = 2")
manager.move_cell(1, 0)

# Undo the last operation
manager.undo()  # Undoes move_cell

# Undo multiple operations
manager.undo(steps=2)  # Undoes the two insert operations

# Redo operations
manager.redo()  # Redoes one insert
manager.redo(steps=2)  # Redoes two operations

# View operation history
print(manager.get_history())

# Clear history
manager.clear_history()
```

---

## DialogManager Patterns

### Pattern 1: Interactive Analysis Session

```python
from headlesnb import DialogManager
from headlesnb.dialogmanager.llm import MockLLMClient

# Setup
manager = DialogManager(
    default_llm_client=MockLLMClient(responses=["Analysis complete!"])
)
manager.use_dialog("session", "session.ipynb", mode="create")

# Build analysis incrementally
manager.add_message("# Sales Analysis", msg_type='note')
manager.add_message("import pandas as pd", msg_type='code')

# Execute code to load data
manager.execute_code(code="import pandas as pd")

# Ask LLM about the data
manager.add_message("What patterns should I look for in sales data?", msg_type='prompt')
response = manager.execute_prompt()
```

### Pattern 2: Code Review Dialog

```python
# Create a dialog for code review
manager.use_dialog("review", "review.ipynb", mode="create")

# Add code to review
manager.add_message('''
def process_data(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
''', msg_type='code')

# Ask for review
manager.add_message("Review this code for efficiency and suggest improvements", msg_type='prompt')
response = manager.execute_prompt()
print(response.content)
```

### Pattern 3: Iterative Problem Solving

```python
# Create dialog
manager.use_dialog("problem", "problem.ipynb", mode="create")

# First attempt
manager.add_message("def factorial(n): return 1 if n <= 1 else n * factorial(n-1)", msg_type='code')
manager.add_message("Is this implementation efficient for large numbers?", msg_type='prompt')
response1 = manager.execute_prompt()

# Follow-up based on response
manager.add_message("Show me an iterative version", msg_type='prompt')
response2 = manager.execute_prompt()
```

---

## NotebookManager Patterns

### Pattern 1: Quick Analysis

```python
manager = NotebookManager()
manager.use_notebook("quick", "quick.ipynb", mode="create")

# Add all code at once
code = """
import pandas as pd
import numpy as np

data = np.random.randn(100, 5)
df = pd.DataFrame(data, columns=['A', 'B', 'C', 'D', 'E'])
print(df.describe())
"""

outputs = manager.insert_execute_code_cell(0, code)
print(outputs)
```

### Pattern 2: Iterative Development

```python
# Start with imports
manager.insert_execute_code_cell(0, "import pandas as pd")

# Add data loading
manager.insert_execute_code_cell(1, "df = pd.read_csv('data.csv')")

# Explore data
manager.execute_code("df.head()")  # Quick check, not saved

# Add more analysis
manager.insert_execute_code_cell(2, "df.describe()")
```

### Pattern 3: Notebook Generation

```python
# Generate a complete notebook
manager.use_notebook("report", "report.ipynb", mode="create")

# Add header
manager.insert_cell(0, "markdown", "# Analysis Report")

# Add sections
manager.insert_cell(1, "markdown", "## Data Loading")
manager.insert_cell(2, "code", "import pandas as pd\ndf = pd.read_csv('data.csv')")

manager.insert_cell(3, "markdown", "## Statistics")
manager.insert_cell(4, "code", "df.describe()")

manager.insert_cell(5, "markdown", "## Visualizations")
manager.insert_cell(6, "code", "import matplotlib.pyplot as plt\ndf.plot()")

# Execute all code cells
for i in [2, 4, 6]:
    manager.execute_cell(i)
```

---

## Run Examples

```bash
# Basic usage example
cd examples
python basic_usage.py

# Multiple notebooks example
python multi_notebook.py

# File operations example
python file_operations.py
```

## Run Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_manager.py
pytest tests/test_dialogmanager.py

# Run with coverage
pytest tests/ --cov=headlesnb
```

---

## Troubleshooting

### Import Errors

```bash
# Make sure dependencies are installed
pip install fastcore ipython matplotlib-inline
```

### Notebook Not Found

```python
# Check the path is relative to root_path
manager = NotebookManager(root_path="/full/path/to/notebooks")
manager.use_notebook("test", "test.ipynb", mode="connect")
```

### Execution Timeout

```python
# Increase timeout for long-running cells
outputs = manager.execute_cell(0, timeout=300)  # 5 minutes
```

### Kernel State Issues

```python
# Restart kernel to clear state
manager.restart_notebook("my_notebook")
```

### Mock LLM for Testing

```python
# Use MockLLMClient to avoid API calls during development
from headlesnb.dialogmanager.llm import MockLLMClient

client = MockLLMClient(responses=["Test response 1", "Test response 2"])
manager = DialogManager(default_llm_client=client)
```

---

## Next Steps

- Read the [API Documentation](docs/API.md) for complete reference
- See [DialogManager Guide](docs/DIALOGMANAGER.md) for advanced DialogManager usage
- Check [MCP Server Guide](docs/MCP_SERVER.md) for AI integration
- Review [Contributing Guide](CONTRIBUTING.md) to contribute

## Need Help?

- Check [Issues](https://github.com/yourusername/headlesnb/issues) for common problems
- Read the [Full Documentation](docs/)
- Look at [Examples](examples/) for patterns

Happy notebook automation!
