"""Example of cell reordering operations"""

from headlesnb import NotebookManager

# Create a notebook manager
manager = NotebookManager(root_path=".")

print("=== Cell Reordering Examples ===\n")

# Create a notebook with several cells
print("1. Creating a notebook with 5 cells...")
manager.use_notebook("reorder_demo", "reorder_demo.ipynb", mode="create")

# Add cells
manager.insert_cell(0, "markdown", "# Data Analysis Workflow")
manager.insert_cell(1, "code", "import pandas as pd\nimport numpy as np")
manager.insert_cell(2, "code", "data = {'x': [1,2,3,4,5], 'y': [2,4,6,8,10]}")
manager.insert_cell(3, "code", "df = pd.DataFrame(data)")
manager.insert_cell(4, "code", "print(df.describe())")

# Read the initial structure
print("\n2. Initial notebook structure:")
print(manager.read_notebook("reorder_demo", response_format="brief"))

# Example 1: Move a single cell
print("\n3. Moving cell 1 (imports) to position 0...")
result = manager.move_cell(1, 0)
print(result)

print("\nNotebook structure after move:")
print(manager.read_notebook("reorder_demo", response_format="brief"))

# Example 2: Swap two cells
print("\n4. Swapping cells 2 and 3...")
result = manager.swap_cells(2, 3)
print(result)

print("\nNotebook structure after swap:")
print(manager.read_notebook("reorder_demo", response_format="brief"))

# Example 3: Reorder all cells
print("\n5. Reordering all cells to: [markdown, imports, DataFrame, data, describe]")
print("   Original indices: [0, 1, 2, 3, 4]")
print("   New order:        [1, 0, 3, 2, 4]")

# Reset notebook first
manager.unuse_notebook("reorder_demo")
manager.use_notebook("reorder_demo", "reorder_demo.ipynb", mode="create")

manager.insert_cell(0, "markdown", "# Data Analysis Workflow")
manager.insert_cell(1, "code", "import pandas as pd\nimport numpy as np")
manager.insert_cell(2, "code", "data = {'x': [1,2,3,4,5], 'y': [2,4,6,8,10]}")
manager.insert_cell(3, "code", "df = pd.DataFrame(data)")
manager.insert_cell(4, "code", "print(df.describe())")

result = manager.reorder_cells([1, 0, 3, 2, 4])
print(result)

print("\nNotebook structure after reordering:")
print(manager.read_notebook("reorder_demo", response_format="brief"))

# Example 4: Reverse the order of cells
print("\n6. Reversing the order of all cells...")
result = manager.reorder_cells([4, 3, 2, 1, 0])
print(result)

print("\nNotebook structure after reversing:")
print(manager.read_notebook("reorder_demo", response_format="brief"))

# Example 5: Practical use case - reorganize notebook sections
print("\n7. Practical example: Reorganizing notebook sections...")

# Create a more complex notebook
manager.unuse_notebook("reorder_demo")
manager.use_notebook("complex", "complex.ipynb", mode="create")

# Add cells in random order
sections = [
    ("markdown", "# Results"),
    ("code", "print('Result:', result)"),
    ("markdown", "# Setup"),
    ("code", "import matplotlib.pyplot as plt"),
    ("markdown", "# Data Loading"),
    ("code", "df = pd.read_csv('data.csv')"),
    ("markdown", "# Analysis"),
    ("code", "result = df.mean()"),
]

for idx, (cell_type, source) in enumerate(sections):
    manager.insert_cell(idx, cell_type, source)

print("\nInitial structure (random order):")
print(manager.read_notebook("complex", response_format="brief"))

# Reorder to logical flow: Setup → Data Loading → Analysis → Results
# Original: [Results, result, Setup, imports, Data Loading, read_csv, Analysis, mean]
# Indices:  [0,       1,      2,     3,       4,            5,        6,        7]
# Desired:  [2,       3,      4,     5,       6,            7,        0,        1]
new_order = [2, 3, 4, 5, 6, 7, 0, 1]

print(f"\nReorganizing to logical flow with order: {new_order}")
result = manager.reorder_cells(new_order)
print(result)

print("\nFinal structure (logical order):")
print(manager.read_notebook("complex", response_format="brief"))

# Example 6: Using move_cell for incremental changes
print("\n8. Incremental organization with move_cell...")
print("   Moving 'Results' section to the end...")

# Find Results header (now at index 0 after previous reorder)
# Move it to position 6 (before the final code cell)
result = manager.move_cell(6, 7)  # Actually it's at 6 now, move to 7
print(result)

print("\nFinal notebook structure:")
print(manager.read_notebook("complex", response_format="detailed", limit=10))

# Clean up
print("\n9. Cleaning up...")
manager.unuse_notebook("reorder_demo")
manager.unuse_notebook("complex")

print("\n=== Cell Reordering Examples Complete ===")
print("\nKey takeaways:")
print("- move_cell: Move a single cell from one position to another")
print("- swap_cells: Swap two cells quickly")
print("- reorder_cells: Reorganize entire notebook in one operation")
print("- All operations save changes immediately")
print("- Changes persist when notebook is closed and reopened")
