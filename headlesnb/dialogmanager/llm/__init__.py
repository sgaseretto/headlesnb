"""LLM client abstractions for DialogManager.

This package provides abstract and concrete LLM client implementations:
- LLMClient: Abstract base class defining the interface
- LLMResponse: Response dataclass
- MockLLMClient: Testing client with predefined responses
- ContextBuilder: Build context windows from dialog messages
"""

from .base import LLMClient, LLMResponse
from .mock import MockLLMClient, MockLLMResponse, create_mock_for_tool_use
from .context import ContextBuilder

__all__ = [
    'LLMClient',
    'LLMResponse',
    'MockLLMClient',
    'MockLLMResponse',
    'create_mock_for_tool_use',
    'ContextBuilder',
]
