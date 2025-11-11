"""Example of file system operations"""

from headlesnb import NotebookManager
from pathlib import Path

# Create a notebook manager
manager = NotebookManager(root_path=".")

print("=== File System Operations ===\n")

# Create some test directories and files
print("1. Creating test structure...")
test_dir = Path("test_files")
test_dir.mkdir(exist_ok=True)
(test_dir / "data").mkdir(exist_ok=True)
(test_dir / "notebooks").mkdir(exist_ok=True)

# Create some test files
(test_dir / "readme.txt").write_text("Test readme file")
(test_dir / "data" / "dataset1.csv").write_text("col1,col2\n1,2\n3,4")
(test_dir / "data" / "dataset2.csv").write_text("col1,col2\n5,6\n7,8")

# Create a test notebook
from execnb.nbio import new_nb, write_nb, mk_cell
nb = new_nb()
nb.cells.append(mk_cell("print('Test')", cell_type='code'))
write_nb(nb, test_dir / "notebooks" / "test.ipynb")

# List files at different depths
print("\n2. Listing files (depth=0, current directory only):")
result = manager.list_files(path="test_files", max_depth=0, limit=10)
print(result)

print("\n3. Listing files (depth=1, including subdirectories):")
result = manager.list_files(path="test_files", max_depth=1, limit=20)
print(result)

print("\n4. Listing files (depth=2, full tree):")
result = manager.list_files(path="test_files", max_depth=2, limit=50)
print(result)

# Filter by pattern
print("\n5. Listing only CSV files:")
result = manager.list_files(path="test_files", pattern="*.csv", max_depth=2)
print(result)

print("\n6. Listing only notebook files:")
result = manager.list_files(path="test_files", pattern="*.ipynb", max_depth=2)
print(result)

# Pagination example
print("\n7. Pagination example (limit=2, start_index=0):")
result = manager.list_files(path="test_files", max_depth=2, limit=2, start_index=0)
print(result)

print("\n8. Pagination example (limit=2, start_index=2):")
result = manager.list_files(path="test_files", max_depth=2, limit=2, start_index=2)
print(result)

# List all files (no limit)
print("\n9. Listing all files (no limit):")
result = manager.list_files(path="test_files", max_depth=2, limit=0)
print(result)

# Clean up
print("\n10. Cleaning up test structure...")
import shutil
shutil.rmtree(test_dir)

print("\n=== File Operations Example Complete ===")
