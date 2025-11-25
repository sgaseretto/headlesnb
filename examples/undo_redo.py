"""Example demonstrating undo/redo functionality"""

from headlesnb import NotebookManager

# Create a notebook manager
manager = NotebookManager(root_path=".")

print("=== Undo/Redo Examples ===\n")

# ==================== Example 1: Basic Undo/Redo ====================
print("1. Creating a notebook and performing operations...")
manager.use_notebook("undo_demo", "undo_demo.ipynb", mode="create")

# Add some cells
manager.insert_cell(0, "code", "a = 1")
manager.insert_cell(1, "code", "b = 2")
manager.insert_cell(2, "code", "c = 3")

print("\nInitial notebook:")
print(manager.read_notebook("undo_demo", response_format="brief"))

# Undo the last insert
print("\n2. Undoing last cell insertion...")
result = manager.undo()
print(result)
print("\nNotebook after undo:")
print(manager.read_notebook("undo_demo", response_format="brief"))

# Redo the insert
print("\n3. Redoing the operation...")
result = manager.redo()
print(result)
print("\nNotebook after redo:")
print(manager.read_notebook("undo_demo", response_format="brief"))

# ==================== Example 2: Multiple Undo/Redo ====================
print("\n\n4. Performing multiple operations...")
manager.overwrite_cell_source(1, "b = 20")
manager.move_cell(2, 0)
manager.insert_cell(3, "code", "d = 4")

print("\nNotebook state:")
print(manager.read_notebook("undo_demo", response_format="brief"))

# Undo last 3 operations
print("\n5. Undoing last 3 operations...")
result = manager.undo(steps=3)
print(result)
print("\nNotebook after undo:")
print(manager.read_notebook("undo_demo", response_format="brief"))

# Redo 2 operations
print("\n6. Redoing 2 operations...")
result = manager.redo(steps=2)
print(result)
print("\nNotebook after redo:")
print(manager.read_notebook("undo_demo", response_format="brief"))

# ==================== Example 3: View History ====================
print("\n\n7. Viewing operation history...")
history = manager.get_history()
print(history)

# ==================== Example 4: Complex Scenario ====================
print("\n\n8. Complex workflow with undo/redo...")

# Reset notebook
manager.unuse_notebook("undo_demo")
manager.use_notebook("complex", "complex.ipynb", mode="create")

# Add 5 cells
print("   Adding 5 cells...")
for i in range(5):
    manager.insert_cell(i, "code", f"cell_{i} = {i}")

# Rearrange twice
print("   Rearranging cells (1st time - reverse)...")
manager.reorder_cells([4, 3, 2, 1, 0])

print("   Rearranging cells (2nd time - swap first two)...")
manager.reorder_cells([1, 0, 2, 3, 4])

# Add 2 more cells
print("   Adding 2 more cells...")
manager.insert_cell(5, "code", "extra_1 = 10")
manager.insert_cell(6, "code", "extra_2 = 20")

# Move last cell to first
print("   Moving last cell to first position...")
manager.move_cell(6, 0)

print("\nNotebook state before undo:")
print(manager.read_notebook("complex", response_format="brief"))

# Undo 3 times (will undo: move, insert extra_2, insert extra_1)
print("\n9. Undoing last 3 operations...")
result = manager.undo(steps=3)
print(result)

print("\nNotebook state after undo (should have 5 cells with 2nd rearrangement):")
print(manager.read_notebook("complex", response_format="brief"))

# ==================== Example 5: Redo Stack Cleared ====================
print("\n\n10. Demonstrating redo stack clearing...")

# Currently have 3 operations in redo stack
print("   Current redo stack has 3 operations")

# Perform a new operation
print("   Performing new operation (insert cell)...")
manager.insert_cell(5, "code", "new_cell = 99")

# Try to redo - should fail because redo stack was cleared
print("\n11. Trying to redo after new operation...")
result = manager.redo()
print(result)

# ==================== Example 6: Overwrite with Undo ====================
print("\n\n12. Testing overwrite undo...")
manager.unuse_notebook("complex")
manager.use_notebook("overwrite_test", "overwrite_test.ipynb", mode="create")

# Add a cell
manager.insert_cell(0, "code", "original = 'first version'")
print("Original cell content:")
print(manager.read_notebook("overwrite_test", response_format="detailed", limit=1))

# Overwrite it multiple times
manager.overwrite_cell_source(0, "original = 'second version'")
manager.overwrite_cell_source(0, "original = 'third version'")
manager.overwrite_cell_source(0, "original = 'fourth version'")

print("\nAfter 3 overwrites:")
print(manager.read_notebook("overwrite_test", response_format="detailed", limit=1))

# Undo all overwrites
print("\n13. Undoing all 3 overwrites...")
manager.undo(steps=3)

print("\nAfter undoing overwrites (should be back to first version):")
print(manager.read_notebook("overwrite_test", response_format="detailed", limit=1))

# ==================== Example 7: Delete and Undo ====================
print("\n\n14. Testing delete with undo...")
manager.unuse_notebook("overwrite_test")
manager.use_notebook("delete_test", "delete_test.ipynb", mode="create")

# Add multiple cells
for i in range(5):
    manager.insert_cell(i, "markdown", f"# Section {i+1}")
    manager.insert_cell(i*2+1, "code", f"data_{i} = {i * 10}")

print("Notebook with 10 cells:")
print(manager.read_notebook("delete_test", response_format="brief"))

# Delete some cells
print("\n15. Deleting cells at indices [2, 5, 8]...")
result = manager.delete_cell([8, 5, 2], include_source=True)
print(result)

print("\nAfter deletion:")
print(manager.read_notebook("delete_test", response_format="brief"))

# Undo deletion
print("\n16. Undoing deletion...")
result = manager.undo()
print(result)

print("\nAfter undo (cells restored):")
print(manager.read_notebook("delete_test", response_format="brief"))

# ==================== Example 8: Clear History ====================
print("\n\n17. Clearing history...")
print("   Current history:")
print(manager.get_history())

print("\n   Clearing history...")
result = manager.clear_history()
print(result)

print("\n   History after clear:")
print(manager.get_history())

print("\n   Trying to undo (should fail)...")
result = manager.undo()
print(result)

# Clean up
print("\n\n18. Cleaning up...")
manager.unuse_notebook("undo_demo")
manager.unuse_notebook("complex")
manager.unuse_notebook("overwrite_test")
manager.unuse_notebook("delete_test")

print("\n=== Undo/Redo Examples Complete ===")
print("\nKey takeaways:")
print("- undo(steps=N): Undo the last N operations")
print("- redo(steps=N): Redo the last N undone operations")
print("- get_history(): View operation history")
print("- clear_history(): Clear all undo/redo history")
print("- Redo stack is cleared when a new operation is performed")
print("- Each notebook has its own independent history")
print("- Operations tracked: insert, delete, overwrite, move, swap, reorder")
print("- Cell execution is NOT tracked in history")
