"""Basic usage examples for HeadlesNB"""

from headlesnb import NotebookManager

# Create a notebook manager
manager = NotebookManager(root_path=".")

# Example 1: Creating a new notebook
print("=== Example 1: Creating a New Notebook ===")
result = manager.use_notebook("my_notebook", "my_notebook.ipynb", mode="create")
print(result)

# Example 2: Inserting cells
print("\n=== Example 2: Inserting Cells ===")
manager.insert_cell(0, "markdown", "# My Data Analysis Notebook")
manager.insert_cell(1, "code", "import pandas as pd\nimport numpy as np")
manager.insert_cell(2, "code", "data = {'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]}")
manager.insert_cell(3, "code", "df = pd.DataFrame(data)\nprint(df)")

# Example 3: Executing cells
print("\n=== Example 3: Executing Cells ===")
outputs = manager.execute_cell(1)  # Import statements
print("Executed imports")

outputs = manager.execute_cell(2)  # Create data
print("Created data")

outputs = manager.execute_cell(3)  # Display dataframe
print("Outputs:", outputs)

# Example 4: Executing code directly (without saving to notebook)
print("\n=== Example 4: Direct Code Execution ===")
outputs = manager.execute_code("print(df.describe())")
print("Statistics:", outputs)

# Example 5: Reading notebook contents
print("\n=== Example 5: Reading Notebook ===")
result = manager.read_notebook("my_notebook", response_format="brief")
print(result)

# Example 6: Modifying a cell
print("\n=== Example 6: Modifying a Cell ===")
result = manager.overwrite_cell_source(3, "df = pd.DataFrame(data)\nprint(df.head())\nprint(df.tail())")
print(result)

# Example 7: Inserting and executing in one step
print("\n=== Example 7: Insert and Execute ===")
outputs = manager.insert_execute_code_cell(
    -1,  # Append to end
    "result = df['y'].sum()\nprint(f'Sum of y: {result}')"
)
print("Outputs:", outputs)

# Example 8: Deleting cells
print("\n=== Example 8: Deleting Cells ===")
# Note: Delete in descending order
result = manager.delete_cell([0], include_source=True)  # Delete the markdown header
print(result)

# Example 9: Restarting the kernel
print("\n=== Example 9: Restarting Kernel ===")
result = manager.restart_notebook("my_notebook")
print(result)

# Try to access a variable (should fail after restart)
outputs = manager.execute_code("print(df)")
print("After restart:", outputs)

# Example 10: Cleaning up
print("\n=== Example 10: Closing Notebook ===")
result = manager.unuse_notebook("my_notebook")
print(result)

print("\n=== Examples Complete ===")
