"""Comprehensive tests for DialogManager.

Tests cover:
- Dialog lifecycle (use/unuse/list)
- Message operations (add/update/delete/read)
- Serialization roundtrip
- Undo/redo operations
- LLM prompt execution with mock client
- Context building
"""

import pytest
import json
import tempfile
from pathlib import Path

from headlesnb.dialogmanager import (
    DialogManager,
    DialogInfo,
    Message,
    generate_msg_id,
    dialog_to_notebook,
    notebook_to_dialog,
    message_to_cell,
    cell_to_message,
    get_cell_type,
)
from headlesnb.dialogmanager.llm import (
    MockLLMClient,
    MockLLMResponse,
    LLMResponse,
    ContextBuilder,
    create_mock_for_tool_use,
)


# ================== Fixtures ==================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_client():
    """Create a mock LLM client."""
    return MockLLMClient(responses=[
        "This is a test response.",
        "This is another response.",
        "Third response here."
    ])


@pytest.fixture
def manager(temp_dir, mock_client):
    """Create a DialogManager with mock client."""
    return DialogManager(
        root_path=str(temp_dir),
        default_llm_client=mock_client
    )


@pytest.fixture
def dialog_with_messages(manager, temp_dir):
    """Create a dialog with various message types."""
    manager.use_dialog('test', 'test.ipynb', mode='create')
    manager.add_message("# Test Dialog\nThis is a note.", msg_type='note')
    manager.add_message("import pandas as pd\ndf = pd.DataFrame()", msg_type='code')
    manager.add_message("What does this code do?", msg_type='prompt')
    return manager


# ================== Message Tests ==================

class TestMessage:
    """Tests for Message dataclass."""

    def test_generate_msg_id(self):
        """Test unique message ID generation."""
        id1 = generate_msg_id()
        id2 = generate_msg_id()

        assert id1.startswith('_')
        assert len(id1) == 9
        assert id1 != id2

    def test_message_defaults(self):
        """Test message default values."""
        msg = Message()

        assert msg.content == ""
        assert msg.msg_type == "note"
        assert msg.output == ""
        assert msg.skipped == 0
        assert msg.pinned == 0
        assert msg.id.startswith('_')

    def test_message_to_dict(self):
        """Test message to dictionary conversion."""
        msg = Message(content="test", msg_type="code", pinned=1)
        d = msg.to_dict()

        assert d['content'] == "test"
        assert d['msg_type'] == "code"
        assert d['pinned'] == 1

    def test_message_from_dict(self):
        """Test message creation from dictionary."""
        data = {
            'id': '_abc12345',
            'content': 'Hello',
            'msg_type': 'prompt',
            'pinned': 1
        }
        msg = Message.from_dict(data)

        assert msg.id == '_abc12345'
        assert msg.content == 'Hello'
        assert msg.msg_type == 'prompt'
        assert msg.pinned == 1


# ================== Serialization Tests ==================

class TestSerialization:
    """Tests for dialog serialization."""

    def test_get_cell_type(self):
        """Test message type to cell type conversion."""
        assert get_cell_type('code') == 'code'
        assert get_cell_type('note') == 'markdown'
        assert get_cell_type('prompt') == 'markdown'
        assert get_cell_type('raw') == 'raw'
        assert get_cell_type(None) == 'raw'
        assert get_cell_type('unknown') == 'raw'

    def test_code_message_roundtrip(self):
        """Test code message serialization roundtrip."""
        msg = Message(
            content="print('hello')",
            msg_type='code',
            output='[{"output_type": "stream", "name": "stdout", "text": ["hello\\n"]}]'
        )

        cell = message_to_cell(msg)
        recovered = cell_to_message(cell)

        assert recovered.msg_type == 'code'
        assert recovered.content == msg.content
        assert json.loads(recovered.output) == json.loads(msg.output)

    def test_note_message_roundtrip(self):
        """Test note message serialization roundtrip."""
        msg = Message(
            content="# Heading\nThis is a note.",
            msg_type='note'
        )

        cell = message_to_cell(msg)
        recovered = cell_to_message(cell)

        assert recovered.msg_type == 'note'
        assert recovered.content == msg.content
        # Note cells should NOT have solveit_ai
        assert 'solveit_ai' not in cell.get('metadata', {})

    def test_prompt_message_roundtrip(self):
        """Test prompt message serialization roundtrip."""
        msg = Message(
            content="What is Python?",
            msg_type='prompt',
            output="Python is a programming language."
        )

        cell = message_to_cell(msg)
        recovered = cell_to_message(cell)

        assert recovered.msg_type == 'prompt'
        assert recovered.content == msg.content
        assert recovered.output == msg.output
        # Prompt cells MUST have solveit_ai
        assert cell['metadata'].get('solveit_ai') == True
        # Check separator is in source
        source = ''.join(cell['source'])
        assert 'SOLVEIT_SEPARATOR_' in source

    def test_raw_message_roundtrip(self):
        """Test raw/None message serialization."""
        msg = Message(
            content="Some raw content",
            msg_type=None
        )

        cell = message_to_cell(msg)
        recovered = cell_to_message(cell)

        assert cell['cell_type'] == 'raw'
        assert recovered.msg_type == 'raw'
        assert recovered.content == msg.content

    def test_dialog_to_notebook(self):
        """Test full dialog to notebook conversion."""
        dialog = DialogInfo(name='test', mode='learning')
        dialog.messages = [
            Message(content='print(1)', msg_type='code'),
            Message(content='# Note', msg_type='note'),
            Message(content='Question?', msg_type='prompt', output='Answer.')
        ]

        nb = dialog_to_notebook(dialog)

        assert nb['nbformat'] == 4
        assert nb['metadata']['solveit_dialog_mode'] == 'learning'
        assert len(nb['cells']) == 3
        assert nb['cells'][0]['cell_type'] == 'code'
        assert nb['cells'][1]['cell_type'] == 'markdown'
        assert nb['cells'][2]['cell_type'] == 'markdown'
        assert nb['cells'][2]['metadata'].get('solveit_ai') == True

    def test_notebook_to_dialog(self):
        """Test notebook to dialog conversion."""
        nb = {
            'nbformat': 4,
            'nbformat_minor': 5,
            'metadata': {
                'solveit_dialog_mode': 'concise',
                'solveit_ver': 2
            },
            'cells': [
                {
                    'cell_type': 'code',
                    'source': ['x = 1'],
                    'outputs': [],
                    'metadata': {'id': 'abc123'}
                },
                {
                    'cell_type': 'markdown',
                    'source': ['# Note'],
                    'metadata': {'id': 'def456'}
                }
            ]
        }

        dialog = notebook_to_dialog(nb, 'test')

        assert dialog.name == 'test'
        assert dialog.mode == 'concise'
        assert len(dialog.messages) == 2
        assert dialog.messages[0].msg_type == 'code'
        assert dialog.messages[1].msg_type == 'note'


# ================== DialogManager Tests ==================

class TestDialogManager:
    """Tests for DialogManager core functionality."""

    def test_use_dialog_create(self, manager, temp_dir):
        """Test creating a new dialog."""
        result = manager.use_dialog('test', 'test.ipynb', mode='create')

        assert "activated" in result
        assert 'test' in manager.dialogs
        assert manager.active_dialog == 'test'
        assert (temp_dir / 'test.ipynb').exists()

    def test_use_dialog_connect(self, manager, temp_dir):
        """Test connecting to existing dialog."""
        # First create
        manager.use_dialog('test', 'test.ipynb', mode='create')
        manager.add_message("Hello", msg_type='note')
        manager.unuse_dialog('test')

        # Then connect
        result = manager.use_dialog('test2', 'test.ipynb', mode='connect')

        assert "activated" in result
        assert 'test2' in manager.dialogs
        assert len(manager.dialogs['test2'].messages) == 1

    def test_use_dialog_already_in_use(self, manager):
        """Test error when dialog already in use."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        result = manager.use_dialog('test', 'test2.ipynb', mode='create')

        assert "already in use" in result

    def test_unuse_dialog(self, manager, temp_dir):
        """Test releasing a dialog."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        manager.add_message("Hello", msg_type='note')

        result = manager.unuse_dialog('test')

        assert "released" in result
        assert 'test' not in manager.dialogs
        # File should be saved
        assert (temp_dir / 'test.ipynb').exists()

    def test_list_dialogs(self, manager):
        """Test listing active dialogs."""
        manager.use_dialog('dialog1', 'dialog1.ipynb', mode='create')
        manager.use_dialog('dialog2', 'dialog2.ipynb', mode='create')

        result = manager.list_dialogs()

        assert 'dialog1' in result
        assert 'dialog2' in result

    def test_set_active_dialog(self, manager):
        """Test switching active dialog."""
        manager.use_dialog('dialog1', 'dialog1.ipynb', mode='create')
        manager.use_dialog('dialog2', 'dialog2.ipynb', mode='create')

        assert manager.active_dialog == 'dialog2'

        manager.set_active_dialog('dialog1')

        assert manager.active_dialog == 'dialog1'


class TestMessageOperations:
    """Tests for message CRUD operations."""

    def test_add_message(self, manager):
        """Test adding messages."""
        manager.use_dialog('test', 'test.ipynb', mode='create')

        msg_id = manager.add_message("Hello", msg_type='note')

        assert msg_id.startswith('_')
        assert len(manager.dialogs['test'].messages) == 1
        assert manager.dialogs['test'].messages[0].content == "Hello"

    def test_add_message_types(self, manager):
        """Test adding different message types."""
        manager.use_dialog('test', 'test.ipynb', mode='create')

        manager.add_message("print(1)", msg_type='code')
        manager.add_message("# Note", msg_type='note')
        manager.add_message("Question?", msg_type='prompt')
        manager.add_message("Raw", msg_type='raw')

        msgs = manager.dialogs['test'].messages
        assert msgs[0].msg_type == 'code'
        assert msgs[1].msg_type == 'note'
        assert msgs[2].msg_type == 'prompt'
        assert msgs[3].msg_type == 'raw'

    def test_add_message_at_index(self, manager):
        """Test inserting message at specific index."""
        manager.use_dialog('test', 'test.ipynb', mode='create')

        manager.add_message("First", msg_type='note')
        manager.add_message("Third", msg_type='note')
        manager.add_message("Second", msg_type='note', index=1)

        msgs = manager.dialogs['test'].messages
        assert msgs[0].content == "First"
        assert msgs[1].content == "Second"
        assert msgs[2].content == "Third"

    def test_update_message_content(self, manager):
        """Test updating message content."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        msg_id = manager.add_message("Original", msg_type='note')

        manager.update_message(msg_id, content="Updated")

        assert manager.dialogs['test'].messages[0].content == "Updated"

    def test_update_message_attributes(self, manager):
        """Test updating message attributes."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        msg_id = manager.add_message("Note", msg_type='note')

        manager.update_message(msg_id, pinned=1, skipped=1)

        msg = manager.dialogs['test'].messages[0]
        assert msg.pinned == 1
        assert msg.skipped == 1

    def test_delete_message(self, manager):
        """Test deleting messages."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        msg_id = manager.add_message("To delete", msg_type='note')

        result = manager.delete_message(msg_id)

        assert "Deleted" in result
        assert len(manager.dialogs['test'].messages) == 0

    def test_delete_multiple_messages(self, manager):
        """Test deleting multiple messages."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        id1 = manager.add_message("First", msg_type='note')
        id2 = manager.add_message("Second", msg_type='note')
        id3 = manager.add_message("Third", msg_type='note')

        manager.delete_message([id1, id3])

        assert len(manager.dialogs['test'].messages) == 1
        assert manager.dialogs['test'].messages[0].id == id2

    def test_read_message(self, manager):
        """Test reading a message."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        msg_id = manager.add_message("Content", msg_type='note')

        result = manager.read_message(msg_id=msg_id)

        assert result['msg']['content'] == "Content"
        assert result['index'] == 0

    def test_list_messages(self, dialog_with_messages):
        """Test listing messages."""
        result = dialog_with_messages.list_messages()

        assert "note" in result
        assert "code" in result
        assert "prompt" in result


# ================== Undo/Redo Tests ==================

class TestUndoRedo:
    """Tests for undo/redo functionality."""

    def test_undo_add_message(self, manager):
        """Test undoing message addition."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        manager.add_message("Hello", msg_type='note')

        assert len(manager.dialogs['test'].messages) == 1

        manager.undo()

        assert len(manager.dialogs['test'].messages) == 0

    def test_redo_add_message(self, manager):
        """Test redoing message addition."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        manager.add_message("Hello", msg_type='note')
        manager.undo()

        assert len(manager.dialogs['test'].messages) == 0

        manager.redo()

        assert len(manager.dialogs['test'].messages) == 1

    def test_undo_delete_message(self, manager):
        """Test undoing message deletion."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        msg_id = manager.add_message("Hello", msg_type='note')
        manager.delete_message(msg_id)

        assert len(manager.dialogs['test'].messages) == 0

        manager.undo()

        assert len(manager.dialogs['test'].messages) == 1
        assert manager.dialogs['test'].messages[0].content == "Hello"

    def test_undo_multiple_operations(self, manager):
        """Test undoing multiple operations."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        manager.add_message("First", msg_type='note')
        manager.add_message("Second", msg_type='note')
        manager.add_message("Third", msg_type='note')

        manager.undo(steps=2)

        assert len(manager.dialogs['test'].messages) == 1
        assert manager.dialogs['test'].messages[0].content == "First"

    def test_get_history(self, manager):
        """Test getting operation history."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        manager.add_message("Hello", msg_type='note')

        result = manager.get_history()

        assert "Undo available: 1" in result
        assert "Insert" in result


# ================== LLM Tests ==================

class TestMockLLMClient:
    """Tests for MockLLMClient."""

    def test_basic_response(self, mock_client):
        """Test basic chat response."""
        response = mock_client.chat([{"role": "user", "content": "Hi"}])

        assert response.content == "This is a test response."
        assert response.stop_reason == 'end_turn'

    def test_response_cycling(self, mock_client):
        """Test response cycling through list."""
        r1 = mock_client.chat([{"role": "user", "content": "1"}])
        r2 = mock_client.chat([{"role": "user", "content": "2"}])
        r3 = mock_client.chat([{"role": "user", "content": "3"}])
        r4 = mock_client.chat([{"role": "user", "content": "4"}])

        assert r1.content == "This is a test response."
        assert r2.content == "This is another response."
        assert r3.content == "Third response here."
        assert r4.content == "This is a test response."  # Cycles back

    def test_call_history(self, mock_client):
        """Test call history recording."""
        mock_client.chat([{"role": "user", "content": "Hello"}], system_prompt="Be helpful")

        assert len(mock_client.call_history) == 1
        assert mock_client.call_history[0]['system_prompt'] == "Be helpful"

    def test_tool_use_response(self):
        """Test mock with tool calls."""
        client = MockLLMClient(responses=[
            MockLLMResponse(
                content="Calling tool...",
                tool_calls=[{"name": "get_data", "input": {"id": "1"}}],
                stop_reason="tool_use"
            )
        ])

        response = client.chat([{"role": "user", "content": "Get data"}])

        assert response.tool_calls is not None
        assert response.tool_calls[0]['name'] == 'get_data'
        assert response.stop_reason == 'tool_use'

    def test_create_mock_for_tool_use(self):
        """Test helper for tool use flow."""
        client = create_mock_for_tool_use(
            'get_weather',
            {'city': 'NYC'},
            'The weather is sunny.'
        )

        r1 = client.chat([{"role": "user", "content": "Weather?"}])
        r2 = client.chat([{"role": "user", "content": "OK"}])

        assert r1.tool_calls is not None
        assert r1.tool_calls[0]['name'] == 'get_weather'
        assert r2.content == 'The weather is sunny.'


class TestPromptExecution:
    """Tests for prompt execution."""

    def test_execute_prompt(self, dialog_with_messages, mock_client):
        """Test executing a prompt message."""
        response = dialog_with_messages.execute_prompt()

        assert response.content == "This is a test response."

        # Check message was updated
        prompt_msg = dialog_with_messages.dialogs['test'].get_messages_by_type('prompt')[0]
        assert prompt_msg.output == "This is a test response."
        assert prompt_msg.time_run is not None

    def test_execute_prompt_by_id(self, manager, mock_client):
        """Test executing specific prompt by ID."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        manager.add_message("Question 1?", msg_type='prompt')
        msg_id = manager.add_message("Question 2?", msg_type='prompt')

        response = manager.execute_prompt(msg_id=msg_id)

        # Second prompt should have response
        dialog = manager.dialogs['test']
        assert dialog.messages[0].output == ""  # First prompt unchanged
        assert dialog.messages[1].output == "This is a test response."

    def test_execute_prompt_with_context(self, manager, mock_client):
        """Test context is included in prompt."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        manager.add_message("x = 1", msg_type='code')
        manager.add_message("What is x?", msg_type='prompt')

        manager.execute_prompt(system_prompt="You are helpful")

        # Check system prompt was passed
        assert mock_client.call_history[0]['system_prompt'] == "You are helpful"
        # Check messages include context
        messages = mock_client.call_history[0]['messages']
        assert len(messages) >= 1  # At least the prompt


class TestContextBuilder:
    """Tests for ContextBuilder."""

    def test_basic_context_building(self):
        """Test basic context building."""
        builder = ContextBuilder(max_tokens=100000)
        messages = [
            Message(content="Hello", msg_type='note'),
            Message(content="print(1)", msg_type='code'),
        ]

        context = builder.build_context(messages, current_prompt="Question?")

        assert len(context) >= 2
        assert context[-1]['content'] == "Question?"

    def test_skipped_messages_excluded(self):
        """Test skipped messages are not included."""
        builder = ContextBuilder(max_tokens=100000)
        messages = [
            Message(content="Include", msg_type='note'),
            Message(content="Skip this", msg_type='note', skipped=1),
        ]

        context = builder.build_context(messages)

        # Only non-skipped message should be included
        content_texts = [m['content'] for m in context]
        assert any('Include' in c for c in content_texts)
        assert not any('Skip this' in c for c in content_texts)

    def test_pinned_messages_always_included(self):
        """Test pinned messages are always included."""
        builder = ContextBuilder(max_tokens=100)  # Small budget
        messages = [
            Message(content="A" * 1000, msg_type='note'),  # Large
            Message(content="Important", msg_type='note', pinned=1),
        ]

        context = builder.build_context(messages)

        # Pinned should be included even with tight budget
        content_texts = [m['content'] for m in context]
        assert any('Important' in c for c in content_texts)


# ================== Code Execution Tests ==================

class TestCodeExecution:
    """Tests for code execution in dialogs."""

    def test_execute_code_directly(self, manager):
        """Test executing code directly."""
        manager.use_dialog('test', 'test.ipynb', mode='create')

        result = manager.execute_code("x = 1 + 1\nprint(x)")

        assert any("2" in str(r) for r in result)

    def test_execute_code_message(self, manager):
        """Test executing a code message by ID."""
        manager.use_dialog('test', 'test.ipynb', mode='create')
        msg_id = manager.add_message("y = 42\nprint(y)", msg_type='code')

        result = manager.execute_code(msg_id=msg_id)

        assert any("42" in str(r) for r in result)

        # Output should be stored in message
        msg = manager.dialogs['test'].messages[0]
        assert msg.output != ""


# ================== Integration Tests ==================

class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_dialog_workflow(self, manager, temp_dir):
        """Test complete dialog workflow."""
        # Create dialog
        manager.use_dialog('analysis', 'analysis.ipynb', mode='create')

        # Add messages
        manager.add_message("# Data Analysis", msg_type='note')
        code_id = manager.add_message("data = [1, 2, 3]\nprint(sum(data))", msg_type='code')
        prompt_id = manager.add_message("Explain this code", msg_type='prompt')

        # Execute code
        code_result = manager.execute_code(msg_id=code_id)
        assert any("6" in str(r) for r in code_result)

        # Execute prompt
        prompt_result = manager.execute_prompt(msg_id=prompt_id)
        assert prompt_result.content  # Should have response

        # Save and reload
        manager.unuse_dialog('analysis')
        manager.use_dialog('analysis2', 'analysis.ipynb', mode='connect')

        # Verify persistence
        dialog = manager.dialogs['analysis2']
        assert len(dialog.messages) == 3
        assert dialog.messages[0].msg_type == 'note'
        assert dialog.messages[1].msg_type == 'code'
        assert dialog.messages[2].msg_type == 'prompt'
        assert dialog.messages[2].output  # Prompt output should be saved

    def test_undo_redo_persistence(self, manager, temp_dir):
        """Test undo/redo with save/load cycle."""
        manager.use_dialog('test', 'test.ipynb', mode='create')

        # Make changes
        manager.add_message("One", msg_type='note')
        manager.add_message("Two", msg_type='note')

        # Undo
        manager.undo()
        assert len(manager.dialogs['test'].messages) == 1

        # Save and reload
        manager.unuse_dialog('test')
        manager.use_dialog('test2', 'test.ipynb', mode='connect')

        # State should be persisted (only one message)
        assert len(manager.dialogs['test2'].messages) == 1
        assert manager.dialogs['test2'].messages[0].content == "One"
