"""LLM client abstraction layer.

This module defines the abstract interface for LLM clients, allowing
easy swapping between mock clients (for testing) and real clients
(for production).

Example:
    >>> # For testing
    >>> client = MockLLMClient(responses=["Hello!", "How can I help?"])
    >>>
    >>> # For production (when claudette is available)
    >>> client = ClaudetteLLMClient(model='claude-3-5-sonnet-latest')
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator, Union


@dataclass
class LLMResponse:
    """Response from an LLM call.

    Attributes:
        content: The text content of the response.
        tool_calls: List of tool calls requested by the LLM, if any.
        usage: Token usage statistics.
        model: Model identifier that generated the response.
        stop_reason: Why the response ended ('end_turn', 'tool_use', etc).

    Example:
        >>> response = LLMResponse(
        ...     content="Hello! How can I help?",
        ...     stop_reason='end_turn',
        ...     model='claude-3-5-sonnet',
        ...     usage={'input_tokens': 10, 'output_tokens': 5}
        ... )
    """
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    stop_reason: Optional[str] = None


class LLMClient(ABC):
    """Abstract base class for LLM clients.

    This interface allows swapping between different LLM implementations:
    - MockLLMClient for testing (no API calls)
    - ClaudetteLLMClient for production (uses claudette.Chat)

    Example:
        >>> # For testing
        >>> client = MockLLMClient(responses=["Hello!", "How can I help?"])
        >>>
        >>> # For production
        >>> client = ClaudetteLLMClient(model='claude-3-5-sonnet-latest')
    """

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Any]] = None,
        max_tokens: int = 4096,
        temperature: float = 0,
        stream: bool = False
    ) -> Union[LLMResponse, Iterator[str]]:
        """Send messages to the LLM and get a response.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            system_prompt: System prompt to set context.
            tools: List of tool definitions for function calling.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0 = deterministic).
            stream: If True, return an iterator of chunks.

        Returns:
            LLMResponse object, or iterator of strings if streaming.
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to count tokens for.

        Returns:
            Estimated token count.
        """
        pass

    @property
    @abstractmethod
    def context_window(self) -> int:
        """Get the model's context window size.

        Returns:
            Maximum tokens the model can process.
        """
        pass
