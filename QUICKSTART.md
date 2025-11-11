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

## Basic Usage (Python API)

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

## MCP Server Usage

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

## Common Operations

### File Operations

```python
# List all notebook files
files = manager.list_files(pattern="*.ipynb", max_depth=2)
print(files)

# List with pagination
files = manager.list_files(limit=10, start_index=0)
```

### Cell Operations

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
manager.restart_notebook("my_notebook")

# Stop running execution
manager.stop_execution()

# List all kernels
print(manager.list_kernels())
```

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

# Run with coverage
pytest tests/ --cov=headlesnb
```

## Common Patterns

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

## Next Steps

- Read the [API Documentation](docs/API.md) for complete reference
- See [Examples](examples/) for more usage patterns
- Check [MCP Server Guide](docs/MCP_SERVER.md) for AI integration
- Review [Contributing Guide](CONTRIBUTING.md) to contribute

## Need Help?

- Check [Issues](https://github.com/yourusername/headlesnb/issues) for common problems
- Read the [Full Documentation](docs/)
- Look at [Examples](examples/) for patterns

Happy notebook automation! 🚀
