"""DialogManager - Manager for dialog-based AI conversations.

This module provides DialogManager, which extends notebook functionality
with AI-assisted conversations through prompt messages.

Example:
    >>> from headlesnb.dialogmanager import DialogManager
    >>> from headlesnb.dialogmanager.llm import MockLLMClient
    >>>
    >>> manager = DialogManager(
    ...     root_path='/path/to/dialogs',
    ...     default_llm_client=MockLLMClient(responses=["Hello!"])
    ... )
    >>> manager.use_dialog('test', 'test.ipynb', mode='create')
    >>> manager.add_message("What is Python?", msg_type='prompt')
    >>> response = manager.execute_prompt()
"""

import threading
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from execnb.shell import CaptureShell

from .message import Message, generate_msg_id
from .dialog_info import DialogInfo
from .serialization import (
    dialog_to_notebook,
    notebook_to_dialog,
    save_dialog_to_file,
    load_dialog_from_file
)
from .dialog_history import (
    InsertMessageCommand,
    DeleteMessageCommand,
    UpdateMessageCommand,
    MoveMessageCommand,
    SwapMessagesCommand,
    ReorderMessagesCommand,
    UpdateMessageOutputCommand
)
from .llm import LLMClient, LLMResponse, MockLLMClient, ContextBuilder


class DialogManager:
    """Manager for dialog-based AI conversations.

    DialogManager provides:
    - Create/load/save dialogs (stored as .ipynb files)
    - Add/edit/delete messages of various types
    - Execute code messages
    - Execute prompts via LLM
    - Undo/redo support for all operations
    - Context window management for LLM calls

    Attributes:
        root_path: Base path for file operations.
        dialogs: Dictionary of active dialogs.
        active_dialog: Name of currently active dialog.

    Example:
        >>> manager = DialogManager('/notebooks')
        >>> manager.use_dialog('analysis', 'analysis.ipynb', mode='create')
        >>> manager.add_message("import pandas as pd", msg_type='code')
        >>> manager.add_message("Explain this import", msg_type='prompt')
        >>> response = manager.execute_prompt()
    """

    def __init__(
        self,
        root_path: str = ".",
        default_llm_client: Optional[LLMClient] = None
    ):
        """Initialize the DialogManager.

        Args:
            root_path: Root directory for file operations.
            default_llm_client: Default LLM client for prompt execution.
                If None, uses MockLLMClient.
        """
        self.root_path = Path(root_path).resolve()
        self.dialogs: Dict[str, DialogInfo] = {}
        self.active_dialog: Optional[str] = None
        self._lock = threading.Lock()
        self._default_llm_client = default_llm_client or MockLLMClient()
        self._context_builder = ContextBuilder(
            llm_client=self._default_llm_client
        )

    # ================== Dialog Management ==================

    def use_dialog(
        self,
        dialog_name: str,
        dialog_path: str,
        mode: str = "connect",
        llm_client: Optional[LLMClient] = None
    ) -> str:
        """Use a dialog and activate it.

        Args:
            dialog_name: Unique identifier for the dialog.
            dialog_path: Path to the dialog file (.ipynb).
            mode: 'connect' to load existing, 'create' to create new.
            llm_client: LLM client for this dialog (uses default if None).

        Returns:
            Success message with dialog information.
        """
        with self._lock:
            full_path = self.root_path / dialog_path

            if dialog_name in self.dialogs:
                return f"Error: Dialog '{dialog_name}' is already in use."

            if mode == "create":
                if full_path.exists():
                    return f"Error: Dialog '{dialog_path}' already exists."
                dialog = DialogInfo(
                    name=dialog_name,
                    path=full_path,
                    shell=CaptureShell(path=full_path.parent),
                    llm_client=llm_client or self._default_llm_client,
                    is_active=True
                )
                # Create parent directory if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)
                save_dialog_to_file(dialog, full_path)

            elif mode == "connect":
                if not full_path.exists():
                    return f"Error: Dialog '{dialog_path}' not found."
                dialog = load_dialog_from_file(full_path, dialog_name)
                dialog.shell = CaptureShell(path=full_path.parent)
                dialog.llm_client = llm_client or self._default_llm_client
                dialog.is_active = True

            else:
                return f"Error: Invalid mode '{mode}'."

            self.dialogs[dialog_name] = dialog
            self.active_dialog = dialog_name

            # Get overview
            msg_count = len(dialog.messages)
            code_msgs = len(dialog.get_messages_by_type('code'))
            prompt_msgs = len(dialog.get_messages_by_type('prompt'))
            note_msgs = len(dialog.get_messages_by_type('note'))

            return (
                f"Dialog '{dialog_name}' activated\n"
                f"Path: {dialog_path}\n"
                f"Mode: {mode}\n"
                f"Messages: {msg_count} ({code_msgs} code, {prompt_msgs} prompt, {note_msgs} note)\n"
                f"Dialog mode: {dialog.mode}"
            )

    def unuse_dialog(self, dialog_name: str) -> str:
        """Release a dialog and save it.

        Args:
            dialog_name: Name of dialog to release.

        Returns:
            Success message.
        """
        with self._lock:
            if dialog_name not in self.dialogs:
                return f"Error: Dialog '{dialog_name}' not found"

            dialog = self.dialogs[dialog_name]
            if dialog.path:
                save_dialog_to_file(dialog, dialog.path)

            del self.dialogs[dialog_name]

            if self.active_dialog == dialog_name:
                self.active_dialog = next(iter(self.dialogs.keys()), None)

            return f"Dialog '{dialog_name}' released"

    def list_dialogs(self) -> str:
        """List all active dialogs.

        Returns:
            TSV formatted table with dialog information.
        """
        header = "Name\tPath\tMessages\tMode\tActive"

        if not self.dialogs:
            return header + "\n(No dialogs in use)"

        rows = []
        for dialog in self.dialogs.values():
            active_mark = "*" if dialog.is_active else ""
            rel_path = dialog.path.relative_to(self.root_path) if dialog.path else "(memory)"
            rows.append(
                f"{dialog.name}\t{rel_path}\t{len(dialog.messages)}\t"
                f"{dialog.mode}\t{active_mark}"
            )

        return header + "\n" + "\n".join(rows)

    def set_active_dialog(self, dialog_name: str) -> str:
        """Set a different dialog as active.

        Args:
            dialog_name: Name of dialog to activate.

        Returns:
            Success message.
        """
        if dialog_name not in self.dialogs:
            return f"Error: Dialog '{dialog_name}' not found"

        if self.active_dialog:
            self.dialogs[self.active_dialog].is_active = False

        self.active_dialog = dialog_name
        self.dialogs[dialog_name].is_active = True

        return f"Dialog '{dialog_name}' is now active"

    def get_active_dialog(self) -> Optional[str]:
        """Get name of currently active dialog."""
        return self.active_dialog

    # ================== Message Operations ==================

    def add_message(
        self,
        content: str,
        msg_type: str = "note",
        index: int = -1,
        **kwargs
    ) -> str:
        """Add a message to the active dialog.

        Args:
            content: Message content.
            msg_type: Type ('code', 'note', 'prompt', 'raw').
            index: Position to insert (-1 for append).
            **kwargs: Additional message attributes (pinned, skipped, etc.).

        Returns:
            Message ID of the new message.
        """
        if not self.active_dialog:
            return "Error: No active dialog. Use use_dialog first."

        dialog = self.dialogs[self.active_dialog]

        # Create message
        msg = Message(
            content=content,
            msg_type=msg_type,
            **kwargs
        )

        # Create and execute command
        command = InsertMessageCommand(msg_index=index, message=msg)

        try:
            command.execute(self)
            dialog.history.add_command(command)
            dialog.current_msg_id = msg.id
            return msg.id
        except Exception as e:
            return f"Error adding message: {str(e)}"

    def update_message(
        self,
        msg_id: str,
        content: Optional[str] = None,
        output: Optional[str] = None,
        **kwargs
    ) -> str:
        """Update a message's content or attributes.

        Args:
            msg_id: ID of message to update.
            content: New content (if provided).
            output: New output (if provided).
            **kwargs: Other attributes to update.

        Returns:
            Success message.
        """
        if not self.active_dialog:
            return "Error: No active dialog."

        dialog = self.dialogs[self.active_dialog]
        msg_index = dialog.get_message_index(msg_id)

        if msg_index is None:
            return f"Error: Message '{msg_id}' not found"

        msg = dialog.messages[msg_index]

        # Update content if provided
        if content is not None:
            old_content = msg.content
            command = UpdateMessageCommand(
                msg_index=msg_index,
                field_name='content',
                old_value=old_content,
                new_value=content
            )
            try:
                command.execute(self)
                dialog.history.add_command(command)
            except Exception as e:
                return f"Error updating content: {str(e)}"

        # Update output if provided
        if output is not None:
            old_output = msg.output
            command = UpdateMessageOutputCommand(
                msg_index=msg_index,
                old_output=old_output,
                new_output=output,
                new_time_run=datetime.now().strftime("%I:%M:%S%p").lower()
            )
            try:
                command.execute(self)
                dialog.history.add_command(command)
            except Exception as e:
                return f"Error updating output: {str(e)}"

        # Update other attributes
        for key, value in kwargs.items():
            if hasattr(msg, key):
                old_value = getattr(msg, key)
                command = UpdateMessageCommand(
                    msg_index=msg_index,
                    field_name=key,
                    old_value=old_value,
                    new_value=value
                )
                try:
                    command.execute(self)
                    dialog.history.add_command(command)
                except Exception as e:
                    return f"Error updating {key}: {str(e)}"

        return f"Message '{msg_id}' updated"

    def delete_message(self, msg_ids: Union[str, List[str]]) -> str:
        """Delete messages from the active dialog.

        Args:
            msg_ids: Single message ID or list of IDs.

        Returns:
            Success message.
        """
        if not self.active_dialog:
            return "Error: No active dialog."

        dialog = self.dialogs[self.active_dialog]

        # Normalize to list
        if isinstance(msg_ids, str):
            msg_ids = [msg_ids]

        # Convert IDs to indices
        indices = []
        for msg_id in msg_ids:
            idx = dialog.get_message_index(msg_id)
            if idx is not None:
                indices.append(idx)

        if not indices:
            return "Error: No valid message IDs provided"

        command = DeleteMessageCommand(msg_indices=indices)

        try:
            command.execute(self)
            dialog.history.add_command(command)
            return f"Deleted {len(indices)} message(s)"
        except Exception as e:
            return f"Error deleting messages: {str(e)}"

    def read_message(
        self,
        msg_id: Optional[str] = None,
        index: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read a message from the active dialog.

        Args:
            msg_id: Message ID (preferred).
            index: Message index (if ID not provided).

        Returns:
            Dictionary with message information.
        """
        if not self.active_dialog:
            return {"error": "No active dialog"}

        dialog = self.dialogs[self.active_dialog]

        if msg_id:
            msg = dialog.get_message_by_id(msg_id)
            if not msg:
                return {"error": f"Message '{msg_id}' not found"}
        elif index is not None:
            if 0 <= index < len(dialog.messages):
                msg = dialog.messages[index]
            else:
                return {"error": f"Index {index} out of range"}
        else:
            return {"error": "Provide msg_id or index"}

        return {
            "msg": msg.to_dict(),
            "index": dialog.get_message_index(msg.id)
        }

    def list_messages(
        self,
        start_index: int = 0,
        limit: int = 20,
        msg_type: Optional[str] = None
    ) -> str:
        """List messages in the active dialog.

        Args:
            start_index: Starting index for pagination.
            limit: Maximum messages to return.
            msg_type: Filter by message type.

        Returns:
            Formatted message list.
        """
        if not self.active_dialog:
            return "Error: No active dialog"

        dialog = self.dialogs[self.active_dialog]

        # Filter by type if specified
        if msg_type:
            messages = dialog.get_messages_by_type(msg_type)
        else:
            messages = dialog.messages

        total = len(messages)
        end_index = min(start_index + limit, total)
        page = messages[start_index:end_index]

        header = f"Messages {start_index}-{end_index-1} of {total}\n"
        header += "Index\tID\tType\tPinned\tSkipped\tContent_Preview"

        rows = []
        for i, msg in enumerate(page, start=start_index):
            preview = msg.content[:40].replace('\n', ' ') + "..." if len(msg.content) > 40 else msg.content.replace('\n', ' ')
            pinned = "*" if msg.pinned else ""
            skipped = "x" if msg.skipped else ""
            rows.append(f"{i}\t{msg.id}\t{msg.msg_type}\t{pinned}\t{skipped}\t{preview}")

        return header + "\n" + "\n".join(rows)

    # ================== Code Execution ==================

    def execute_code(
        self,
        code: Optional[str] = None,
        msg_id: Optional[str] = None,
        timeout: int = 30
    ) -> List[Union[str, Dict]]:
        """Execute code in the dialog's kernel.

        Args:
            code: Code to execute directly.
            msg_id: ID of code message to execute.
            timeout: Execution timeout in seconds.

        Returns:
            List of outputs.
        """
        if not self.active_dialog:
            return ["Error: No active dialog"]

        dialog = self.dialogs[self.active_dialog]

        # Get code to execute
        if msg_id:
            msg = dialog.get_message_by_id(msg_id)
            if not msg:
                return [f"Error: Message '{msg_id}' not found"]
            if msg.msg_type != 'code':
                return [f"Error: Message is not a code message (type: {msg.msg_type})"]
            code = msg.content

        if not code:
            return ["Error: No code provided"]

        try:
            outputs = dialog.shell.run(code, timeout=min(timeout, 60))
            dialog.last_activity = datetime.now()

            # Store outputs in message if executing by ID
            if msg_id and msg:
                msg.output = json.dumps(outputs)
                msg.time_run = datetime.now().strftime("%I:%M:%S%p").lower()
                if dialog.path:
                    save_dialog_to_file(dialog, dialog.path)

            return self._format_outputs(outputs)

        except TimeoutError:
            return [f"Error: Execution timed out after {timeout}s"]
        except Exception as e:
            return [f"Error: {str(e)}"]

    # ================== Prompt Execution ==================

    def execute_prompt(
        self,
        msg_id: Optional[str] = None,
        system_prompt: str = "",
        max_tokens: int = 4096,
        include_context: bool = True,
        stream: bool = False
    ) -> LLMResponse:
        """Execute a prompt message via LLM.

        Args:
            msg_id: ID of prompt message to execute. If None, uses
                the last prompt message without output.
            system_prompt: System prompt for LLM.
            max_tokens: Maximum response tokens.
            include_context: Include prior messages as context.
            stream: Enable streaming response.

        Returns:
            LLMResponse with the response.
        """
        if not self.active_dialog:
            return LLMResponse(content="Error: No active dialog")

        dialog = self.dialogs[self.active_dialog]
        llm = dialog.llm_client or self._default_llm_client

        # Find prompt message
        if msg_id:
            msg = dialog.get_message_by_id(msg_id)
            if not msg:
                return LLMResponse(content=f"Error: Message '{msg_id}' not found")
            if msg.msg_type != 'prompt':
                return LLMResponse(content=f"Error: Message is not a prompt (type: {msg.msg_type})")
        else:
            # Find last prompt without output
            msg = None
            for m in reversed(dialog.messages):
                if m.msg_type == 'prompt' and not m.output:
                    msg = m
                    break
            if not msg:
                return LLMResponse(content="Error: No pending prompt found")

        # Build context
        if include_context:
            msg_index = dialog.get_message_index(msg.id)
            prior_messages = dialog.messages[:msg_index]
            context = self._context_builder.build_context_with_prompt_response(
                prior_messages,
                system_prompt=system_prompt
            )
            # Add current prompt
            context.append({'role': 'user', 'content': msg.content})
        else:
            context = [{'role': 'user', 'content': msg.content}]

        # Execute LLM call
        try:
            response = llm.chat(
                messages=context,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                stream=stream
            )

            # Handle streaming
            if stream:
                # Collect stream into response
                content = ''.join(response)
                response = LLMResponse(content=content, stop_reason='end_turn')

            # Update message with response
            msg.output = response.content
            msg.time_run = datetime.now().strftime("%I:%M:%S%p").lower()

            # Save dialog
            if dialog.path:
                save_dialog_to_file(dialog, dialog.path)
            dialog.last_activity = datetime.now()

            return response

        except Exception as e:
            return LLMResponse(content=f"Error: {str(e)}")

    # ================== Undo/Redo Operations ==================

    def undo(self, steps: int = 1) -> str:
        """Undo the last N operations.

        Args:
            steps: Number of operations to undo.

        Returns:
            Summary of undone operations.
        """
        if not self.active_dialog:
            return "Error: No active dialog"

        dialog = self.dialogs[self.active_dialog]

        if not dialog.history.can_undo():
            return "Nothing to undo"

        descriptions = dialog.history.get_undo_description(steps)

        try:
            results = dialog.history.undo(self, steps)
            summary = f"Undid {len(results)} operation(s):\n"
            for desc in descriptions[:len(results)]:
                summary += f"  - {desc}\n"
            return summary.rstrip()
        except Exception as e:
            return f"Error during undo: {str(e)}"

    def redo(self, steps: int = 1) -> str:
        """Redo the last N undone operations.

        Args:
            steps: Number of operations to redo.

        Returns:
            Summary of redone operations.
        """
        if not self.active_dialog:
            return "Error: No active dialog"

        dialog = self.dialogs[self.active_dialog]

        if not dialog.history.can_redo():
            return "Nothing to redo"

        descriptions = dialog.history.get_redo_description(steps)

        try:
            results = dialog.history.redo(self, steps)
            summary = f"Redid {len(results)} operation(s):\n"
            for desc in descriptions[:len(results)]:
                summary += f"  - {desc}\n"
            return summary.rstrip()
        except Exception as e:
            return f"Error during redo: {str(e)}"

    def get_history(self) -> str:
        """Get operation history for active dialog.

        Returns:
            Formatted history summary.
        """
        if not self.active_dialog:
            return "Error: No active dialog"

        dialog = self.dialogs[self.active_dialog]
        summary = dialog.history.get_history_summary()

        result = f"History for '{self.active_dialog}':\n"
        result += f"  Undo available: {summary['undo_count']}\n"
        result += f"  Redo available: {summary['redo_count']}\n"

        if summary['recent_operations']:
            result += "\nRecent:\n"
            for i, op in enumerate(summary['recent_operations'], 1):
                result += f"  {i}. {op}\n"

        return result.rstrip()

    def clear_history(self) -> str:
        """Clear operation history."""
        if not self.active_dialog:
            return "Error: No active dialog"

        self.dialogs[self.active_dialog].history.clear()
        return f"History cleared for '{self.active_dialog}'"

    # ================== Message Reordering ==================

    def move_message(self, from_index: int, to_index: int) -> str:
        """Move a message to a new position.

        Args:
            from_index: Current position.
            to_index: Target position.

        Returns:
            Success message.
        """
        if not self.active_dialog:
            return "Error: No active dialog"

        dialog = self.dialogs[self.active_dialog]

        if not (0 <= from_index < len(dialog.messages)):
            return f"Error: from_index {from_index} out of range"
        if not (0 <= to_index < len(dialog.messages)):
            return f"Error: to_index {to_index} out of range"
        if from_index == to_index:
            return "No move needed"

        command = MoveMessageCommand(from_index=from_index, to_index=to_index)

        try:
            command.execute(self)
            dialog.history.add_command(command)
            return f"Moved message from {from_index} to {to_index}"
        except Exception as e:
            return f"Error: {str(e)}"

    def swap_messages(self, index1: int, index2: int) -> str:
        """Swap two messages.

        Args:
            index1: First message index.
            index2: Second message index.

        Returns:
            Success message.
        """
        if not self.active_dialog:
            return "Error: No active dialog"

        dialog = self.dialogs[self.active_dialog]

        if not (0 <= index1 < len(dialog.messages)):
            return f"Error: index1 {index1} out of range"
        if not (0 <= index2 < len(dialog.messages)):
            return f"Error: index2 {index2} out of range"
        if index1 == index2:
            return "No swap needed"

        command = SwapMessagesCommand(index1=index1, index2=index2)

        try:
            command.execute(self)
            dialog.history.add_command(command)
            return f"Swapped messages at {index1} and {index2}"
        except Exception as e:
            return f"Error: {str(e)}"

    # ================== Helper Methods ==================

    def _format_outputs(self, outputs: List) -> List[Union[str, Dict]]:
        """Format execution outputs for display."""
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

    def restart_kernel(self, dialog_name: Optional[str] = None) -> str:
        """Restart the kernel for a dialog.

        Args:
            dialog_name: Dialog to restart (uses active if None).

        Returns:
            Success message.
        """
        name = dialog_name or self.active_dialog
        if not name:
            return "Error: No dialog specified"

        if name not in self.dialogs:
            return f"Error: Dialog '{name}' not found"

        dialog = self.dialogs[name]
        if dialog.shell:
            dialog.shell.restart_kernel()
            dialog.last_activity = datetime.now()
            return f"Kernel restarted for '{name}'"
        return f"Error: No kernel for '{name}'"
