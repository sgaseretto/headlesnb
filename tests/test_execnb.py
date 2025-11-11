"""Unit tests for execnb components"""

import pytest
import tempfile
import shutil
from pathlib import Path

from execnb.nbio import (
    new_nb, mk_cell, read_nb, write_nb,
    nb2dict, dict2nb, NbCell
)
from execnb.shell import CaptureShell, out_exec, out_stream, out_error


class TestNbIO:
    """Test cases for notebook I/O operations"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    def test_new_nb(self):
        """Test creating a new notebook"""
        nb = new_nb()
        assert hasattr(nb, 'cells')
        assert hasattr(nb, 'metadata')
        assert len(nb.cells) == 0

    def test_mk_cell_code(self):
        """Test creating a code cell"""
        cell = mk_cell("print('test')", cell_type='code')
        assert cell.cell_type == 'code'
        assert cell.source == "print('test')"
        assert 'outputs' in cell
        assert 'execution_count' in cell

    def test_mk_cell_markdown(self):
        """Test creating a markdown cell"""
        cell = mk_cell("# Title", cell_type='markdown')
        assert cell.cell_type == 'markdown'
        assert cell.source == "# Title"
        assert 'outputs' not in cell

    def test_mk_cell_invalid_type(self):
        """Test error with invalid cell type"""
        with pytest.raises(AssertionError):
            mk_cell("test", cell_type='invalid')

    def test_write_and_read_nb(self, temp_dir):
        """Test writing and reading a notebook"""
        nb = new_nb()
        nb.cells.append(mk_cell("x = 1", cell_type='code'))
        nb.cells.append(mk_cell("# Header", cell_type='markdown'))

        nb_path = temp_dir / "test.ipynb"
        write_nb(nb, nb_path)

        assert nb_path.exists()

        # Read it back
        nb2 = read_nb(nb_path)
        assert len(nb2.cells) == 2
        assert nb2.cells[0].source == "x = 1"
        assert nb2.cells[1].source == "# Header"

    def test_nb2dict(self):
        """Test converting notebook to dict"""
        nb = new_nb()
        nb.cells.append(mk_cell("test", cell_type='code'))

        d = nb2dict(nb)
        assert isinstance(d, dict)
        assert 'cells' in d
        assert 'metadata' in d

    def test_dict2nb(self):
        """Test converting dict to notebook"""
        d = {
            'cells': [
                {'cell_type': 'code', 'source': 'test', 'metadata': {}, 'outputs': [], 'execution_count': 0}
            ],
            'metadata': {},
            'nbformat': 4,
            'nbformat_minor': 5
        }

        nb = dict2nb(d)
        assert len(nb.cells) == 1
        assert isinstance(nb.cells[0], NbCell)

    def test_nbcell_set_source(self):
        """Test setting cell source"""
        cell = mk_cell("original", cell_type='code')
        assert cell.source == "original"

        cell.set_source("updated")
        assert cell.source == "updated"

    def test_nbcell_parsed(self):
        """Test parsing cell source"""
        cell = mk_cell("x = 1\ny = 2", cell_type='code')
        parsed = cell.parsed_()

        assert parsed is not None
        assert len(parsed) == 2  # Two statements

    def test_nbcell_parsed_magic(self):
        """Test parsing cell with magic command"""
        cell = mk_cell("%pwd", cell_type='code')
        parsed = cell.parsed_()

        # Magic commands shouldn't be parsed
        assert parsed is None

    def test_nbcell_equality(self):
        """Test cell equality"""
        cell1 = mk_cell("test", cell_type='code')
        cell2 = mk_cell("test", cell_type='code')
        cell3 = mk_cell("different", cell_type='code')

        assert cell1 == cell2
        assert cell1 != cell3


class TestCaptureShell:
    """Test cases for CaptureShell"""

    @pytest.fixture
    def shell(self):
        """Create a CaptureShell instance"""
        return CaptureShell()

    def test_shell_initialization(self, shell):
        """Test shell initialization"""
        assert shell is not None
        assert hasattr(shell, 'run')
        assert hasattr(shell, 'run_cell')

    def test_run_simple_code(self, shell):
        """Test running simple code"""
        outputs = shell.run("print('Hello')")
        assert len(outputs) > 0

        text = out_stream(outputs)
        assert "Hello" in text

    def test_run_with_result(self, shell):
        """Test running code with result"""
        outputs = shell.run("2 + 2")
        result = out_exec(outputs)
        assert "4" in result

    def test_run_with_error(self, shell):
        """Test running code with error"""
        outputs = shell.run("raise ValueError('test error')")
        error = out_error(outputs)
        assert "ValueError" in error
        assert "test error" in error

    def test_run_multiline(self, shell):
        """Test running multiline code"""
        code = """
x = 10
y = 20
print(x + y)
"""
        outputs = shell.run(code)
        text = out_stream(outputs)
        assert "30" in text

    def test_run_with_variables(self, shell):
        """Test variable persistence"""
        shell.run("var1 = 100")
        outputs = shell.run("print(var1)")
        text = out_stream(outputs)
        assert "100" in text

    def test_restart_kernel(self, shell):
        """Test kernel restart"""
        # Set a variable
        shell.run("restart_test = 'value'")

        # Restart
        shell.restart_kernel()

        # Variable should be gone
        outputs = shell.run("print(restart_test)")
        error = out_error(outputs)
        assert error is not None  # Should have NameError

    def test_stop_execution(self, shell):
        """Test stopping execution"""
        shell.stop_execution()
        # Next execution should be stopped
        try:
            outputs = shell.run("print('test')")
            # Should get a KeyboardInterrupt
            error = out_error(outputs)
            assert error is not None or "stopped" in str(outputs).lower()
        except KeyboardInterrupt:
            pass  # Expected

    def test_run_with_timeout(self, shell):
        """Test execution timeout"""
        with pytest.raises(TimeoutError):
            # This should timeout (sleep for 5 seconds with 1 second timeout)
            shell.run("import time; time.sleep(5)", timeout=1)

    def test_complete(self, shell):
        """Test code completion"""
        shell.run("import math")
        completions = shell.complete("math.")
        assert len(completions) > 0
        assert "sqrt" in completions

    def test_magic_command(self, shell):
        """Test magic command execution"""
        outputs = shell.run("%pwd")
        assert len(outputs) > 0

    def test_shell_command(self, shell):
        """Test shell command execution"""
        outputs = shell.run("!echo 'test'")
        text = out_stream(outputs)
        assert "test" in text

    def test_quiet_output(self, shell):
        """Test quiet output with semicolon"""
        outputs = shell.run("x = 5;")
        # Should not have output for the assignment
        assert len(outputs) == 0 or out_exec(outputs) is None

    def test_display_output(self, shell):
        """Test display output"""
        outputs = shell.run("from IPython.display import HTML; HTML('<b>test</b>')")
        # Should have display data
        assert len(outputs) > 0

    def test_exception_traceback(self, shell):
        """Test exception traceback"""
        outputs = shell.run("def foo():\n    raise RuntimeError('test')\nfoo()")
        error = out_error(outputs)
        assert "RuntimeError" in error
        assert "test" in error
        assert "foo" in error  # Function name should be in traceback


class TestOutputFormatting:
    """Test cases for output formatting functions"""

    @pytest.fixture
    def shell(self):
        """Create a CaptureShell instance"""
        return CaptureShell()

    def test_out_exec(self, shell):
        """Test extracting execution result"""
        outputs = shell.run("42")
        result = out_exec(outputs)
        assert "42" in result

    def test_out_exec_none(self, shell):
        """Test extraction when no execution result"""
        outputs = shell.run("x = 5")
        result = out_exec(outputs)
        assert result is None

    def test_out_stream(self, shell):
        """Test extracting stream output"""
        outputs = shell.run("print('stream test')")
        text = out_stream(outputs)
        assert "stream test" in text

    def test_out_stream_none(self):
        """Test extraction when no stream output"""
        outputs = []
        text = out_stream(outputs)
        assert text is None

    def test_out_error(self, shell):
        """Test extracting error output"""
        outputs = shell.run("1 / 0")
        error = out_error(outputs)
        assert "ZeroDivisionError" in error

    def test_out_error_none(self, shell):
        """Test extraction when no error"""
        outputs = shell.run("print('ok')")
        error = out_error(outputs)
        assert error is None

    def test_multiple_outputs(self, shell):
        """Test handling multiple outputs"""
        code = """
print('First')
print('Second')
42
"""
        outputs = shell.run(code)
        text = out_stream(outputs)
        result = out_exec(outputs)

        assert "First" in text
        assert "Second" in text
        assert "42" in result
