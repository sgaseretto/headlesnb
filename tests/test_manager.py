"""Unit tests for NotebookManager"""

import pytest
import tempfile
import shutil
from pathlib import Path

from headlesnb.manager import NotebookManager
from execnb.nbio import new_nb, write_nb, mk_cell


class TestNotebookManager:
    """Test cases for NotebookManager"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a NotebookManager instance"""
        return NotebookManager(root_path=str(temp_dir))

    @pytest.fixture
    def sample_notebook(self, temp_dir):
        """Create a sample notebook for testing"""
        nb = new_nb()
        nb.cells.append(mk_cell("print('Hello, World!')", cell_type='code'))
        nb.cells.append(mk_cell("# Test Notebook", cell_type='markdown'))
        nb.cells.append(mk_cell("x = 42\nprint(x)", cell_type='code'))

        nb_path = temp_dir / "test_notebook.ipynb"
        write_nb(nb, nb_path)
        return nb_path

    # ================== Server Management Tools Tests ==================

    def test_list_files_empty_directory(self, manager, temp_dir):
        """Test listing files in an empty directory"""
        result = manager.list_files()
        assert "Showing" in result
        assert "Path\tType\tSize\tLast_Modified" in result

    def test_list_files_with_notebooks(self, manager, sample_notebook):
        """Test listing files with notebooks"""
        result = manager.list_files()
        assert "test_notebook.ipynb" in result
        assert "notebook" in result

    def test_list_files_with_pattern(self, manager, sample_notebook):
        """Test listing files with glob pattern"""
        result = manager.list_files(pattern="*.ipynb")
        assert "test_notebook.ipynb" in result

    def test_list_files_pagination(self, manager, temp_dir):
        """Test file listing pagination"""
        # Create multiple files
        for i in range(30):
            (temp_dir / f"file_{i}.txt").touch()

        result = manager.list_files(limit=10, start_index=0)
        assert "Showing 1-10 of" in result

        result = manager.list_files(limit=10, start_index=10)
        assert "Showing 11-20 of" in result

    def test_list_kernels_empty(self, manager):
        """Test listing kernels when none are active"""
        result = manager.list_kernels()
        assert "ID\tName\tDisplay_Name" in result
        assert "(No active kernels)" in result

    def test_list_kernels_with_notebooks(self, manager, sample_notebook):
        """Test listing kernels with active notebooks"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.list_kernels()
        assert "test" in result
        assert "python" in result
        assert "idle" in result

    # ================== Multi-Notebook Management Tests ==================

    def test_use_notebook_connect(self, manager, sample_notebook):
        """Test connecting to an existing notebook"""
        result = manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        assert "✓ Notebook 'test' activated successfully" in result
        assert "test" in manager.notebooks
        assert manager.active_notebook == "test"

    def test_use_notebook_create(self, manager, temp_dir):
        """Test creating a new notebook"""
        nb_path = "new_notebook.ipynb"
        result = manager.use_notebook("new", nb_path, mode="create")
        assert "✓ Notebook 'new' activated successfully" in result
        assert (temp_dir / nb_path).exists()
        assert "new" in manager.notebooks

    def test_use_notebook_already_in_use(self, manager, sample_notebook):
        """Test error when notebook is already in use"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        assert "Error" in result
        assert "already in use" in result

    def test_use_notebook_not_found(self, manager):
        """Test error when notebook file doesn't exist"""
        result = manager.use_notebook("test", "nonexistent.ipynb", mode="connect")
        assert "Error" in result
        assert "not found" in result

    def test_list_notebooks_empty(self, manager):
        """Test listing notebooks when none are in use"""
        result = manager.list_notebooks()
        assert "Name\tPath\tKernel_ID" in result
        assert "(No notebooks in use)" in result

    def test_list_notebooks_with_active(self, manager, sample_notebook):
        """Test listing notebooks with active notebook"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.list_notebooks()
        assert "test" in result
        assert "✓" in result  # Active marker

    def test_restart_notebook(self, manager, sample_notebook):
        """Test restarting a notebook's kernel"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")

        # Execute some code to set a variable
        manager.execute_code("test_var = 123")

        # Restart the kernel
        result = manager.restart_notebook("test")
        assert "✓ Kernel for notebook 'test' restarted successfully" in result

        # Verify variable is gone (should error)
        outputs = manager.execute_code("print(test_var)")
        # Should have an error output
        assert any("error" in str(o).lower() or "NameError" in str(o) for o in outputs)

    def test_restart_notebook_not_found(self, manager):
        """Test error when restarting non-existent notebook"""
        result = manager.restart_notebook("nonexistent")
        assert "Error" in result
        assert "not found" in result

    def test_unuse_notebook(self, manager, sample_notebook):
        """Test disconnecting from a notebook"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.unuse_notebook("test")
        assert "✓ Notebook 'test' disconnected successfully" in result
        assert "test" not in manager.notebooks

    def test_unuse_notebook_switches_active(self, manager, sample_notebook, temp_dir):
        """Test that active notebook switches when current is closed"""
        # Create two notebooks
        nb2_path = temp_dir / "notebook2.ipynb"
        nb2 = new_nb()
        write_nb(nb2, nb2_path)

        manager.use_notebook("nb1", str(sample_notebook.name), mode="connect")
        manager.use_notebook("nb2", "notebook2.ipynb", mode="connect")

        # Close the active notebook
        manager.unuse_notebook("nb2")
        assert manager.active_notebook == "nb1"

    def test_read_notebook_brief(self, manager, sample_notebook):
        """Test reading notebook in brief format"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.read_notebook("test", response_format="brief")
        assert "Index\tType\tExec_Count\tFirst_Line\tLines" in result
        assert "print('Hello, World!')" in result
        assert "# Test Notebook" in result

    def test_read_notebook_detailed(self, manager, sample_notebook):
        """Test reading notebook in detailed format"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.read_notebook("test", response_format="detailed")
        assert "Cell [0]" in result
        assert "print('Hello, World!')" in result
        assert "x = 42" in result

    def test_read_notebook_pagination(self, manager, sample_notebook):
        """Test reading notebook with pagination"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.read_notebook("test", start_index=0, limit=1)
        assert "Showing cells 0-0 of 3" in result

    # ================== Cell Tools Tests ==================

    def test_insert_cell_code(self, manager, sample_notebook):
        """Test inserting a code cell"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.insert_cell(0, "code", "y = 100")
        assert "✓ Cell inserted at index 0" in result
        assert "Type: code" in result

        # Verify cell was inserted
        nb = manager.notebooks["test"].notebook
        assert len(nb.cells) == 4
        assert nb.cells[0].source == "y = 100"

    def test_insert_cell_markdown(self, manager, sample_notebook):
        """Test inserting a markdown cell"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.insert_cell(1, "markdown", "## New Section")
        assert "✓ Cell inserted at index 1" in result
        assert "Type: markdown" in result

    def test_insert_cell_append(self, manager, sample_notebook):
        """Test appending a cell at the end"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.insert_cell(-1, "code", "z = 200")
        assert "✓ Cell inserted" in result

        nb = manager.notebooks["test"].notebook
        assert nb.cells[-1].source == "z = 200"

    def test_insert_cell_no_active(self, manager):
        """Test error when no active notebook"""
        result = manager.insert_cell(0, "code", "test")
        assert "Error" in result
        assert "No active notebook" in result

    def test_overwrite_cell_source(self, manager, sample_notebook):
        """Test overwriting a cell's source"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.overwrite_cell_source(0, "print('Updated!')")
        assert "✓ Cell [0] source overwritten" in result
        assert "Diff:" in result

        # Verify cell was updated
        nb = manager.notebooks["test"].notebook
        assert nb.cells[0].source == "print('Updated!')"

    def test_overwrite_cell_invalid_index(self, manager, sample_notebook):
        """Test error when overwriting with invalid index"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.overwrite_cell_source(100, "test")
        assert "Error" in result
        assert "out of range" in result

    def test_execute_cell(self, manager, sample_notebook):
        """Test executing a cell"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        outputs = manager.execute_cell(0, timeout=10)

        # Should have output
        assert len(outputs) > 0
        # Should contain "Hello, World!"
        output_text = " ".join(str(o) for o in outputs)
        assert "Hello, World!" in output_text

    def test_execute_cell_with_error(self, manager, sample_notebook):
        """Test executing a cell that raises an error"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        manager.insert_cell(0, "code", "raise ValueError('Test error')")
        outputs = manager.execute_cell(0, timeout=10)

        # Should have error output
        output_text = " ".join(str(o) for o in outputs)
        assert "ValueError" in output_text or "ERROR" in output_text

    def test_execute_cell_non_code(self, manager, sample_notebook):
        """Test error when executing non-code cell"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        outputs = manager.execute_cell(1, timeout=10)  # Markdown cell

        # Should have error
        assert any("Error" in str(o) for o in outputs)

    def test_insert_execute_code_cell(self, manager, sample_notebook):
        """Test inserting and executing a code cell"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        outputs = manager.insert_execute_code_cell(0, "result = 5 + 5\nprint(result)", timeout=10)

        # Should have insertion message and output
        assert len(outputs) > 0
        output_text = " ".join(str(o) for o in outputs)
        assert "Cell inserted" in output_text
        assert "10" in output_text

    def test_read_cell(self, manager, sample_notebook):
        """Test reading a specific cell"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        outputs = manager.read_cell(0, include_outputs=True)

        output_text = " ".join(str(o) for o in outputs)
        assert "Cell [0]" in output_text
        assert "print('Hello, World!')" in output_text

    def test_read_cell_without_outputs(self, manager, sample_notebook):
        """Test reading a cell without outputs"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        outputs = manager.read_cell(0, include_outputs=False)

        output_text = " ".join(str(o) for o in outputs)
        assert "Cell [0]" in output_text
        # Should not have outputs section if not executed
        assert "print('Hello, World!')" in output_text

    def test_delete_cell_single(self, manager, sample_notebook):
        """Test deleting a single cell"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.delete_cell([0], include_source=True)

        assert "✓ Deleted 1 cell(s): [0]" in result
        assert "print('Hello, World!')" in result

        # Verify cell was deleted
        nb = manager.notebooks["test"].notebook
        assert len(nb.cells) == 2

    def test_delete_cell_multiple(self, manager, sample_notebook):
        """Test deleting multiple cells"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.delete_cell([0, 2], include_source=True)

        assert "✓ Deleted 2 cell(s):" in result

        # Verify cells were deleted
        nb = manager.notebooks["test"].notebook
        assert len(nb.cells) == 1

    def test_delete_cell_invalid_index(self, manager, sample_notebook):
        """Test error when deleting with invalid index"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.delete_cell([100], include_source=True)

        assert "Error" in result
        assert "Invalid cell indices" in result

    def test_execute_code(self, manager, sample_notebook):
        """Test executing code directly"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        outputs = manager.execute_code("print('Direct execution')", timeout=10)

        output_text = " ".join(str(o) for o in outputs)
        assert "Direct execution" in output_text

    def test_execute_code_magic_command(self, manager, sample_notebook):
        """Test executing magic command"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        outputs = manager.execute_code("%pwd", timeout=10)

        # Should return current directory
        assert len(outputs) > 0

    def test_execute_code_shell_command(self, manager, sample_notebook):
        """Test executing shell command"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        outputs = manager.execute_code("!echo 'test'", timeout=10)

        output_text = " ".join(str(o) for o in outputs)
        assert "test" in output_text

    # ================== Additional Tools Tests ==================

    def test_stop_execution(self, manager, sample_notebook):
        """Test stopping execution"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        result = manager.stop_execution()
        assert "✓ Execution stop requested" in result

    def test_set_active_notebook(self, manager, sample_notebook, temp_dir):
        """Test setting active notebook"""
        # Create two notebooks
        nb2_path = temp_dir / "notebook2.ipynb"
        nb2 = new_nb()
        write_nb(nb2, nb2_path)

        manager.use_notebook("nb1", str(sample_notebook.name), mode="connect")
        manager.use_notebook("nb2", "notebook2.ipynb", mode="connect")

        # Set nb1 as active
        result = manager.set_active_notebook("nb1")
        assert "✓ Notebook 'nb1' is now active" in result
        assert manager.active_notebook == "nb1"

    def test_set_active_notebook_not_found(self, manager):
        """Test error when setting non-existent notebook as active"""
        result = manager.set_active_notebook("nonexistent")
        assert "Error" in result
        assert "not found" in result

    def test_get_active_notebook(self, manager, sample_notebook):
        """Test getting active notebook name"""
        manager.use_notebook("test", str(sample_notebook.name), mode="connect")
        assert manager.get_active_notebook() == "test"

    # ================== Integration Tests ==================

    def test_full_workflow(self, manager, temp_dir):
        """Test a full workflow of notebook operations"""
        # Create a new notebook
        result = manager.use_notebook("workflow", "workflow.ipynb", mode="create")
        assert "✓" in result

        # Insert some cells
        manager.insert_cell(0, "code", "import math")
        manager.insert_cell(1, "code", "x = 10")
        manager.insert_cell(2, "code", "y = math.sqrt(x)")
        manager.insert_cell(3, "code", "print(f'Result: {y}')")

        # Execute cells
        manager.execute_cell(0)
        manager.execute_cell(1)
        manager.execute_cell(2)
        outputs = manager.execute_cell(3)

        output_text = " ".join(str(o) for o in outputs)
        assert "Result:" in output_text

        # Read the notebook
        result = manager.read_notebook("workflow", response_format="brief")
        assert "import math" in result

        # Restart and verify state is cleared
        manager.restart_notebook("workflow")
        outputs = manager.execute_code("print(x)")
        output_text = " ".join(str(o) for o in outputs)
        assert "NameError" in output_text or "error" in output_text.lower()

        # Clean up
        manager.unuse_notebook("workflow")
        assert "workflow" not in manager.notebooks

    def test_multiple_notebooks(self, manager, sample_notebook, temp_dir):
        """Test managing multiple notebooks simultaneously"""
        # Create second notebook
        nb2_path = temp_dir / "notebook2.ipynb"
        nb2 = new_nb()
        nb2.cells.append(mk_cell("a = 1", cell_type='code'))
        write_nb(nb2, nb2_path)

        # Use both notebooks
        manager.use_notebook("nb1", str(sample_notebook.name), mode="connect")
        manager.use_notebook("nb2", "notebook2.ipynb", mode="connect")

        # List notebooks
        result = manager.list_notebooks()
        assert "nb1" in result
        assert "nb2" in result

        # Execute in nb2 (currently active)
        outputs = manager.execute_code("b = a + 1\nprint(b)")
        output_text = " ".join(str(o) for o in outputs)
        assert "2" in output_text

        # Switch to nb1
        manager.set_active_notebook("nb1")

        # Execute in nb1
        outputs = manager.execute_code("print('In nb1')")
        output_text = " ".join(str(o) for o in outputs)
        assert "In nb1" in output_text

        # Clean up
        manager.unuse_notebook("nb1")
        manager.unuse_notebook("nb2")
