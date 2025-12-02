"""DialogManager package for AI-assisted dialog notebooks.

This package provides DialogManager, a manager for dialog-based AI conversations
stored as Jupyter notebooks with extended metadata.

Key components:
- DialogManager: Main manager class for dialogs
- Message: Individual message dataclass
- DialogInfo: Dialog metadata and state
- LLM clients: MockLLMClient for testing, LLMClient interface

Example:
    >>> from headlesnb.dialogmanager import DialogManager, Message
    >>> from headlesnb.dialogmanager.llm import MockLLMClient
    >>>
    >>> # Create manager with mock LLM for testing
    >>> manager = DialogManager(
    ...     root_path='/notebooks',
    ...     default_llm_client=MockLLMClient(responses=["Hello!"])
    ... )
    >>>
    >>> # Create a new dialog
    >>> manager.use_dialog('chat', 'chat.ipynb', mode='create')
    >>>
    >>> # Add messages
    >>> manager.add_message("import pandas as pd", msg_type='code')
    >>> manager.add_message("What does pandas do?", msg_type='prompt')
    >>>
    >>> # Execute the prompt
    >>> response = manager.execute_prompt()
"""

from .message import Message, generate_msg_id
from .dialog_info import DialogInfo
from .manager import DialogManager
from .serialization import (
    dialog_to_notebook,
    notebook_to_dialog,
    save_dialog_to_file,
    load_dialog_from_file,
    message_to_cell,
    cell_to_message,
    get_cell_type,
    generate_separator
)

__all__ = [
    # Core classes
    'DialogManager',
    'DialogInfo',
    'Message',
    'generate_msg_id',
    # Serialization
    'dialog_to_notebook',
    'notebook_to_dialog',
    'save_dialog_to_file',
    'load_dialog_from_file',
    'message_to_cell',
    'cell_to_message',
    'get_cell_type',
    'generate_separator',
]
