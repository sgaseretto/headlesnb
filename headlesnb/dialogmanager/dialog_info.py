"""DialogInfo dataclass for dialog metadata.

This module defines the DialogInfo dataclass that extends ManagedItemInfo
with dialog-specific fields.

Example:
    >>> dialog = DialogInfo(
    ...     name='analysis',
    ...     mode='learning',
    ... )
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from pathlib import Path
from datetime import datetime

from execnb.shell import CaptureShell

from ..history import OperationHistory
from .message import Message


@dataclass
class DialogInfo:
    """Information about a managed dialog.

    Extends ManagedItemInfo with dialog-specific fields for message
    management and LLM interaction.

    Attributes:
        name: Unique identifier for this dialog.
        path: File system path where dialog is stored. None for in-memory dialogs.
        shell: CaptureShell instance for code execution. None if not needed.
        history: Operation history for undo/redo support.
        created_at: Timestamp when dialog was created or loaded.
        last_activity: Timestamp of most recent modification.
        is_active: Whether this dialog is currently the active/focused dialog.
        messages: List of Message objects in the dialog.
        mode: Dialog mode (e.g., 'learning', 'concise').
        version: Solveit format version (currently 2).
        current_msg_id: ID of the currently focused message.
        llm_client: LLM client for prompt execution. Can be None,
            MockLLMClient (for testing), or ClaudetteLLMClient (for production).

    Example:
        >>> dialog = DialogInfo(
        ...     name='analysis',
        ...     mode='learning',
        ... )
    """
    name: str
    path: Optional[Path] = None
    shell: Optional[CaptureShell] = None
    history: OperationHistory = field(default_factory=lambda: OperationHistory(max_size=100))
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = False
    messages: List[Message] = field(default_factory=list)
    mode: str = "default"
    version: int = 2
    current_msg_id: Optional[str] = None
    llm_client: Optional[Any] = None

    def get_message_by_id(self, msg_id: str) -> Optional[Message]:
        """Get a message by its ID.

        Args:
            msg_id: The ID of the message to find.

        Returns:
            The Message with the given ID, or None if not found.
        """
        for msg in self.messages:
            if msg.id == msg_id:
                return msg
        return None

    def get_message_index(self, msg_id: str) -> Optional[int]:
        """Get the index of a message by its ID.

        Args:
            msg_id: The ID of the message to find.

        Returns:
            The index of the message, or None if not found.
        """
        for i, msg in enumerate(self.messages):
            if msg.id == msg_id:
                return i
        return None

    def message_count(self) -> int:
        """Get the total number of messages.

        Returns:
            Number of messages in the dialog.
        """
        return len(self.messages)

    def get_messages_by_type(self, msg_type: str) -> List[Message]:
        """Get all messages of a specific type.

        Args:
            msg_type: The type of messages to find ('code', 'note', 'prompt', 'raw').

        Returns:
            List of messages with the given type.
        """
        return [msg for msg in self.messages if msg.msg_type == msg_type]
