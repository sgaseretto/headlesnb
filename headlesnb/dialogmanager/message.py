"""Message dataclass for dialog messages.

This module defines the Message dataclass used to represent individual
messages within a dialog. Messages can be code, notes, prompts, or raw content.

Example:
    >>> msg = Message(content="print('hello')", msg_type='code')
    >>> msg.id
    '_a1b2c3d4'  # Auto-generated
"""

import secrets
from dataclasses import dataclass, field
from typing import Optional


def generate_msg_id() -> str:
    """Generate a unique message ID.

    IDs follow Jupyter cell ID format: underscore + 8 hex characters.

    Returns:
        Unique ID string like '_a1b2c3d4'.

    Example:
        >>> msg_id = generate_msg_id()
        >>> len(msg_id)
        9
        >>> msg_id[0]
        '_'
    """
    return f"_{secrets.token_hex(4)}"


@dataclass
class Message:
    """A single message in a dialog.

    Messages can be code, notes, prompts, or raw content. Each message
    has metadata controlling its behavior in the dialog and LLM context.

    Attributes:
        id: Unique identifier (8 hex chars with underscore prefix).
        content: Main content (code, markdown, or prompt text).
        msg_type: Type of message. One of 'code', 'note', 'prompt', 'raw',
            or None. None is treated as 'raw' during serialization.
        output: Execution output (JSON for code, markdown for prompts).
        time_run: Timestamp of last execution (e.g., '2:30:45pm').
        is_exported: If 1, export to Python module (code only).
        skipped: If 1, exclude from LLM context.
        pinned: If 1, always include in LLM context.
        i_collapsed: If 1, input is collapsed in UI.
        o_collapsed: If 1, output is collapsed in UI.
        heading_collapsed: If 1, section is collapsed in UI.
        use_thinking: If True, enable extended thinking (prompts only).

    Example:
        >>> msg = Message(
        ...     content="print('hello')",
        ...     msg_type='code'
        ... )
        >>> msg.to_dict()
        {'id': '_a1b2c3d4', 'content': "print('hello')", 'msg_type': 'code', ...}
    """
    content: str = ""
    msg_type: Optional[str] = "note"  # 'code', 'note', 'prompt', 'raw', or None
    output: str = ""
    time_run: Optional[str] = None
    is_exported: int = 0
    skipped: int = 0
    pinned: int = 0
    i_collapsed: int = 0
    o_collapsed: int = 0
    heading_collapsed: int = 0
    use_thinking: bool = False
    id: str = field(default_factory=generate_msg_id)

    def to_dict(self) -> dict:
        """Convert message to dictionary.

        Returns:
            Dictionary with all message fields.
        """
        return {
            'id': self.id,
            'content': self.content,
            'msg_type': self.msg_type,
            'output': self.output,
            'time_run': self.time_run,
            'is_exported': self.is_exported,
            'skipped': self.skipped,
            'pinned': self.pinned,
            'i_collapsed': self.i_collapsed,
            'o_collapsed': self.o_collapsed,
            'heading_collapsed': self.heading_collapsed,
            'use_thinking': self.use_thinking
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        """Create message from dictionary.

        Args:
            data: Dictionary with message fields.

        Returns:
            New Message instance.
        """
        msg = cls()
        for key, value in data.items():
            if hasattr(msg, key):
                setattr(msg, key, value)
        return msg

    def __repr__(self) -> str:
        """Return a concise string representation."""
        content_preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"Message(id='{self.id}', type='{self.msg_type}', content='{content_preview}')"
