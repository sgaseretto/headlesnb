"""
History tracking and undo/redo functionality for notebook operations.

Design Philosophy:
------------------
This module implements the Command Pattern for undo/redo functionality. Each
notebook-modifying operation is represented as a command object that can be
executed and undone.

Key Design Decisions:
---------------------

1. **Command Pattern**: Each operation (insert, delete, move, etc.) is encapsulated
   as a command object with execute() and undo() methods. This provides a clean
   abstraction and makes it easy to add new undoable operations.

2. **Dual Stack Architecture**: We maintain two stacks:
   - undo_stack: Commands that have been executed and can be undone
   - redo_stack: Commands that have been undone and can be redone

   When a new operation is performed, the redo_stack is cleared (standard UX pattern).

3. **What Gets Tracked**: Only operations that modify the notebook structure or
   content are tracked:
   - insert_cell, delete_cell, overwrite_cell_source
   - move_cell, swap_cells, reorder_cells

   Operations that don't modify the notebook (execute_cell, read operations) are
   NOT tracked because:
   - Execution outputs are transient and recreating them would require re-execution
   - Read operations don't change state
   - This keeps the history focused on structural changes

4. **State Preservation**: Each command stores the minimum information needed to
   undo the operation:
   - insert_cell: stores the inserted cell and index
   - delete_cell: stores the deleted cells with their original indices
   - overwrite_cell_source: stores the old and new source
   - move_cell/swap_cells/reorder_cells: stores the transformation that occurred

5. **Index Handling**: Special care is taken with indices:
   - delete_cell operations store cells in descending index order to avoid
     index shifting issues during redo
   - reorder_cells stores the complete old order for accurate undo

6. **Memory Management**: History has a configurable maximum size (default: 100)
   to prevent unbounded memory growth.

7. **Atomicity**: Operations are atomic - if an undo/redo fails, the notebook
   remains in a consistent state.

8. **History Persistence**: History is NOT persisted to disk. When a notebook is
   closed and reopened, history is cleared. This is intentional because:
   - The notebook file format doesn't include history
   - History is session-specific
   - Users expect undo/redo to work within a session, not across sessions

Threading Considerations:
-------------------------
History operations are thread-safe when used with the NotebookManager's lock,
but the history stack itself is not separately locked. It's designed to be used
only through the NotebookManager's synchronized methods.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy


class HistoryCommand:
    """
    Base class for all undoable commands.

    Each command represents a single operation that can be undone and redone.
    Commands store the minimal information needed to reverse their effects.
    """
    def __init__(self):
        self.timestamp = datetime.now()

    def execute(self, manager) -> str:
        """Execute this command. Returns a result message."""
        raise NotImplementedError

    def undo(self, manager) -> str:
        """Undo this command. Returns a result message."""
        raise NotImplementedError

    def redo(self, manager) -> str:
        """Redo this command (default: call execute again)."""
        return self.execute(manager)

    def description(self) -> str:
        """Human-readable description of this command."""
        raise NotImplementedError


@dataclass
class InsertCellCommand(HistoryCommand):
    """Command for inserting a cell."""
    cell_index: int
    cell_type: str
    cell_source: str

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        from execnb.nbio import mk_cell

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Create new cell
        new_cell = mk_cell(self.cell_source, cell_type=self.cell_type)

        # Handle append case
        actual_index = len(nb.cells) if self.cell_index == -1 else self.cell_index

        # Insert cell
        nb.cells.insert(actual_index, new_cell)

        # Reindex cells
        for i, cell in enumerate(nb.cells):
            cell.idx_ = i

        # Save notebook
        from execnb.nbio import write_nb
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        # Update stored index if it was -1
        self.cell_index = actual_index

        return f"Inserted {self.cell_type} cell at index {actual_index}"

    def undo(self, manager) -> str:
        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Remove the cell
        if self.cell_index < len(nb.cells):
            del nb.cells[self.cell_index]

        # Reindex cells
        for i, cell in enumerate(nb.cells):
            cell.idx_ = i

        # Save notebook
        from execnb.nbio import write_nb
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Undid insert of {self.cell_type} cell at index {self.cell_index}"

    def description(self) -> str:
        return f"Insert {self.cell_type} cell at [{self.cell_index}]"


@dataclass
class DeleteCellCommand(HistoryCommand):
    """Command for deleting cells."""
    cell_indices: List[int]
    deleted_cells: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        from execnb.nbio import write_nb, nb2dict

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Sort indices in descending order
        sorted_indices = sorted(set(self.cell_indices), reverse=True)

        # Store cells before deletion
        self.deleted_cells = []
        for idx in sorted_indices:
            if idx < len(nb.cells):
                # Store cell as dict with its original index
                cell_dict = nb2dict(nb.cells[idx])
                self.deleted_cells.append({
                    'index': idx,
                    'cell': cell_dict
                })
                del nb.cells[idx]

        # Reindex cells
        for i, cell in enumerate(nb.cells):
            cell.idx_ = i

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Deleted {len(self.deleted_cells)} cell(s)"

    def undo(self, manager) -> str:
        from execnb.nbio import write_nb, NbCell

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Re-insert cells in reverse order (ascending indices)
        for item in reversed(self.deleted_cells):
            idx = item['index']
            cell_dict = item['cell']
            # Recreate cell object
            cell = NbCell(idx, cell_dict)
            nb.cells.insert(idx, cell)

        # Reindex cells
        for i, cell in enumerate(nb.cells):
            cell.idx_ = i

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Restored {len(self.deleted_cells)} deleted cell(s)"

    def description(self) -> str:
        return f"Delete {len(self.cell_indices)} cell(s) at {self.cell_indices}"


@dataclass
class OverwriteCellCommand(HistoryCommand):
    """Command for overwriting a cell's source."""
    cell_index: int
    old_source: str
    new_source: str

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        from execnb.nbio import write_nb

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Store old source if not set
        if not self.old_source:
            self.old_source = nb.cells[self.cell_index].source

        # Update cell source
        nb.cells[self.cell_index].set_source(self.new_source)

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Overwrote cell [{self.cell_index}] source"

    def undo(self, manager) -> str:
        from execnb.nbio import write_nb

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Restore old source
        nb.cells[self.cell_index].set_source(self.old_source)

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Restored cell [{self.cell_index}] to previous source"

    def description(self) -> str:
        return f"Overwrite cell [{self.cell_index}]"


@dataclass
class MoveCellCommand(HistoryCommand):
    """Command for moving a cell."""
    from_index: int
    to_index: int

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        from execnb.nbio import write_nb

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Remove cell from original position
        cell = nb.cells.pop(self.from_index)

        # Insert at new position
        nb.cells.insert(self.to_index, cell)

        # Reindex cells
        for i, c in enumerate(nb.cells):
            c.idx_ = i

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Moved cell from [{self.from_index}] to [{self.to_index}]"

    def undo(self, manager) -> str:
        from execnb.nbio import write_nb

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Move cell back
        cell = nb.cells.pop(self.to_index)
        nb.cells.insert(self.from_index, cell)

        # Reindex cells
        for i, c in enumerate(nb.cells):
            c.idx_ = i

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Moved cell back from [{self.to_index}] to [{self.from_index}]"

    def description(self) -> str:
        return f"Move cell [{self.from_index}] → [{self.to_index}]"


@dataclass
class SwapCellsCommand(HistoryCommand):
    """Command for swapping two cells."""
    index1: int
    index2: int

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        from execnb.nbio import write_nb

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Swap cells
        nb.cells[self.index1], nb.cells[self.index2] = nb.cells[self.index2], nb.cells[self.index1]

        # Reindex cells
        for i, c in enumerate(nb.cells):
            c.idx_ = i

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Swapped cells [{self.index1}] and [{self.index2}]"

    def undo(self, manager) -> str:
        # Swapping again undoes the swap
        return self.execute(manager)

    def description(self) -> str:
        return f"Swap cells [{self.index1}] ↔ [{self.index2}]"


@dataclass
class ReorderCellsCommand(HistoryCommand):
    """Command for reordering cells."""
    old_order: List[int] = field(default_factory=list)
    new_order: List[int] = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        from execnb.nbio import write_nb

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Store old order if not set
        if not self.old_order:
            self.old_order = list(range(len(nb.cells)))

        # Create new cell list in specified order
        old_cells = nb.cells.copy()
        nb.cells = [old_cells[i] for i in self.new_order]

        # Reindex cells
        for i, c in enumerate(nb.cells):
            c.idx_ = i

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Reordered {len(nb.cells)} cells"

    def undo(self, manager) -> str:
        from execnb.nbio import write_nb

        nb_info = manager.notebooks[manager.active_notebook]
        nb = nb_info.notebook

        # Restore old order
        old_cells = nb.cells.copy()
        nb.cells = [old_cells[self.new_order.index(i)] for i in self.old_order]

        # Reindex cells
        for i, c in enumerate(nb.cells):
            c.idx_ = i

        # Save notebook
        write_nb(nb, nb_info.path)
        nb_info.last_activity = datetime.now()

        return f"Restored previous cell order"

    def description(self) -> str:
        return f"Reorder cells: {self.new_order}"


class OperationHistory:
    """
    Manages the history of operations for undo/redo functionality.

    This class maintains two stacks:
    - undo_stack: Operations that can be undone
    - redo_stack: Operations that can be redone

    When a new operation is performed, it's added to undo_stack and redo_stack
    is cleared (standard undo/redo behavior).
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize the operation history.

        Args:
            max_size: Maximum number of operations to keep in history.
                     Older operations are discarded when limit is reached.
        """
        self.max_size = max_size
        self.undo_stack: List[HistoryCommand] = []
        self.redo_stack: List[HistoryCommand] = []

    def add_command(self, command: HistoryCommand):
        """
        Add a command to the history.

        This should be called after a command is successfully executed.
        Clears the redo stack (standard undo/redo behavior).
        """
        self.undo_stack.append(command)
        self.redo_stack.clear()  # Clear redo stack on new operation

        # Limit history size
        if len(self.undo_stack) > self.max_size:
            self.undo_stack.pop(0)

    def can_undo(self) -> bool:
        """Check if there are operations that can be undone."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if there are operations that can be redone."""
        return len(self.redo_stack) > 0

    def get_undo_description(self, count: int = 1) -> List[str]:
        """Get descriptions of the next N operations that would be undone."""
        if count > len(self.undo_stack):
            count = len(self.undo_stack)
        return [self.undo_stack[-(i+1)].description() for i in range(count)]

    def get_redo_description(self, count: int = 1) -> List[str]:
        """Get descriptions of the next N operations that would be redone."""
        if count > len(self.redo_stack):
            count = len(self.redo_stack)
        return [self.redo_stack[-(i+1)].description() for i in range(count)]

    def undo(self, manager, steps: int = 1) -> List[str]:
        """
        Undo the last N operations.

        Args:
            manager: The NotebookManager instance
            steps: Number of operations to undo

        Returns:
            List of result messages for each undone operation
        """
        results = []
        steps = min(steps, len(self.undo_stack))

        for _ in range(steps):
            if not self.undo_stack:
                break

            command = self.undo_stack.pop()
            try:
                result = command.undo(manager)
                results.append(result)
                self.redo_stack.append(command)
            except Exception as e:
                # If undo fails, put command back and raise
                self.undo_stack.append(command)
                raise Exception(f"Failed to undo {command.description()}: {str(e)}")

        return results

    def redo(self, manager, steps: int = 1) -> List[str]:
        """
        Redo the last N undone operations.

        Args:
            manager: The NotebookManager instance
            steps: Number of operations to redo

        Returns:
            List of result messages for each redone operation
        """
        results = []
        steps = min(steps, len(self.redo_stack))

        for _ in range(steps):
            if not self.redo_stack:
                break

            command = self.redo_stack.pop()
            try:
                result = command.redo(manager)
                results.append(result)
                self.undo_stack.append(command)
            except Exception as e:
                # If redo fails, put command back and raise
                self.redo_stack.append(command)
                raise Exception(f"Failed to redo {command.description()}: {str(e)}")

        return results

    def clear(self):
        """Clear all history."""
        self.undo_stack.clear()
        self.redo_stack.clear()

    def get_history_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current history state.

        Returns a dictionary with:
        - undo_count: Number of operations that can be undone
        - redo_count: Number of operations that can be redone
        - recent_operations: List of recent operation descriptions
        """
        return {
            'undo_count': len(self.undo_stack),
            'redo_count': len(self.redo_stack),
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo(),
            'recent_operations': [cmd.description() for cmd in self.undo_stack[-10:]]
        }
