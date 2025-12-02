"""Dialog serialization - convert between Dialog and Notebook formats.

This module handles bidirectional conversion between the in-memory Dialog
representation and the .ipynb notebook format used for persistence.

Key features:
- Supports all four message types (code, note, prompt, raw)
- Handles None/missing msg_type as 'raw'
- Preserves all metadata through round-trips
- Uses special separator for prompt content/output

Example:
    >>> from headlesnb.dialogmanager.serialization import dialog_to_notebook, notebook_to_dialog
    >>> nb_dict = dialog_to_notebook(dialog)
    >>> recovered = notebook_to_dialog(nb_dict, 'my_dialog')
"""

import json
import re
import secrets
from typing import Optional, Dict, Any, List
from pathlib import Path

from .message import Message
from .dialog_info import DialogInfo


# Regex to match and split on the AI reply separator
SEPARATOR_PATTERN = re.compile(r'##### 🤖Reply🤖<!-- SOLVEIT_SEPARATOR_[a-f0-9]+ -->')


def generate_separator() -> str:
    """Generate a unique separator token for prompt messages.

    The separator marks the boundary between user prompt and AI response
    in the serialized notebook format.

    Returns:
        Separator string like '##### Reply<!-- SOLVEIT_SEPARATOR_7f3a9b2c -->'.

    Example:
        >>> sep = generate_separator()
        >>> 'SOLVEIT_SEPARATOR_' in sep
        True
    """
    token = secrets.token_hex(4)
    return f"##### 🤖Reply🤖<!-- SOLVEIT_SEPARATOR_{token} -->"


def get_cell_type(msg_type: Optional[str]) -> str:
    """Convert message type to notebook cell type.

    This function handles the mapping between dialog message types and
    Jupyter notebook cell types, including the case where msg_type is
    None or missing.

    Args:
        msg_type: The message type. One of 'code', 'note', 'prompt',
            'raw', or None.

    Returns:
        The corresponding notebook cell type:
        - 'code' for code messages
        - 'markdown' for note and prompt messages
        - 'raw' for raw messages or when msg_type is None/unknown

    Example:
        >>> get_cell_type('code')
        'code'
        >>> get_cell_type('note')
        'markdown'
        >>> get_cell_type(None)
        'raw'
        >>> get_cell_type('unknown_type')
        'raw'
    """
    if msg_type is None or msg_type == 'raw':
        return 'raw'
    elif msg_type == 'code':
        return 'code'
    elif msg_type in ('note', 'prompt'):
        return 'markdown'
    else:
        return 'raw'  # Unknown types default to raw


def message_to_cell(msg: Message) -> dict:
    """Convert a Message to a notebook cell dictionary.

    Handles all message types including code, note, prompt, and raw.
    For prompt messages, combines content and output with a separator.

    Args:
        msg: The Message to convert.

    Returns:
        Dictionary representing a notebook cell.

    Example:
        >>> msg = Message(content='print(1)', msg_type='code')
        >>> cell = message_to_cell(msg)
        >>> cell['cell_type']
        'code'
    """
    cell_type = get_cell_type(msg.msg_type)

    # Base cell structure
    cell = {
        'cell_type': cell_type,
        'metadata': {'id': msg.id.lstrip('_')},  # Remove underscore for notebook ID
        'source': []
    }

    if cell_type == 'code':
        # Code cell
        cell['source'] = _text_to_source_list(msg.content)
        cell['outputs'] = json.loads(msg.output) if msg.output else []
        cell['execution_count'] = None

        # Code-specific metadata
        if msg.time_run:
            cell['metadata']['time_run'] = msg.time_run
        if msg.is_exported:
            cell['metadata']['is_exported'] = msg.is_exported
        if msg.skipped:
            cell['metadata']['skipped'] = msg.skipped
        if msg.pinned:
            cell['metadata']['pinned'] = msg.pinned
        if msg.i_collapsed:
            cell['metadata']['i_collapsed'] = msg.i_collapsed
        if msg.o_collapsed:
            cell['metadata']['o_collapsed'] = msg.o_collapsed

    elif cell_type == 'markdown':
        if msg.msg_type == 'prompt':
            # Prompt cell - combine content and output with separator
            cell['metadata']['solveit_ai'] = True
            if msg.use_thinking:
                cell['metadata']['use_thinking'] = msg.use_thinking
            if msg.time_run:
                cell['metadata']['time_run'] = msg.time_run

            # Build source with separator
            separator = generate_separator()
            source_text = msg.content
            if msg.output:
                source_text += f"\n\n{separator}\n\n{msg.output}"
            cell['source'] = _text_to_source_list(source_text)
        else:
            # Note cell - plain markdown, NO solveit_ai
            cell['source'] = _text_to_source_list(msg.content)

        if msg.heading_collapsed:
            cell['metadata']['collapsed'] = msg.heading_collapsed
        if msg.pinned:
            cell['metadata']['pinned'] = msg.pinned
        if msg.skipped:
            cell['metadata']['skipped'] = msg.skipped

    else:
        # Raw cell
        cell['source'] = _text_to_source_list(msg.content)

    return cell


def cell_to_message(cell: dict) -> Message:
    """Convert a notebook cell dictionary to a Message.

    Handles all cell types and extracts dialog-specific metadata.
    For markdown cells with solveit_ai, splits content and output.

    Args:
        cell: Dictionary representing a notebook cell.

    Returns:
        Message object.

    Example:
        >>> cell = {'cell_type': 'code', 'source': ['print(1)'], ...}
        >>> msg = cell_to_message(cell)
        >>> msg.msg_type
        'code'
    """
    cell_type = cell.get('cell_type', 'raw')
    metadata = cell.get('metadata', {})
    source = _source_list_to_text(cell.get('source', []))

    # Get or generate ID
    cell_id = metadata.get('id', secrets.token_hex(4))
    msg_id = f"_{cell_id}" if not cell_id.startswith('_') else cell_id

    msg = Message(id=msg_id)

    if cell_type == 'code':
        msg.msg_type = 'code'
        msg.content = source
        msg.output = json.dumps(cell.get('outputs', []))
        msg.time_run = metadata.get('time_run')
        msg.is_exported = metadata.get('is_exported', 0)
        msg.skipped = metadata.get('skipped', 0)
        msg.pinned = metadata.get('pinned', 0)
        msg.i_collapsed = metadata.get('i_collapsed', 0)
        msg.o_collapsed = metadata.get('o_collapsed', 0)

    elif cell_type == 'markdown':
        if metadata.get('solveit_ai'):
            # Prompt cell
            msg.msg_type = 'prompt'
            msg.use_thinking = metadata.get('use_thinking', False)
            msg.time_run = metadata.get('time_run')

            # Split on separator
            parts = SEPARATOR_PATTERN.split(source, maxsplit=1)
            msg.content = parts[0].strip()
            msg.output = parts[1].strip() if len(parts) > 1 else ''
        else:
            # Note cell
            msg.msg_type = 'note'
            msg.content = source

        msg.heading_collapsed = metadata.get('collapsed', 0)
        msg.pinned = metadata.get('pinned', 0)
        msg.skipped = metadata.get('skipped', 0)

    elif cell_type == 'raw':
        msg.msg_type = 'raw'
        msg.content = source

    else:
        # Unknown cell type - treat as raw
        msg.msg_type = None  # Will serialize back as 'raw'
        msg.content = source

    return msg


def dialog_to_notebook(dialog: DialogInfo) -> dict:
    """Convert a Dialog to notebook dictionary format.

    Args:
        dialog: The DialogInfo to convert.

    Returns:
        Dictionary in .ipynb format.

    Example:
        >>> dialog = DialogInfo(name='test', mode='learning')
        >>> nb = dialog_to_notebook(dialog)
        >>> nb['metadata']['solveit_dialog_mode']
        'learning'
    """
    cells = [message_to_cell(msg) for msg in dialog.messages]

    return {
        'nbformat': 4,
        'nbformat_minor': 5,
        'metadata': {
            'solveit_dialog_mode': dialog.mode,
            'solveit_ver': dialog.version,
            'kernelspec': {
                'display_name': 'Python 3',
                'language': 'python',
                'name': 'python3'
            },
            'language_info': {
                'name': 'python',
                'version': '3.10.0'
            }
        },
        'cells': cells
    }


def notebook_to_dialog(nb_dict: dict, name: str) -> DialogInfo:
    """Parse a notebook dictionary into a DialogInfo.

    Args:
        nb_dict: Dictionary in .ipynb format.
        name: Name for the dialog.

    Returns:
        DialogInfo with parsed messages.

    Example:
        >>> nb = {'metadata': {'solveit_dialog_mode': 'learning'}, 'cells': []}
        >>> dialog = notebook_to_dialog(nb, 'test')
        >>> dialog.mode
        'learning'
    """
    metadata = nb_dict.get('metadata', {})
    cells = nb_dict.get('cells', [])

    messages = [cell_to_message(cell) for cell in cells]

    return DialogInfo(
        name=name,
        messages=messages,
        mode=metadata.get('solveit_dialog_mode', 'default'),
        version=metadata.get('solveit_ver', 2),
        current_msg_id=messages[-1].id if messages else None
    )


def _text_to_source_list(text: str) -> list:
    """Convert text to notebook source format (list of lines).

    Args:
        text: Text content.

    Returns:
        List of lines with proper newline handling.
    """
    if not text:
        return []
    lines = text.split('\n')
    return [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []


def _source_list_to_text(source: list) -> str:
    """Convert notebook source format to text.

    Args:
        source: List of lines from notebook.

    Returns:
        Joined text content.
    """
    if isinstance(source, str):
        return source
    return ''.join(source)


def save_dialog_to_file(dialog: DialogInfo, path: Path) -> None:
    """Save a dialog to an .ipynb file.

    Args:
        dialog: The DialogInfo to save.
        path: Path to save to.
    """
    nb_dict = dialog_to_notebook(dialog)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb_dict, f, indent=1, ensure_ascii=False)


def load_dialog_from_file(path: Path, name: str) -> DialogInfo:
    """Load a dialog from an .ipynb file.

    Args:
        path: Path to the .ipynb file.
        name: Name for the dialog.

    Returns:
        Loaded DialogInfo.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(path, 'r', encoding='utf-8') as f:
        nb_dict = json.load(f)
    dialog = notebook_to_dialog(nb_dict, name)
    dialog.path = path
    return dialog
