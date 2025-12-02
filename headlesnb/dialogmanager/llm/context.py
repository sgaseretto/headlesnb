"""Context window management for LLM calls.

This module provides utilities for building context windows from dialog
messages, respecting token budgets and message flags (pinned/skipped).

Example:
    >>> builder = ContextBuilder(max_tokens=100000)
    >>> messages = builder.build_context(dialog.messages, current_prompt)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json

from ..message import Message
from .base import LLMClient


@dataclass
class ContextBudget:
    """Track token budget usage.

    Attributes:
        max_tokens: Maximum tokens allowed.
        used_tokens: Tokens currently used.
        reserved_tokens: Tokens reserved for response.
    """
    max_tokens: int
    used_tokens: int = 0
    reserved_tokens: int = 4096  # Default response buffer

    @property
    def available(self) -> int:
        """Get remaining available tokens."""
        return self.max_tokens - self.used_tokens - self.reserved_tokens

    def can_fit(self, tokens: int) -> bool:
        """Check if tokens can fit in remaining budget."""
        return tokens <= self.available

    def consume(self, tokens: int) -> bool:
        """Consume tokens from budget. Returns True if successful."""
        if self.can_fit(tokens):
            self.used_tokens += tokens
            return True
        return False


class ContextBuilder:
    """Build LLM context windows from dialog messages.

    Handles:
    - Pinned messages (always included)
    - Skipped messages (never included)
    - Token budget management
    - Message ordering and formatting

    Attributes:
        llm_client: Client for token counting.
        max_tokens: Maximum context window size.

    Example:
        >>> builder = ContextBuilder(max_tokens=100000)
        >>> messages = builder.build_context(
        ...     dialog_messages=dialog.messages,
        ...     current_prompt="What does this code do?",
        ...     include_outputs=True
        ... )
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_tokens: int = 200000
    ):
        """Initialize the context builder.

        Args:
            llm_client: LLM client for token counting. If None, uses
                character-based estimation (4 chars = 1 token).
            max_tokens: Maximum tokens for context window.
        """
        self.llm_client = llm_client
        self.max_tokens = max_tokens

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Uses LLM client if available, otherwise estimates.

        Args:
            text: Text to count tokens for.

        Returns:
            Token count.
        """
        if self.llm_client:
            return self.llm_client.count_tokens(text)
        # Fallback: ~4 characters per token
        return len(text) // 4

    def build_context(
        self,
        dialog_messages: List[Message],
        current_prompt: Optional[str] = None,
        include_outputs: bool = True,
        system_prompt: str = "",
        reserved_tokens: int = 4096
    ) -> List[Dict[str, Any]]:
        """Build context for LLM from dialog messages.

        Strategy:
        1. Always include pinned messages
        2. Skip messages marked as skipped
        3. Include recent messages newest-first until budget exhausted
        4. Current prompt goes last

        Args:
            dialog_messages: List of Message objects from dialog.
            current_prompt: Current user prompt (optional).
            include_outputs: Whether to include message outputs.
            system_prompt: System prompt (for budget calculation).
            reserved_tokens: Tokens to reserve for response.

        Returns:
            List of message dictionaries for LLM API.
        """
        budget = ContextBudget(
            max_tokens=self.max_tokens,
            reserved_tokens=reserved_tokens
        )

        # Account for system prompt
        if system_prompt:
            budget.consume(self.count_tokens(system_prompt))

        result_messages: List[Dict[str, Any]] = []

        # Separate pinned vs regular messages
        pinned_messages = []
        regular_messages = []

        for msg in dialog_messages:
            if msg.skipped:
                continue  # Skip messages marked as skipped
            if msg.pinned:
                pinned_messages.append(msg)
            else:
                regular_messages.append(msg)

        # Always include pinned messages first
        for msg in pinned_messages:
            formatted = self._format_message(msg, include_outputs)
            tokens = self.count_tokens(self._message_to_text(formatted))
            budget.consume(tokens)  # Pinned always included
            result_messages.append(formatted)

        # Add regular messages newest-first until budget exhausted
        # (but we'll reverse at the end to maintain order)
        regular_to_include = []
        for msg in reversed(regular_messages):
            formatted = self._format_message(msg, include_outputs)
            tokens = self.count_tokens(self._message_to_text(formatted))
            if budget.can_fit(tokens):
                budget.consume(tokens)
                regular_to_include.append(formatted)

        # Reverse to maintain chronological order
        regular_to_include.reverse()

        # Insert regular messages after pinned ones
        # Actually, we should maintain original order
        # So let's rebuild in proper order

        # Build final list maintaining original message order
        final_messages = []
        included_ids = {msg['id'] for msg in result_messages}
        regular_ids = {self._get_msg_id(m) for m in regular_to_include}

        for msg in dialog_messages:
            if msg.skipped:
                continue
            msg_id = msg.id
            if msg.pinned and msg_id in included_ids:
                # Find the formatted pinned message
                for fmt in result_messages:
                    if fmt.get('id') == msg_id:
                        final_messages.append(fmt)
                        break
            elif msg_id in regular_ids:
                # Find the formatted regular message
                for fmt in regular_to_include:
                    if self._get_msg_id(fmt) == msg_id:
                        final_messages.append(fmt)
                        break

        # Convert to LLM format (removing our internal 'id' field)
        llm_messages = []
        for msg in final_messages:
            llm_msg = {k: v for k, v in msg.items() if k != 'id'}
            llm_messages.append(llm_msg)

        # Add current prompt if provided
        if current_prompt:
            llm_messages.append({
                'role': 'user',
                'content': current_prompt
            })

        return llm_messages

    def _format_message(
        self,
        msg: Message,
        include_outputs: bool = True
    ) -> Dict[str, Any]:
        """Format a message for LLM context.

        Args:
            msg: Message to format.
            include_outputs: Whether to include outputs.

        Returns:
            Dictionary with 'role', 'content', and 'id' keys.
        """
        if msg.msg_type == 'code':
            # Code messages become user messages with output
            content = f"```python\n{msg.content}\n```"
            if include_outputs and msg.output:
                try:
                    outputs = json.loads(msg.output)
                    output_text = self._format_code_output(outputs)
                    if output_text:
                        content += f"\n\nOutput:\n```\n{output_text}\n```"
                except json.JSONDecodeError:
                    pass
            return {
                'role': 'user',
                'content': content,
                'id': msg.id
            }

        elif msg.msg_type == 'prompt':
            # Prompt messages: content is user, output is assistant
            messages = [{
                'role': 'user',
                'content': msg.content,
                'id': msg.id
            }]
            if msg.output:
                messages.append({
                    'role': 'assistant',
                    'content': msg.output,
                    'id': f"{msg.id}_response"
                })
            # For simplicity, return just the user part
            # The caller should handle assistant responses
            return messages[0]

        elif msg.msg_type == 'note':
            # Note messages become user context
            return {
                'role': 'user',
                'content': f"[Note]\n{msg.content}",
                'id': msg.id
            }

        else:
            # Raw or unknown - include as context
            return {
                'role': 'user',
                'content': msg.content,
                'id': msg.id
            }

    def _format_code_output(self, outputs: List[Dict]) -> str:
        """Format code cell outputs for context.

        Args:
            outputs: List of output dictionaries.

        Returns:
            Formatted output string.
        """
        result = []
        for output in outputs:
            output_type = output.get('output_type', '')

            if output_type == 'stream':
                text = ''.join(output.get('text', []))
                result.append(text)

            elif output_type in ('execute_result', 'display_data'):
                data = output.get('data', {})
                if 'text/plain' in data:
                    result.append(''.join(data['text/plain']))

            elif output_type == 'error':
                ename = output.get('ename', 'Error')
                evalue = output.get('evalue', '')
                result.append(f"{ename}: {evalue}")

        return '\n'.join(result)

    def _message_to_text(self, msg: Dict[str, Any]) -> str:
        """Convert message dict to text for token counting.

        Args:
            msg: Message dictionary.

        Returns:
            Text representation.
        """
        content = msg.get('content', '')
        if isinstance(content, list):
            return ' '.join(
                item.get('text', '') if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content)

    def _get_msg_id(self, msg: Dict[str, Any]) -> str:
        """Get message ID from formatted message."""
        return msg.get('id', '')

    def build_context_with_prompt_response(
        self,
        dialog_messages: List[Message],
        system_prompt: str = "",
        reserved_tokens: int = 4096
    ) -> List[Dict[str, Any]]:
        """Build context including prompt/response pairs.

        This method properly handles prompt messages by including
        both the user prompt and assistant response.

        Args:
            dialog_messages: List of Message objects.
            system_prompt: System prompt.
            reserved_tokens: Tokens to reserve.

        Returns:
            List of message dictionaries with proper user/assistant pairing.
        """
        budget = ContextBudget(
            max_tokens=self.max_tokens,
            reserved_tokens=reserved_tokens
        )

        if system_prompt:
            budget.consume(self.count_tokens(system_prompt))

        result: List[Dict[str, Any]] = []

        for msg in dialog_messages:
            if msg.skipped:
                continue

            if msg.msg_type == 'prompt':
                # Add user message
                user_msg = {'role': 'user', 'content': msg.content}
                user_tokens = self.count_tokens(msg.content)

                # Add assistant response if present
                if msg.output:
                    assistant_msg = {'role': 'assistant', 'content': msg.output}
                    assistant_tokens = self.count_tokens(msg.output)
                    total_tokens = user_tokens + assistant_tokens

                    if msg.pinned or budget.can_fit(total_tokens):
                        budget.consume(total_tokens)
                        result.append(user_msg)
                        result.append(assistant_msg)
                else:
                    if msg.pinned or budget.can_fit(user_tokens):
                        budget.consume(user_tokens)
                        result.append(user_msg)

            elif msg.msg_type == 'code':
                formatted = self._format_message(msg, include_outputs=True)
                tokens = self.count_tokens(formatted['content'])
                if msg.pinned or budget.can_fit(tokens):
                    budget.consume(tokens)
                    result.append({'role': 'user', 'content': formatted['content']})

            elif msg.msg_type == 'note':
                content = f"[Note]\n{msg.content}"
                tokens = self.count_tokens(content)
                if msg.pinned or budget.can_fit(tokens):
                    budget.consume(tokens)
                    result.append({'role': 'user', 'content': content})

        return result
