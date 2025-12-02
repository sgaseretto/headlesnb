"""Mock LLM client for testing.

This module provides MockLLMClient, which simulates LLM responses without
making actual API calls. Useful for testing dialog flows.

Example:
    >>> client = MockLLMClient(responses=["Hello!", "How can I help?"])
    >>> response = client.chat([{"role": "user", "content": "Hi"}])
    >>> response.content
    'Hello!'
"""

from typing import List, Dict, Any, Optional, Iterator, Union
from dataclasses import dataclass, field

from .base import LLMClient, LLMResponse


@dataclass
class MockLLMResponse:
    """Configuration for a mock response.

    Use this to specify responses with tool calls or specific metadata.

    Attributes:
        content: Text content of the response.
        tool_calls: Optional list of tool calls.
        stop_reason: Why response ended. Defaults to 'end_turn'.

    Example:
        >>> response = MockLLMResponse(
        ...     content="I'll check that order for you.",
        ...     tool_calls=[{"name": "get_order", "input": {"id": "O1"}}]
        ... )
    """
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    stop_reason: str = "end_turn"


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API calls.

    This client cycles through predefined responses, making it easy to
    test dialog flows without incurring API costs or network latency.

    Attributes:
        responses: List of responses to cycle through.
        call_history: Record of all calls made for assertions.

    Example:
        >>> # Simple usage with string responses
        >>> client = MockLLMClient(responses=["Hello!", "How can I help?"])
        >>> response = client.chat([{"role": "user", "content": "Hi"}])
        >>> response.content
        'Hello!'

        >>> # With tool calls
        >>> client = MockLLMClient(responses=[
        ...     MockLLMResponse(
        ...         content="Checking order...",
        ...         tool_calls=[{"name": "get_order", "input": {"id": "O1"}}],
        ...         stop_reason="tool_use"
        ...     ),
        ...     "Order O1 is shipped."
        ... ])
    """

    def __init__(
        self,
        responses: Optional[List[Union[str, MockLLMResponse]]] = None,
        default_response: str = "Mock response",
        context_window_size: int = 200000
    ):
        """Initialize the mock client.

        Args:
            responses: List of responses to cycle through. Can be strings
                or MockLLMResponse objects for more control.
            default_response: Response to use if responses list is empty.
            context_window_size: Simulated context window size.
        """
        self.responses = responses or []
        self.default_response = default_response
        self._context_window = context_window_size
        self._response_index = 0
        self.call_history: List[Dict[str, Any]] = []

    def chat(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Any]] = None,
        max_tokens: int = 4096,
        temperature: float = 0,
        stream: bool = False
    ) -> Union[LLMResponse, Iterator[str]]:
        """Return the next mock response.

        Args:
            messages: List of message dictionaries (recorded in history).
            system_prompt: System prompt (recorded in history).
            tools: Tool definitions (recorded in history).
            max_tokens: Max tokens (recorded in history).
            temperature: Temperature (recorded in history).
            stream: If True, yield response character by character.

        Returns:
            LLMResponse or iterator of strings if streaming.
        """
        # Record the call
        self.call_history.append({
            'messages': messages,
            'system_prompt': system_prompt,
            'tools': tools,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': stream
        })

        # Get response (cycle through list)
        if self.responses:
            response = self.responses[self._response_index % len(self.responses)]
            self._response_index += 1
        else:
            response = self.default_response

        # Normalize to LLMResponse
        if isinstance(response, str):
            llm_response = LLMResponse(
                content=response,
                stop_reason='end_turn',
                model='mock-model',
                usage={'input_tokens': 100, 'output_tokens': 50}
            )
        elif isinstance(response, MockLLMResponse):
            llm_response = LLMResponse(
                content=response.content,
                tool_calls=response.tool_calls,
                stop_reason=response.stop_reason,
                model='mock-model',
                usage={'input_tokens': 100, 'output_tokens': 50}
            )
        else:
            llm_response = response

        if stream:
            return self._stream_response(llm_response.content)
        return llm_response

    def _stream_response(self, content: str) -> Iterator[str]:
        """Yield response content character by character.

        Args:
            content: Content to stream.

        Yields:
            Individual characters from content.
        """
        for char in content:
            yield char

    def count_tokens(self, text: str) -> int:
        """Estimate tokens (4 chars per token).

        Args:
            text: Text to count.

        Returns:
            Estimated token count.
        """
        return len(text) // 4

    @property
    def context_window(self) -> int:
        """Get mock context window size."""
        return self._context_window

    # ================== Testing Utilities ==================

    def reset(self):
        """Reset call history and response index."""
        self.call_history = []
        self._response_index = 0

    def assert_called_times(self, n: int):
        """Assert the client was called exactly n times.

        Args:
            n: Expected number of calls.

        Raises:
            AssertionError: If call count doesn't match.
        """
        assert len(self.call_history) == n, \
            f"Expected {n} calls, got {len(self.call_history)}"

    def assert_last_message_contains(self, text: str):
        """Assert the last user message contains text.

        Args:
            text: Text to search for.

        Raises:
            AssertionError: If text not found.
        """
        if not self.call_history:
            raise AssertionError("No calls recorded")

        last_call = self.call_history[-1]
        for msg in reversed(last_call['messages']):
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                if isinstance(content, str) and text in content:
                    return
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and text in item.get('text', ''):
                            return

        raise AssertionError(f"'{text}' not found in last user message")

    def get_all_user_messages(self) -> List[str]:
        """Get all user messages sent to the client.

        Returns:
            List of user message contents.
        """
        messages = []
        for call in self.call_history:
            for msg in call['messages']:
                if msg.get('role') == 'user':
                    content = msg.get('content', '')
                    if isinstance(content, str):
                        messages.append(content)
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                messages.append(item['text'])
        return messages

    def get_last_system_prompt(self) -> Optional[str]:
        """Get the system prompt from the last call.

        Returns:
            System prompt string, or None if no calls recorded.
        """
        if not self.call_history:
            return None
        return self.call_history[-1].get('system_prompt', '')


def create_mock_for_tool_use(
    tool_name: str,
    tool_input: Dict[str, Any],
    final_response: str
) -> MockLLMClient:
    """Create a mock client that simulates a tool use flow.

    The mock will first return a tool call, then the final response.

    Args:
        tool_name: Name of the tool to call.
        tool_input: Input arguments for the tool.
        final_response: Response after tool execution.

    Returns:
        Configured MockLLMClient.

    Example:
        >>> client = create_mock_for_tool_use(
        ...     'get_weather',
        ...     {'city': 'NYC'},
        ...     'The weather in NYC is sunny.'
        ... )
    """
    return MockLLMClient(responses=[
        MockLLMResponse(
            content=f"I'll use the {tool_name} tool.",
            tool_calls=[{
                'name': tool_name,
                'input': tool_input,
                'id': f'call_{tool_name}'
            }],
            stop_reason='tool_use'
        ),
        final_response
    ])
