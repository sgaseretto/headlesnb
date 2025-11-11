"""Example of managing multiple notebooks simultaneously"""

from headlesnb import NotebookManager

# Create a notebook manager
manager = NotebookManager(root_path=".")

print("=== Managing Multiple Notebooks ===\n")

# Create two notebooks
print("1. Creating two notebooks...")
manager.use_notebook("data_prep", "data_prep.ipynb", mode="create")
manager.use_notebook("analysis", "analysis.ipynb", mode="create")

# List all notebooks
print("\n2. Listing all notebooks:")
print(manager.list_notebooks())

# Work with the first notebook (currently active)
print("\n3. Working with 'analysis' notebook:")
manager.insert_cell(0, "code", "import numpy as np")
manager.insert_cell(1, "code", "data = np.array([1, 2, 3, 4, 5])")
manager.insert_cell(2, "code", "mean = data.mean()\nprint(f'Mean: {mean}')")

manager.execute_cell(0)
manager.execute_cell(1)
outputs = manager.execute_cell(2)
print("Analysis output:", outputs)

# Switch to the other notebook
print("\n4. Switching to 'data_prep' notebook:")
result = manager.set_active_notebook("data_prep")
print(result)

# Work with the second notebook
print("\n5. Working with 'data_prep' notebook:")
manager.insert_cell(0, "code", "import pandas as pd")
manager.insert_cell(1, "code", "raw_data = [10, 20, 30, 40, 50]")
manager.insert_cell(2, "code", "df = pd.DataFrame({'values': raw_data})\nprint(df)")

manager.execute_cell(0)
manager.execute_cell(1)
outputs = manager.execute_cell(2)
print("Data prep output:", outputs)

# List kernels to see both are running
print("\n6. Listing all kernels:")
print(manager.list_kernels())

# Switch back to analysis
print("\n7. Switching back to 'analysis' notebook:")
manager.set_active_notebook("analysis")

# Add more analysis
outputs = manager.execute_code("std = data.std()\nprint(f'Std Dev: {std}')")
print("Additional analysis:", outputs)

# Read both notebooks
print("\n8. Reading 'analysis' notebook (brief):")
print(manager.read_notebook("analysis", response_format="brief"))

print("\n9. Reading 'data_prep' notebook (brief):")
print(manager.read_notebook("data_prep", response_format="brief"))

# Clean up
print("\n10. Cleaning up:")
manager.unuse_notebook("analysis")
manager.unuse_notebook("data_prep")

print("\n11. Final notebook list:")
print(manager.list_notebooks())

print("\n=== Multi-Notebook Example Complete ===")
