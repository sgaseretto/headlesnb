"""Notebook Manager for managing multiple notebooks and their execution state"""

import os
import time
import difflib
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from execnb.shell import CaptureShell
from execnb.nbio import read_nb, write_nb, new_nb, mk_cell, NbCell

from .history import (
    OperationHistory,
    InsertCellCommand,
    DeleteCellCommand,
    OverwriteCellCommand,
    MoveCellCommand,
    SwapCellsCommand,
    ReorderCellsCommand
)


@dataclass
class NotebookInfo:
    """Information about a managed notebook"""
    name: str
    path: Path
    shell: CaptureShell
    notebook: Any  # The notebook object
    kernel_id: str
    history: OperationHistory = field(default_factory=lambda: OperationHistory(max_size=100))
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = False


class NotebookManager:
    """Manager for multiple notebooks with execnb backend"""

    def __init__(self, root_path: str = "."):
        """
        Initialize the NotebookManager

        Args:
            root_path: Root path for file operations
        """
        self.root_path = Path(root_path).resolve()
        self.notebooks: Dict[str, NotebookInfo] = {}
        self.active_notebook: Optional[str] = None
        self._lock = threading.Lock()

    # ================== Server Management Tools ==================

    def list_files(
        self,
        path: str = "",
        max_depth: int = 1,
        start_index: int = 0,
        limit: int = 25,
        pattern: str = ""
    ) -> str:
        """
        List all files and directories recursively in the file system.

        Args:
            path: Starting path to list from (empty string means root directory)
            max_depth: Maximum depth to recurse into subdirectories (default: 1, max: 3)
            start_index: Starting index for pagination (0-based, default: 0)
            limit: Maximum number of items to return (0 means no limit, default: 25)
            pattern: Glob pattern to filter file paths (default: "")

        Returns:
            Tab-separated table with columns: Path, Type, Size, Last_Modified
        """
        max_depth = min(max_depth, 3)
        start_path = self.root_path / path if path else self.root_path

        if not start_path.exists():
            return f"Error: Path '{path}' does not exist"

        files = []

        def _scan_dir(current_path: Path, current_depth: int):
            if current_depth > max_depth:
                return

            try:
                for item in current_path.iterdir():
                    rel_path = item.relative_to(self.root_path)

                    # Apply pattern filter if provided
                    if pattern and not item.match(pattern):
                        continue

                    try:
                        stat = item.stat()
                        if item.is_file():
                            file_type = "notebook" if item.suffix == ".ipynb" else "file"
                            size = stat.st_size
                            size_str = self._format_size(size)
                        else:
                            file_type = "directory"
                            size_str = ""

                        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                        files.append({
                            "path": str(rel_path),
                            "type": file_type,
                            "size": size_str,
                            "modified": modified
                        })

                        # Recurse into directories
                        if item.is_dir():
                            _scan_dir(item, current_depth + 1)

                    except (PermissionError, OSError):
                        files.append({
                            "path": str(rel_path),
                            "type": "error",
                            "size": "",
                            "modified": ""
                        })
            except (PermissionError, OSError):
                pass

        _scan_dir(start_path, 0)

        # Sort by path
        files.sort(key=lambda x: x["path"])

        # Apply pagination
        total_count = len(files)
        end_index = start_index + limit if limit > 0 else total_count
        paginated_files = files[start_index:end_index]

        # Format as TSV
        header = f"Showing {start_index + 1}-{min(end_index, total_count)} of {total_count} items\n"
        header += "Path\tType\tSize\tLast_Modified"

        rows = [
            f"{f['path']}\t{f['type']}\t{f['size']}\t{f['modified']}"
            for f in paginated_files
        ]

        return header + "\n" + "\n".join(rows)

    def list_kernels(self) -> str:
        """
        List all available kernels (managed notebooks with their shells).

        Returns:
            Tab-separated table with columns: ID, Name, Display_Name, Language, State,
            Connections, Last_Activity, Environment
        """
        header = "ID\tName\tDisplay_Name\tLanguage\tState\tConnections\tLast_Activity\tEnvironment"

        if not self.notebooks:
            return header + "\n(No active kernels)"

        rows = []
        for nb_info in self.notebooks.values():
            # Determine state based on shell activity
            state = "idle"  # execnb shells are typically idle unless actively executing

            last_activity = nb_info.last_activity.strftime("%Y-%m-%d %H:%M:%S")

            rows.append(
                f"{nb_info.kernel_id}\t"
                f"{nb_info.name}\t"
                f"Python 3 (execnb)\t"
                f"python\t"
                f"{state}\t"
                f"1\t"
                f"{last_activity}\t"
                f"execnb environment"
            )

        return header + "\n" + "\n".join(rows)

    # ================== Multi-Notebook Management Tools ==================

    def use_notebook(
        self,
        notebook_name: str,
        notebook_path: str,
        mode: str = "connect",
        kernel_id: Optional[str] = None
    ) -> str:
        """
        Use a notebook and activate it for following cell operations.

        Args:
            notebook_name: Unique identifier for the notebook
            notebook_path: Path to the notebook file
            mode: "connect" to connect to existing, "create" to create new
            kernel_id: Specific kernel ID to use (will create new if skipped)

        Returns:
            Success message with notebook information
        """
        with self._lock:
            full_path = self.root_path / notebook_path

            # Check if notebook is already in use
            if notebook_name in self.notebooks:
                return f"Error: Notebook '{notebook_name}' is already in use. Use unuse_notebook first."

            # Handle create mode
            if mode == "create":
                if full_path.exists():
                    return f"Error: Notebook '{notebook_path}' already exists. Use 'connect' mode instead."
                nb = new_nb()
                write_nb(nb, full_path)
            elif mode == "connect":
                if not full_path.exists():
                    return f"Error: Notebook '{notebook_path}' not found. Use 'create' mode to create it."
                nb = read_nb(full_path)
            else:
                return f"Error: Invalid mode '{mode}'. Use 'connect' or 'create'."

            # Create shell for this notebook
            shell = CaptureShell(path=full_path.parent)

            # Generate kernel ID if not provided
            if kernel_id is None:
                kernel_id = f"kernel-{notebook_name}-{int(time.time())}"

            # Create notebook info
            nb_info = NotebookInfo(
                name=notebook_name,
                path=full_path,
                shell=shell,
                notebook=nb,
                kernel_id=kernel_id,
                is_active=True
            )

            # Store and activate
            self.notebooks[notebook_name] = nb_info
            self.active_notebook = notebook_name

            # Get notebook overview
            cell_count = len(nb.cells)
            code_cells = sum(1 for c in nb.cells if c.cell_type == 'code')
            md_cells = sum(1 for c in nb.cells if c.cell_type == 'markdown')

            return (
                f"✓ Notebook '{notebook_name}' activated successfully\n"
                f"Path: {notebook_path}\n"
                f"Kernel ID: {kernel_id}\n"
                f"Mode: {mode}\n"
                f"Cells: {cell_count} total ({code_cells} code, {md_cells} markdown)\n"
                f"Status: Active"
            )

    def list_notebooks(self) -> str:
        """
        List all notebooks that have been used via use_notebook tool.

        Returns:
            TSV formatted table with notebook information
        """
        header = "Name\tPath\tKernel_ID\tKernel_Status\tActive"

        if not self.notebooks:
            return header + "\n(No notebooks in use)"

        rows = []
        for nb_info in self.notebooks.values():
            status = "running"
            active_mark = "✓" if nb_info.is_active else ""

            rows.append(
                f"{nb_info.name}\t"
                f"{nb_info.path.relative_to(self.root_path)}\t"
                f"{nb_info.kernel_id}\t"
                f"{status}\t"
                f"{active_mark}"
            )

        return header + "\n" + "\n".join(rows)

    def restart_notebook(self, notebook_name: str) -> str:
        """
        Restart the kernel for a specific notebook.

        Args:
            notebook_name: Notebook identifier to restart

        Returns:
            Success message confirming restart
        """
        with self._lock:
            if notebook_name not in self.notebooks:
                return f"Error: Notebook '{notebook_name}' not found"

            nb_info = self.notebooks[notebook_name]
            nb_info.shell.restart_kernel()
            nb_info.last_activity = datetime.now()

            return f"✓ Kernel for notebook '{notebook_name}' restarted successfully\nMemory state cleared"

    def unuse_notebook(self, notebook_name: str) -> str:
        """
        Unuse from a specific notebook and release its resources.

        Args:
            notebook_name: Notebook identifier to disconnect

        Returns:
            Success message confirming disconnection
        """
        with self._lock:
            if notebook_name not in self.notebooks:
                return f"Error: Notebook '{notebook_name}' not found"

            nb_info = self.notebooks[notebook_name]

            # Save the notebook before disconnecting
            write_nb(nb_info.notebook, nb_info.path)

            # Remove from managed notebooks
            del self.notebooks[notebook_name]

            # Update active notebook if this was active
            if self.active_notebook == notebook_name:
                self.active_notebook = next(iter(self.notebooks.keys()), None)
                if self.active_notebook:
                    self.notebooks[self.active_notebook].is_active = True

            return f"✓ Notebook '{notebook_name}' disconnected successfully\nResources released"

    def read_notebook(
        self,
        notebook_name: str,
        response_format: str = "brief",
        start_index: int = 0,
        limit: int = 20
    ) -> str:
        """
        Read a notebook and return cell information.

        Args:
            notebook_name: Notebook identifier to read
            response_format: "brief" for overview, "detailed" for full content
            start_index: Starting index for pagination (0-based)
            limit: Maximum number of items to return (0 means no limit)

        Returns:
            Notebook content in requested format
        """
        if notebook_name not in self.notebooks:
            return f"Error: Notebook '{notebook_name}' not found"

        nb_info = self.notebooks[notebook_name]
        nb = nb_info.notebook

        total_cells = len(nb.cells)
        end_index = start_index + limit if limit > 0 else total_cells
        cells = nb.cells[start_index:end_index]

        header = (
            f"Notebook: {notebook_name}\n"
            f"Path: {nb_info.path.relative_to(self.root_path)}\n"
            f"Showing cells {start_index}-{min(end_index, total_cells) - 1} of {total_cells}\n"
            f"Format: {response_format}\n"
            f"{'-' * 80}\n"
        )

        if response_format == "brief":
            rows = ["Index\tType\tExec_Count\tFirst_Line\tLines"]
            for cell in cells:
                first_line = cell.source.split('\n')[0][:50] if cell.source else "(empty)"
                line_count = len(cell.source.split('\n'))
                exec_count = cell.get('execution_count', '') or ''

                rows.append(
                    f"{cell.idx_}\t"
                    f"{cell.cell_type}\t"
                    f"{exec_count}\t"
                    f"{first_line}\t"
                    f"{line_count}"
                )
            return header + "\n".join(rows)

        else:  # detailed
            result = [header]
            for cell in cells:
                exec_count = cell.get('execution_count', '') or ''
                result.append(
                    f"\n{'=' * 80}\n"
                    f"Cell [{cell.idx_}] - Type: {cell.cell_type}, Exec Count: {exec_count}\n"
                    f"{'-' * 80}\n"
                    f"{cell.source}\n"
                )

                # Include outputs for code cells
                if cell.cell_type == 'code' and cell.get('outputs'):
                    result.append(f"\nOutputs:\n{'-' * 40}\n")
                    for output in cell.outputs:
                        output_type = output.get('output_type', 'unknown')
                        result.append(f"[{output_type}]\n")

                        if output_type == 'stream':
                            result.append(''.join(output.get('text', [])))
                        elif output_type in ('execute_result', 'display_data'):
                            data = output.get('data', {})
                            if 'text/plain' in data:
                                result.append(''.join(data['text/plain']))
                        elif output_type == 'error':
                            result.append(''.join(output.get('traceback', [])))

                        result.append("\n")

            return "".join(result)

    # ================== Cell Tools ==================

    def insert_cell(
        self,
        cell_index: int,
        cell_type: str,
        cell_source: str
    ) -> str:
        """
        Insert a cell at specified position in the active notebook.

        Args:
            cell_index: Target index for insertion (0-based), use -1 to append
            cell_type: Type of cell ("code" or "markdown")
            cell_source: Source content for the cell

        Returns:
            Success message with surrounding cell structure
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        if cell_type not in ("code", "markdown"):
            return f"Error: Invalid cell_type '{cell_type}'. Use 'code' or 'markdown'."

        nb_info = self.notebooks[self.active_notebook]

        # Create and execute command
        command = InsertCellCommand(
            cell_index=cell_index,
            cell_type=cell_type,
            cell_source=cell_source
        )

        try:
            command.execute(self)
            nb_info.history.add_command(command)

            # Get the actual index (in case it was -1)
            actual_index = command.cell_index
            nb = nb_info.notebook

            # Get surrounding cells context
            context_start = max(0, actual_index - 2)
            context_end = min(len(nb.cells), actual_index + 3)
            context_cells = []

            for i in range(context_start, context_end):
                cell = nb.cells[i]
                marker = ">>> NEW <<<" if i == actual_index else ""
                first_line = cell.source.split('\n')[0][:40] if cell.source else "(empty)"
                context_cells.append(f"[{i}] {cell.cell_type}: {first_line} {marker}")

            context = "\n".join(context_cells)

            return (
                f"✓ Cell inserted at index {actual_index}\n"
                f"Type: {cell_type}\n"
                f"Notebook: {self.active_notebook}\n"
                f"\nSurrounding cells:\n{context}"
            )

        except Exception as e:
            return f"Error inserting cell: {str(e)}"

    def overwrite_cell_source(
        self,
        cell_index: int,
        cell_source: str
    ) -> str:
        """
        Overwrite the source of a specific cell in the active notebook.

        Args:
            cell_index: Index of the cell to overwrite (0-based)
            cell_source: New complete cell source

        Returns:
            Success message with diff-style comparison
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]
        nb = nb_info.notebook

        if cell_index < 0 or cell_index >= len(nb.cells):
            return f"Error: Cell index {cell_index} out of range (0-{len(nb.cells) - 1})"

        old_source = nb.cells[cell_index].source

        # Create and execute command
        command = OverwriteCellCommand(
            cell_index=cell_index,
            old_source=old_source,
            new_source=cell_source
        )

        try:
            command.execute(self)
            nb_info.history.add_command(command)

            # Generate diff
            diff = difflib.unified_diff(
                old_source.splitlines(keepends=True),
                cell_source.splitlines(keepends=True),
                lineterm='',
                fromfile=f'Cell [{cell_index}] (old)',
                tofile=f'Cell [{cell_index}] (new)'
            )

            diff_text = ''.join(diff)

            return (
                f"✓ Cell [{cell_index}] source overwritten\n"
                f"Notebook: {self.active_notebook}\n"
                f"\nDiff:\n{'-' * 80}\n{diff_text}"
            )

        except Exception as e:
            return f"Error overwriting cell: {str(e)}"

    def execute_cell(
        self,
        cell_index: int,
        timeout: int = 90,
        stream: bool = False,
        progress_interval: int = 5
    ) -> List[Union[str, Dict]]:
        """
        Execute a cell from the active notebook and return outputs.

        Args:
            cell_index: Index of the cell to execute (0-based)
            timeout: Maximum seconds to wait for execution
            stream: Enable streaming progress updates
            progress_interval: Seconds between progress updates

        Returns:
            List of outputs from the executed cell
        """
        if not self.active_notebook:
            return ["Error: No active notebook. Use use_notebook first."]

        nb_info = self.notebooks[self.active_notebook]
        nb = nb_info.notebook

        if cell_index < 0 or cell_index >= len(nb.cells):
            return [f"Error: Cell index {cell_index} out of range (0-{len(nb.cells) - 1})"]

        cell = nb.cells[cell_index]

        if cell.cell_type != 'code':
            return [f"Error: Cell [{cell_index}] is not a code cell (type: {cell.cell_type})"]

        # Execute the cell
        try:
            outputs = nb_info.shell.run(cell.source, timeout=timeout)

            # Store outputs in cell
            cell.outputs = outputs
            cell.execution_count = getattr(nb_info.shell, '_cell_idx', cell_index + 1)

            # Save notebook
            write_nb(nb, nb_info.path)
            nb_info.last_activity = datetime.now()

            return self._format_outputs(outputs)

        except TimeoutError:
            return [f"Error: Cell execution timed out after {timeout} seconds"]
        except KeyboardInterrupt:
            return ["Error: Cell execution was stopped by user"]
        except Exception as e:
            return [f"Error executing cell: {str(e)}"]

    def insert_execute_code_cell(
        self,
        cell_index: int,
        cell_source: str,
        timeout: int = 90
    ) -> List[Union[str, Dict]]:
        """
        Insert a code cell and execute it immediately.

        Args:
            cell_index: Index to insert the cell (0-based)
            cell_source: Code source for the cell
            timeout: Maximum seconds to wait for execution

        Returns:
            List of outputs from the executed cell
        """
        # Insert the cell
        insert_result = self.insert_cell(cell_index, "code", cell_source)

        if insert_result.startswith("Error"):
            return [insert_result]

        # Execute the newly inserted cell
        exec_result = self.execute_cell(cell_index, timeout=timeout)

        return [insert_result] + exec_result

    def read_cell(
        self,
        cell_index: int,
        include_outputs: bool = True
    ) -> List[Union[str, Dict]]:
        """
        Read a specific cell from the active notebook.

        Args:
            cell_index: Index of the cell to read (0-based)
            include_outputs: Include outputs in the response

        Returns:
            List containing cell metadata, source, and outputs
        """
        if not self.active_notebook:
            return ["Error: No active notebook. Use use_notebook first."]

        nb_info = self.notebooks[self.active_notebook]
        nb = nb_info.notebook

        if cell_index < 0 or cell_index >= len(nb.cells):
            return [f"Error: Cell index {cell_index} out of range (0-{len(nb.cells) - 1})"]

        cell = nb.cells[cell_index]
        exec_count = cell.get('execution_count', '') or ''

        result = [
            f"Cell [{cell_index}]\n"
            f"Type: {cell.cell_type}\n"
            f"Execution Count: {exec_count}\n"
            f"{'-' * 80}\n"
            f"Source:\n{cell.source}\n"
        ]

        if include_outputs and cell.cell_type == 'code' and cell.get('outputs'):
            result.append(f"\n{'-' * 80}\nOutputs:\n")
            result.extend(self._format_outputs(cell.outputs))

        return result

    def delete_cell(
        self,
        cell_indices: List[int],
        include_source: bool = True
    ) -> str:
        """
        Delete specific cells from the active notebook.

        Args:
            cell_indices: List of indices of cells to delete (0-based)
            include_source: Whether to include source of deleted cells

        Returns:
            Success message with deleted cell sources
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]
        nb = nb_info.notebook

        # Validate indices
        invalid = [i for i in cell_indices if i < 0 or i >= len(nb.cells)]
        if invalid:
            return f"Error: Invalid cell indices: {invalid} (range: 0-{len(nb.cells) - 1})"

        # Create and execute command
        command = DeleteCellCommand(cell_indices=cell_indices)

        try:
            command.execute(self)
            nb_info.history.add_command(command)

            # Sort indices for display
            sorted_indices = sorted(set(cell_indices), reverse=True)

            # Gather deleted cell info for display
            deleted_info = []
            if include_source:
                for item in command.deleted_cells:
                    idx = item['index']
                    cell_dict = item['cell']
                    deleted_info.append(
                        f"Cell [{idx}] ({cell_dict.get('cell_type', 'unknown')}):\n{'-' * 40}\n{cell_dict.get('source', '')}\n"
                    )

            result = f"✓ Deleted {len(sorted_indices)} cell(s): {sorted_indices}\n"
            result += f"Notebook: {self.active_notebook}\n"

            if include_source and deleted_info:
                result += f"\n{'=' * 80}\nDeleted cells:\n\n" + "\n".join(deleted_info)

            return result

        except Exception as e:
            return f"Error deleting cells: {str(e)}"

    def move_cell(
        self,
        from_index: int,
        to_index: int
    ) -> str:
        """
        Move a cell from one position to another in the active notebook.

        Args:
            from_index: Current index of the cell to move (0-based)
            to_index: Target index to move the cell to (0-based)

        Returns:
            Success message with notebook structure
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]
        nb = nb_info.notebook

        # Validate indices
        if from_index < 0 or from_index >= len(nb.cells):
            return f"Error: from_index {from_index} out of range (0-{len(nb.cells) - 1})"

        if to_index < 0 or to_index >= len(nb.cells):
            return f"Error: to_index {to_index} out of range (0-{len(nb.cells) - 1})"

        if from_index == to_index:
            return f"✓ Cell already at index {to_index}, no move needed"

        # Create and execute command
        command = MoveCellCommand(from_index=from_index, to_index=to_index)

        try:
            command.execute(self)
            nb_info.history.add_command(command)

            # Get context around the moved cell
            context_start = max(0, to_index - 2)
            context_end = min(len(nb.cells), to_index + 3)
            context_cells = []

            for i in range(context_start, context_end):
                c = nb.cells[i]
                marker = ">>> MOVED HERE <<<" if i == to_index else ""
                first_line = c.source.split('\n')[0][:40] if c.source else "(empty)"
                context_cells.append(f"[{i}] {c.cell_type}: {first_line} {marker}")

            context = "\n".join(context_cells)

            return (
                f"✓ Cell moved from index {from_index} to {to_index}\n"
                f"Notebook: {self.active_notebook}\n"
                f"\nNotebook structure:\n{context}"
            )

        except Exception as e:
            return f"Error moving cell: {str(e)}"

    def swap_cells(
        self,
        index1: int,
        index2: int
    ) -> str:
        """
        Swap two cells in the active notebook.

        Args:
            index1: Index of first cell (0-based)
            index2: Index of second cell (0-based)

        Returns:
            Success message
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]
        nb = nb_info.notebook

        # Validate indices
        if index1 < 0 or index1 >= len(nb.cells):
            return f"Error: index1 {index1} out of range (0-{len(nb.cells) - 1})"

        if index2 < 0 or index2 >= len(nb.cells):
            return f"Error: index2 {index2} out of range (0-{len(nb.cells) - 1})"

        if index1 == index2:
            return f"✓ Cells are the same, no swap needed"

        # Create and execute command
        command = SwapCellsCommand(index1=index1, index2=index2)

        try:
            command.execute(self)
            nb_info.history.add_command(command)

            return (
                f"✓ Swapped cells at indices {index1} and {index2}\n"
                f"Notebook: {self.active_notebook}\n"
                f"Cell {index1}: {nb.cells[index1].source.split(chr(10))[0][:40]}\n"
                f"Cell {index2}: {nb.cells[index2].source.split(chr(10))[0][:40]}"
            )

        except Exception as e:
            return f"Error swapping cells: {str(e)}"

    def reorder_cells(
        self,
        new_order: List[int]
    ) -> str:
        """
        Reorder cells according to a new sequence of indices.

        Args:
            new_order: List of cell indices in the desired order.
                      Must contain all indices from 0 to len(cells)-1 exactly once.

        Returns:
            Success message with new cell order

        Example:
            # Original order: [0, 1, 2, 3]
            # Reorder to: [2, 0, 3, 1]
            manager.reorder_cells([2, 0, 3, 1])
            # New order: Cell 2 is now at position 0, Cell 0 is now at position 1, etc.
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]
        nb = nb_info.notebook

        # Validate new_order
        if len(new_order) != len(nb.cells):
            return f"Error: new_order length ({len(new_order)}) doesn't match cell count ({len(nb.cells)})"

        expected_indices = set(range(len(nb.cells)))
        actual_indices = set(new_order)

        if actual_indices != expected_indices:
            missing = expected_indices - actual_indices
            extra = actual_indices - expected_indices
            error_msg = "Error: Invalid new_order."
            if missing:
                error_msg += f" Missing indices: {sorted(missing)}."
            if extra:
                error_msg += f" Invalid indices: {sorted(extra)}."
            return error_msg

        # Create and execute command
        command = ReorderCellsCommand(new_order=new_order)

        try:
            command.execute(self)
            nb_info.history.add_command(command)

            # Create summary of reordering
            reorder_summary = []
            for new_pos, old_pos in enumerate(new_order):
                if new_pos != old_pos:
                    cell = nb.cells[new_pos]
                    first_line = cell.source.split('\n')[0][:40] if cell.source else "(empty)"
                    reorder_summary.append(f"  [{old_pos}] → [{new_pos}]: {first_line}")

            summary = "\n".join(reorder_summary) if reorder_summary else "  (all cells already in order)"

            return (
                f"✓ Reordered {len(nb.cells)} cells\n"
                f"Notebook: {self.active_notebook}\n"
                f"\nChanges:\n{summary}"
            )

        except Exception as e:
            return f"Error reordering cells: {str(e)}"

    def execute_code(
        self,
        code: str,
        timeout: int = 30
    ) -> List[Union[str, Dict]]:
        """
        Execute code directly in the kernel without saving to notebook.

        Args:
            code: Code to execute (supports magic commands and shell commands)
            timeout: Execution timeout in seconds (max: 60)

        Returns:
            List of outputs from the executed code
        """
        if not self.active_notebook:
            return ["Error: No active notebook. Use use_notebook first."]

        nb_info = self.notebooks[self.active_notebook]
        timeout = min(timeout, 60)

        try:
            outputs = nb_info.shell.run(code, timeout=timeout)
            nb_info.last_activity = datetime.now()

            return self._format_outputs(outputs)

        except TimeoutError:
            return [f"Error: Code execution timed out after {timeout} seconds"]
        except KeyboardInterrupt:
            return ["Error: Code execution was stopped by user"]
        except Exception as e:
            return [f"Error executing code: {str(e)}"]

    # ================== Additional Tools ==================

    def stop_execution(self) -> str:
        """
        Stop the current cell execution in the active notebook.

        Returns:
            Success message
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]
        nb_info.shell.stop_execution()

        return f"✓ Execution stop requested for notebook '{self.active_notebook}'"

    def get_active_notebook(self) -> Optional[str]:
        """Get the name of the currently active notebook"""
        return self.active_notebook

    def set_active_notebook(self, notebook_name: str) -> str:
        """
        Set a different notebook as active.

        Args:
            notebook_name: Name of notebook to activate

        Returns:
            Success message
        """
        if notebook_name not in self.notebooks:
            return f"Error: Notebook '{notebook_name}' not found"

        # Deactivate current active notebook
        if self.active_notebook:
            self.notebooks[self.active_notebook].is_active = False

        # Activate new notebook
        self.active_notebook = notebook_name
        self.notebooks[notebook_name].is_active = True

        return f"✓ Notebook '{notebook_name}' is now active"

    # ================== Undo/Redo Operations ==================

    def undo(self, steps: int = 1) -> str:
        """
        Undo the last N operations in the active notebook.

        Args:
            steps: Number of operations to undo (default: 1)

        Returns:
            Success message with list of undone operations
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]

        if not nb_info.history.can_undo():
            return "Nothing to undo"

        # Get descriptions before undoing
        descriptions = nb_info.history.get_undo_description(steps)

        try:
            results = nb_info.history.undo(self, steps)

            summary = f"✓ Undid {len(results)} operation(s):\n"
            for desc in descriptions[:len(results)]:
                summary += f"  - {desc}\n"

            return summary.rstrip()

        except Exception as e:
            return f"Error during undo: {str(e)}"

    def redo(self, steps: int = 1) -> str:
        """
        Redo the last N undone operations in the active notebook.

        Args:
            steps: Number of operations to redo (default: 1)

        Returns:
            Success message with list of redone operations
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]

        if not nb_info.history.can_redo():
            return "Nothing to redo"

        # Get descriptions before redoing
        descriptions = nb_info.history.get_redo_description(steps)

        try:
            results = nb_info.history.redo(self, steps)

            summary = f"✓ Redid {len(results)} operation(s):\n"
            for desc in descriptions[:len(results)]:
                summary += f"  - {desc}\n"

            return summary.rstrip()

        except Exception as e:
            return f"Error during redo: {str(e)}"

    def get_history(self) -> str:
        """
        Get the operation history for the active notebook.

        Returns:
            Formatted history summary
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]
        summary = nb_info.history.get_history_summary()

        result = f"Operation History for '{self.active_notebook}':\n"
        result += f"  Undo available: {summary['undo_count']} operation(s)\n"
        result += f"  Redo available: {summary['redo_count']} operation(s)\n"

        if summary['recent_operations']:
            result += f"\nRecent operations:\n"
            for i, op in enumerate(summary['recent_operations'], 1):
                result += f"  {i}. {op}\n"
        else:
            result += "\nNo operations in history\n"

        return result.rstrip()

    def clear_history(self) -> str:
        """
        Clear the operation history for the active notebook.

        Returns:
            Success message
        """
        if not self.active_notebook:
            return "Error: No active notebook. Use use_notebook first."

        nb_info = self.notebooks[self.active_notebook]
        nb_info.history.clear()

        return f"✓ History cleared for notebook '{self.active_notebook}'"

    # ================== Helper Methods ==================

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def _format_outputs(self, outputs: List) -> List[Union[str, Dict]]:
        """Format outputs for display"""
        if not outputs:
            return ["(no output)"]

        result = []

        for output in outputs:
            output_type = output.get('output_type', 'unknown')

            if output_type == 'stream':
                text = ''.join(output.get('text', []))
                result.append(f"[{output['name']}]\n{text}")

            elif output_type in ('execute_result', 'display_data'):
                data = output.get('data', {})

                # Handle different data types
                if 'text/plain' in data:
                    result.append(''.join(data['text/plain']))
                elif 'text/html' in data:
                    result.append({'type': 'html', 'content': ''.join(data['text/html'])})
                elif 'image/png' in data:
                    result.append({'type': 'image', 'format': 'png', 'data': ''.join(data['image/png'])})
                elif 'image/jpeg' in data:
                    result.append({'type': 'image', 'format': 'jpeg', 'data': ''.join(data['image/jpeg'])})

            elif output_type == 'error':
                traceback = ''.join(output.get('traceback', []))
                result.append(f"[ERROR] {output.get('ename', 'Error')}: {output.get('evalue', '')}\n{traceback}")

        return result
