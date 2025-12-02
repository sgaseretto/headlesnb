"""Generic base classes shared between notebooks and dialogs.

This module provides abstract base classes that encapsulate common
functionality for managing notebooks and dialogs, including:
- Thread-safe item management
- File system operations
- Undo/redo history
- Output formatting utilities

Example:
    >>> from headlesnb.base import BaseManager
    >>> class NotebookManager(BaseManager):
    ...     @property
    ...     def item_type_name(self) -> str:
    ...         return "notebook"
"""

import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from execnb.shell import CaptureShell

from .history import OperationHistory


@dataclass
class ManagedItemInfo(ABC):
    """Base class for managed items (notebooks or dialogs).

    This abstract dataclass provides common fields for both notebooks
    and dialogs. Subclasses should add type-specific fields.

    Attributes:
        name: Unique identifier for this item.
        path: File system path where item is stored. None for in-memory items.
        shell: CaptureShell instance for code execution. None if not needed.
        history: Operation history for undo/redo support.
        created_at: Timestamp when item was created or loaded.
        last_activity: Timestamp of most recent modification.
        is_active: Whether this item is currently the active/focused item.

    Example:
        >>> from headlesnb.base import ManagedItemInfo
        >>> @dataclass
        ... class NotebookInfo(ManagedItemInfo):
        ...     notebook: Any = None  # The actual notebook object
        ...     kernel_id: str = ""
    """
    name: str
    path: Optional[Path] = None
    shell: Optional[CaptureShell] = None
    history: OperationHistory = field(default_factory=lambda: OperationHistory(max_size=100))
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = False


class BaseManager(ABC):
    """Base manager class with common functionality for notebooks and dialogs.

    This abstract base class provides:
    - Thread-safe item management (use/unuse/activate)
    - File listing utilities
    - Undo/redo operations via OperationHistory
    - Output formatting helpers

    Subclasses must implement the abstract methods to handle type-specific
    loading, creation, and saving of items.

    Attributes:
        root_path: Base path for file operations.

    Example:
        >>> from headlesnb.base import BaseManager
        >>> class DialogManager(BaseManager):
        ...     @property
        ...     def item_type_name(self) -> str:
        ...         return "dialog"
        ...
        ...     def _load_item(self, name: str, path: str) -> DialogInfo:
        ...         # Load dialog from .ipynb file
        ...         ...
    """

    def __init__(self, root_path: str = "."):
        """Initialize the BaseManager.

        Args:
            root_path: Root directory for file operations. Defaults to
                current directory.
        """
        self.root_path = Path(root_path).resolve()
        self._items: Dict[str, ManagedItemInfo] = {}
        self._active_item: Optional[str] = None
        self._lock = threading.Lock()

    # ================== Abstract Methods (must implement) ==================

    @property
    @abstractmethod
    def item_type_name(self) -> str:
        """Return the human-readable type name for messages.

        Returns:
            Type name string, e.g., 'notebook' or 'dialog'.
        """
        pass

    @abstractmethod
    def _load_item(self, name: str, path: str) -> ManagedItemInfo:
        """Load an item from disk.

        Args:
            name: Unique identifier for the item.
            path: Relative path to the item file.

        Returns:
            Loaded item info object.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file format is invalid.
        """
        pass

    @abstractmethod
    def _create_item(self, name: str, path: str) -> ManagedItemInfo:
        """Create a new item.

        Args:
            name: Unique identifier for the item.
            path: Relative path where item will be saved.

        Returns:
            Newly created item info object.
        """
        pass

    @abstractmethod
    def _save_item(self, item: ManagedItemInfo):
        """Save an item to disk.

        Args:
            item: Item to save.
        """
        pass

    # ================== Generic File Operations (100% reusable) ==================

    def list_files(
        self,
        path: str = "",
        max_depth: int = 1,
        start_index: int = 0,
        limit: int = 25,
        pattern: str = ""
    ) -> str:
        """List all files and directories recursively.

        This method provides paginated directory listing with optional
        filtering by glob pattern.

        Args:
            path: Starting path relative to root_path. Empty string means
                root directory.
            max_depth: Maximum depth to recurse into subdirectories.
                Capped at 3 for performance. Defaults to 1.
            start_index: Starting index for pagination (0-based).
                Defaults to 0.
            limit: Maximum number of items to return. Use 0 for no limit.
                Defaults to 25.
            pattern: Glob pattern to filter file paths. Empty string means
                no filtering. Defaults to "".

        Returns:
            Tab-separated table with columns: Path, Type, Size, Last_Modified.
            First line shows pagination info.

        Example:
            >>> manager.list_files(pattern="*.ipynb", limit=10)
            'Showing 1-3 of 3 items\\nPath\\tType\\tSize\\tLast_Modified\\n...'
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
                    if pattern and not item.match(pattern):
                        continue
                    try:
                        stat = item.stat()
                        if item.is_file():
                            file_type = "notebook" if item.suffix == ".ipynb" else "file"
                            size_str = self._format_size(stat.st_size)
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
                        if item.is_dir():
                            _scan_dir(item, current_depth + 1)
                    except (PermissionError, OSError):
                        files.append({"path": str(rel_path), "type": "error", "size": "", "modified": ""})
            except (PermissionError, OSError):
                pass

        _scan_dir(start_path, 0)
        files.sort(key=lambda x: x["path"])

        total_count = len(files)
        end_index = start_index + limit if limit > 0 else total_count
        paginated_files = files[start_index:end_index]

        header = f"Showing {start_index + 1}-{min(end_index, total_count)} of {total_count} items\n"
        header += "Path\tType\tSize\tLast_Modified"
        rows = [f"{f['path']}\t{f['type']}\t{f['size']}\t{f['modified']}" for f in paginated_files]

        return header + "\n" + "\n".join(rows)

    # ================== Generic Item Management ==================

    def use_item(
        self,
        name: str,
        path: str,
        mode: str = "connect"
    ) -> str:
        """Use an item and activate it.

        This method either connects to an existing item or creates a new one,
        then makes it the active item for subsequent operations.

        Args:
            name: Unique identifier for the item. Must not already be in use.
            path: Relative path to the item file.
            mode: Either 'connect' (load existing) or 'create' (create new).
                Defaults to 'connect'.

        Returns:
            Success message with item information, or error message if failed.

        Example:
            >>> manager.use_item('my_dialog', 'dialogs/test.ipynb', mode='create')
            '... Dialog "my_dialog" activated'
        """
        with self._lock:
            if name in self._items:
                return f"Error: {self.item_type_name.title()} '{name}' is already in use."

            full_path = self.root_path / path if path else None

            if mode == "create":
                if full_path and full_path.exists():
                    return f"Error: {self.item_type_name.title()} '{path}' already exists."
                item = self._create_item(name, path)
            elif mode == "connect":
                if full_path and not full_path.exists():
                    return f"Error: {self.item_type_name.title()} '{path}' not found."
                item = self._load_item(name, path)
            else:
                return f"Error: Invalid mode '{mode}'."

            self._items[name] = item
            self._active_item = name
            item.is_active = True

            return f"... {self.item_type_name.title()} '{name}' activated"

    def unuse_item(self, name: str) -> str:
        """Release an item and save it to disk.

        Args:
            name: Name of the item to release.

        Returns:
            Success message, or error if item not found.
        """
        with self._lock:
            if name not in self._items:
                return f"Error: {self.item_type_name.title()} '{name}' not found"

            item = self._items[name]
            self._save_item(item)
            del self._items[name]

            if self._active_item == name:
                self._active_item = next(iter(self._items.keys()), None)

            return f"... {self.item_type_name.title()} '{name}' released"

    def get_active_item(self) -> Optional[str]:
        """Get the name of the currently active item.

        Returns:
            Name of active item, or None if no item is active.
        """
        return self._active_item

    def set_active_item(self, name: str) -> str:
        """Set a different item as active.

        Args:
            name: Name of item to activate.

        Returns:
            Success message, or error if item not found.
        """
        if name not in self._items:
            return f"Error: {self.item_type_name.title()} '{name}' not found"

        if self._active_item:
            self._items[self._active_item].is_active = False

        self._active_item = name
        self._items[name].is_active = True

        return f"... {self.item_type_name.title()} '{name}' is now active"

    # ================== Generic Undo/Redo (100% reusable) ==================

    def undo(self, steps: int = 1) -> str:
        """Undo the last N operations.

        Args:
            steps: Number of operations to undo. Defaults to 1.

        Returns:
            Summary of undone operations, or error message.
        """
        if not self._active_item:
            return f"Error: No active {self.item_type_name}."

        item = self._items[self._active_item]

        if not item.history.can_undo():
            return "Nothing to undo"

        descriptions = item.history.get_undo_description(steps)

        try:
            results = item.history.undo(self, steps)
            summary = f"... Undid {len(results)} operation(s):\n"
            for desc in descriptions[:len(results)]:
                summary += f"  - {desc}\n"
            return summary.rstrip()
        except Exception as e:
            return f"Error during undo: {str(e)}"

    def redo(self, steps: int = 1) -> str:
        """Redo the last N undone operations.

        Args:
            steps: Number of operations to redo. Defaults to 1.

        Returns:
            Summary of redone operations, or error message.
        """
        if not self._active_item:
            return f"Error: No active {self.item_type_name}."

        item = self._items[self._active_item]

        if not item.history.can_redo():
            return "Nothing to redo"

        descriptions = item.history.get_redo_description(steps)

        try:
            results = item.history.redo(self, steps)
            summary = f"... Redid {len(results)} operation(s):\n"
            for desc in descriptions[:len(results)]:
                summary += f"  - {desc}\n"
            return summary.rstrip()
        except Exception as e:
            return f"Error during redo: {str(e)}"

    def get_history(self) -> str:
        """Get the operation history for the active item.

        Returns:
            Formatted history summary including undo/redo counts
            and recent operations.
        """
        if not self._active_item:
            return f"Error: No active {self.item_type_name}."

        item = self._items[self._active_item]
        summary = item.history.get_history_summary()

        result = f"Operation History for '{self._active_item}':\n"
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
        """Clear the operation history for the active item.

        Returns:
            Success message.
        """
        if not self._active_item:
            return f"Error: No active {self.item_type_name}."

        self._items[self._active_item].history.clear()
        return f"... History cleared for '{self._active_item}'"

    # ================== Generic Helpers (100% reusable) ==================

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format.

        Args:
            size: Size in bytes.

        Returns:
            Formatted string like "1.5 KB" or "2.3 MB".
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def _format_outputs(self, outputs: List) -> List:
        """Format execution outputs for display.

        Converts raw notebook output format into a more readable format,
        handling streams, execution results, display data, and errors.

        Args:
            outputs: List of output dictionaries from code execution.

        Returns:
            List of formatted output strings or dictionaries for
            special content types (images, HTML).
        """
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
                if 'text/plain' in data:
                    result.append(''.join(data['text/plain']))
                elif 'text/html' in data:
                    result.append({'type': 'html', 'content': ''.join(data['text/html'])})
                elif 'image/png' in data:
                    result.append({'type': 'image', 'format': 'png', 'data': ''.join(data['image/png'])})
            elif output_type == 'error':
                traceback = ''.join(output.get('traceback', []))
                result.append(f"[ERROR] {output.get('ename', 'Error')}: {output.get('evalue', '')}\n{traceback}")

        return result
