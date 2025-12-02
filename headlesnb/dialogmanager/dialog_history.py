"""Dialog-specific history commands for undo/redo functionality.

This module implements the Command Pattern for dialog operations.
Each command represents a single operation that can be undone and redone.

Design Notes:
- Commands store minimal information needed to reverse their effects
- Follows same pattern as nbmanager history commands
- Uses DialogInfo.messages list instead of notebook cells
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy

from ..history import HistoryCommand
from .message import Message
from .serialization import save_dialog_to_file


@dataclass
class InsertMessageCommand(HistoryCommand):
    """Command for inserting a message."""
    msg_index: int
    message: Message
    _inserted_id: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Handle append case
        actual_index = len(dialog.messages) if self.msg_index == -1 else self.msg_index

        # Insert message
        dialog.messages.insert(actual_index, self.message)
        self._inserted_id = self.message.id

        # Update stored index if it was -1
        self.msg_index = actual_index

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Inserted {self.message.msg_type} message at index {actual_index}"

    def undo(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Remove the message
        if self.msg_index < len(dialog.messages):
            del dialog.messages[self.msg_index]

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Undid insert of {self.message.msg_type} message at index {self.msg_index}"

    def description(self) -> str:
        return f"Insert {self.message.msg_type} message at [{self.msg_index}]"


@dataclass
class DeleteMessageCommand(HistoryCommand):
    """Command for deleting messages."""
    msg_indices: List[int]
    deleted_messages: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Sort indices in descending order
        sorted_indices = sorted(set(self.msg_indices), reverse=True)

        # Store messages before deletion
        self.deleted_messages = []
        for idx in sorted_indices:
            if idx < len(dialog.messages):
                msg = dialog.messages[idx]
                self.deleted_messages.append({
                    'index': idx,
                    'message': deepcopy(msg)
                })
                del dialog.messages[idx]

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Deleted {len(self.deleted_messages)} message(s)"

    def undo(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Re-insert messages in reverse order (ascending indices)
        for item in reversed(self.deleted_messages):
            idx = item['index']
            msg = item['message']
            dialog.messages.insert(idx, msg)

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Restored {len(self.deleted_messages)} deleted message(s)"

    def description(self) -> str:
        return f"Delete {len(self.msg_indices)} message(s) at {self.msg_indices}"


@dataclass
class UpdateMessageCommand(HistoryCommand):
    """Command for updating a message's content or output."""
    msg_index: int
    field_name: str  # 'content', 'output', or other field
    old_value: Any
    new_value: Any

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]
        msg = dialog.messages[self.msg_index]

        # Store old value if not set
        if self.old_value is None:
            self.old_value = getattr(msg, self.field_name)

        # Update field
        setattr(msg, self.field_name, self.new_value)

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Updated message [{self.msg_index}] {self.field_name}"

    def undo(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]
        msg = dialog.messages[self.msg_index]

        # Restore old value
        setattr(msg, self.field_name, self.old_value)

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Restored message [{self.msg_index}] {self.field_name} to previous value"

    def description(self) -> str:
        return f"Update message [{self.msg_index}] {self.field_name}"


@dataclass
class MoveMessageCommand(HistoryCommand):
    """Command for moving a message."""
    from_index: int
    to_index: int

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Remove message from original position
        msg = dialog.messages.pop(self.from_index)

        # Insert at new position
        dialog.messages.insert(self.to_index, msg)

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Moved message from [{self.from_index}] to [{self.to_index}]"

    def undo(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Move message back
        msg = dialog.messages.pop(self.to_index)
        dialog.messages.insert(self.from_index, msg)

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Moved message back from [{self.to_index}] to [{self.from_index}]"

    def description(self) -> str:
        return f"Move message [{self.from_index}] -> [{self.to_index}]"


@dataclass
class SwapMessagesCommand(HistoryCommand):
    """Command for swapping two messages."""
    index1: int
    index2: int

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Swap messages
        dialog.messages[self.index1], dialog.messages[self.index2] = \
            dialog.messages[self.index2], dialog.messages[self.index1]

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Swapped messages [{self.index1}] and [{self.index2}]"

    def undo(self, manager) -> str:
        # Swapping again undoes the swap
        return self.execute(manager)

    def description(self) -> str:
        return f"Swap messages [{self.index1}] <-> [{self.index2}]"


@dataclass
class ReorderMessagesCommand(HistoryCommand):
    """Command for reordering messages."""
    old_order: List[int] = field(default_factory=list)
    new_order: List[int] = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Store old order if not set
        if not self.old_order:
            self.old_order = list(range(len(dialog.messages)))

        # Create new message list in specified order
        old_messages = dialog.messages.copy()
        dialog.messages = [old_messages[i] for i in self.new_order]

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Reordered {len(dialog.messages)} messages"

    def undo(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]

        # Restore old order
        old_messages = dialog.messages.copy()
        dialog.messages = [old_messages[self.new_order.index(i)] for i in self.old_order]

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Restored previous message order"

    def description(self) -> str:
        return f"Reorder messages: {self.new_order}"


@dataclass
class UpdateMessageOutputCommand(HistoryCommand):
    """Specialized command for updating message output (e.g., LLM responses).

    This is separate from UpdateMessageCommand to handle the common case
    of updating a prompt's output after an LLM call.
    """
    msg_index: int
    old_output: str
    new_output: str
    old_time_run: Optional[str] = None
    new_time_run: Optional[str] = None

    def __post_init__(self):
        super().__init__()

    def execute(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]
        msg = dialog.messages[self.msg_index]

        # Store old values if not set
        if self.old_output is None:
            self.old_output = msg.output
        if self.old_time_run is None:
            self.old_time_run = msg.time_run

        # Update output and timestamp
        msg.output = self.new_output
        if self.new_time_run:
            msg.time_run = self.new_time_run

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Updated output for message [{self.msg_index}]"

    def undo(self, manager) -> str:
        dialog = manager.dialogs[manager.active_dialog]
        msg = dialog.messages[self.msg_index]

        # Restore old values
        msg.output = self.old_output
        msg.time_run = self.old_time_run

        # Save dialog
        if dialog.path:
            save_dialog_to_file(dialog, dialog.path)
        dialog.last_activity = datetime.now()

        return f"Restored previous output for message [{self.msg_index}]"

    def description(self) -> str:
        return f"Update output for message [{self.msg_index}]"
