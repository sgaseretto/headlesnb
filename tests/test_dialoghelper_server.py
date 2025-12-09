"""Tests for the dialoghelper FastHTML server.

Tests cover all endpoints that the dialoghelper client library uses,
ensuring compatibility with the expected API.
"""

import pytest
import json
import asyncio
import tempfile
from pathlib import Path
from starlette.testclient import TestClient

from headlesnb.dialoghelper_server import (
    app, init_manager, get_manager, html_queues,
    data_store, data_values
)
from headlesnb.dialogmanager import DialogManager


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """Create temporary directory for dialog files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def setup_manager(temp_dir):
    """Initialize manager with temp directory."""
    mgr = init_manager(root_path=temp_dir)
    mgr.use_dialog('test_dialog', 'test.ipynb', mode='create')
    yield mgr
    # Cleanup
    if 'test_dialog' in mgr.dialogs:
        mgr.unuse_dialog('test_dialog')


class TestCoreEndpoints:
    """Test core dialog and message endpoints."""

    def test_index(self, client):
        """Test health check endpoint."""
        response = client.get('/')
        assert response.status_code == 200

    def test_health(self, client):
        """Test JSON health check."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'

    def test_curr_dialog_no_dialog(self, client):
        """Test curr_dialog_ with no active dialog."""
        init_manager()  # Reset
        response = client.post('/curr_dialog_', data={'dlg_name': ''})
        assert response.status_code == 200
        # Should return empty or error
        data = response.json()
        assert data == {} or 'error' in data

    def test_curr_dialog_with_dialog(self, client, setup_manager):
        """Test curr_dialog_ with active dialog."""
        response = client.post('/curr_dialog_', data={'dlg_name': 'test_dialog'})
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'test_dialog'
        assert 'mode' in data

    def test_curr_dialog_with_messages(self, client, setup_manager):
        """Test curr_dialog_ with messages included."""
        # Add a message first
        setup_manager.add_message("test content", msg_type='note')

        response = client.post('/curr_dialog_', data={
            'dlg_name': 'test_dialog',
            'with_messages': 'true'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'messages' in data
        assert len(data['messages']) >= 1


class TestMessageOperations:
    """Test message CRUD operations."""

    def test_add_relative_at_end(self, client, setup_manager):
        """Test adding message at end."""
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'New message',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        assert response.status_code == 200
        msg_id = response.text
        assert msg_id.startswith('_')

    def test_add_relative_at_start(self, client, setup_manager):
        """Test adding message at start."""
        # Add initial message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'First message',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        first_id = response1.text

        # Add at start
        response2 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'New first message',
            'placement': 'at_start',
            'msg_type': 'note'
        })
        new_first_id = response2.text

        # Verify order
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'n': '0',
            'relative': 'false'
        })
        data = response3.json()
        assert data['msg']['content'] == 'New first message'

    def test_add_relative_after_message(self, client, setup_manager):
        """Test adding message after another."""
        # Add first message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'First',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        first_id = response1.text

        # Add after first
        response2 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'After first',
            'placement': 'add_after',
            'msgid': first_id,
            'msg_type': 'note'
        })
        assert response2.status_code == 200

    def test_read_msg_by_index(self, client, setup_manager):
        """Test reading message by absolute index."""
        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Test content',
            'placement': 'at_end',
            'msg_type': 'code'
        })
        msg_id = response1.text

        # Read by index
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'n': '0',
            'relative': 'false'
        })
        assert response2.status_code == 200
        data = response2.json()
        assert data['msg']['content'] == 'Test content'
        assert data['msg']['msg_type'] == 'code'

    def test_read_msg_with_line_numbers(self, client, setup_manager):
        """Test reading message with line numbers."""
        # Add multiline message
        client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'line1\nline2\nline3',
            'placement': 'at_end',
            'msg_type': 'note'
        })

        response = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'n': '-1',
            'relative': 'false',
            'nums': 'true'
        })
        data = response.json()
        assert '1' in data['msg']['content']  # Line number should be present

    def test_update_msg(self, client, setup_manager):
        """Test updating message content."""
        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Original',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Update
        response2 = client.post('/update_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'content': 'Updated'
        })
        assert response2.status_code == 200

        # Verify
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response3.json()
        assert data['msg']['content'] == 'Updated'

    def test_delete_msg(self, client, setup_manager):
        """Test deleting a message."""
        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'To delete',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Delete (note: API uses 'msid' typo)
        response2 = client.post('/rm_msg_', data={
            'dlg_name': 'test_dialog',
            'msid': msg_id
        })
        assert response2.status_code == 200

        # Verify deleted
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response3.json()
        assert 'error' in data

    def test_find_msgs_by_pattern(self, client, setup_manager):
        """Test finding messages by regex pattern."""
        # Add messages
        client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Hello world',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Goodbye world',
            'placement': 'at_end',
            'msg_type': 'note'
        })

        # Find by pattern
        response = client.post('/find_msgs_', data={
            'dlg_name': 'test_dialog',
            're_pattern': 'Hello'
        })
        data = response.json()
        assert len(data['msgs']) == 1
        assert 'Hello' in data['msgs'][0]['content']

    def test_find_msgs_by_type(self, client, setup_manager):
        """Test finding messages by type."""
        # Add different types
        client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'print("hi")',
            'placement': 'at_end',
            'msg_type': 'code'
        })
        client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'A note',
            'placement': 'at_end',
            'msg_type': 'note'
        })

        # Find only code
        response = client.post('/find_msgs_', data={
            'dlg_name': 'test_dialog',
            'msg_type': 'code'
        })
        data = response.json()
        for msg in data['msgs']:
            assert msg['msg_type'] == 'code'

    def test_msg_idx(self, client, setup_manager):
        """Test getting message index."""
        # Add messages
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'First',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        first_id = response1.text

        response2 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Second',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        second_id = response2.text

        # Get index of second
        response3 = client.post('/msg_idx_', data={
            'dlg_name': 'test_dialog',
            'msgid': second_id
        })
        data = response3.json()
        assert data['msgid'] == 1  # Second message is at index 1


class TestTextEditEndpoints:
    """Test text manipulation endpoints."""

    def test_msg_insert_line(self, client, setup_manager):
        """Test inserting line in message."""
        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'line1\nline2',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Insert at line 1
        response2 = client.post('/msg_insert_line_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'insert_line': '1',
            'new_str': 'inserted'
        })
        assert response2.status_code == 200

        # Verify
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response3.json()
        lines = data['msg']['content'].split('\n')
        assert 'inserted' in lines

    def test_msg_str_replace(self, client, setup_manager):
        """Test string replacement in message."""
        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Hello world',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Replace
        response2 = client.post('/msg_str_replace_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'old_str': 'world',
            'new_str': 'universe'
        })
        assert response2.status_code == 200

        # Verify
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response3.json()
        assert 'universe' in data['msg']['content']
        assert 'world' not in data['msg']['content']

    def test_msg_strs_replace(self, client, setup_manager):
        """Test multiple string replacements."""
        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'foo bar baz',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Replace multiple
        response2 = client.post('/msg_strs_replace_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'old_strs': json.dumps(['foo', 'baz']),
            'new_strs': json.dumps(['FOO', 'BAZ'])
        })
        assert response2.status_code == 200

        # Verify
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response3.json()
        assert 'FOO' in data['msg']['content']
        assert 'BAZ' in data['msg']['content']

    def test_msg_replace_lines(self, client, setup_manager):
        """Test replacing line range."""
        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'line1\nline2\nline3\nline4',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Replace lines 2-3
        response2 = client.post('/msg_replace_lines_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'start_line': '2',
            'end_line': '3',
            'new_content': 'replaced'
        })
        assert response2.status_code == 200

        # Verify
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response3.json()
        lines = data['msg']['content'].split('\n')
        assert len(lines) == 3  # line1, replaced, line4
        assert lines[1] == 'replaced'


class TestDialogManagement:
    """Test dialog management endpoints."""

    def test_use_dialog_create(self, client, temp_dir):
        """Test creating a new dialog."""
        init_manager(root_path=temp_dir)

        response = client.post('/use_dialog_', data={
            'dlg_name': 'new_dialog',
            'dialog_path': 'new.ipynb',
            'mode': 'create'
        })
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'

        # Cleanup
        client.post('/unuse_dialog_', data={'dlg_name': 'new_dialog'})

    def test_use_dialog_connect(self, client, temp_dir):
        """Test connecting to existing dialog."""
        mgr = init_manager(root_path=temp_dir)
        # Create first
        mgr.use_dialog('temp', 'temp.ipynb', mode='create')
        mgr.unuse_dialog('temp')

        # Connect
        response = client.post('/use_dialog_', data={
            'dlg_name': 'reconnect',
            'dialog_path': 'temp.ipynb',
            'mode': 'connect'
        })
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'

    def test_list_dialogs(self, client, setup_manager):
        """Test listing active dialogs."""
        response = client.post('/list_dialogs_')
        assert response.status_code == 200
        data = response.json()
        assert 'dialogs' in data
        assert len(data['dialogs']) >= 1


class TestRunQueue:
    """Test code/prompt execution queue."""

    def test_add_runq_api_mode(self, client, setup_manager):
        """Test adding to run queue in API mode."""
        # Add code message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'print("hello")',
            'placement': 'at_end',
            'msg_type': 'code'
        })
        msg_id = response1.text

        # Add to queue
        response2 = client.post('/add_runq_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'api': 'true'
        })
        assert response2.status_code == 200
        data = response2.json()
        assert data['status'] == 'queued'


class TestDataExchange:
    """Test blocking data exchange endpoints."""

    @pytest.mark.asyncio
    async def test_push_pop_data(self, client):
        """Test pushing and popping data."""
        data_id = 'test_data_123'

        # Push data
        response1 = client.post('/push_data_', data={
            'data_id': data_id,
            'data': json.dumps({'key': 'value'})
        })
        assert response1.status_code == 200

        # Pop data
        response2 = client.post('/pop_data_blocking_', data={
            'data_id': data_id,
            'timeout': '5'
        })
        assert response2.status_code == 200
        data = response2.json()
        assert data['key'] == 'value'

    def test_pop_data_timeout(self, client):
        """Test pop data timeout."""
        response = client.post('/pop_data_blocking_', data={
            'data_id': 'nonexistent_12345',
            'timeout': '1'
        })
        data = response.json()
        assert 'error' in data
        assert 'timeout' in data['error']


class TestErrorHandling:
    """Test error handling for edge cases."""

    def test_invalid_dialog_name(self, client):
        """Test accessing non-existent dialog."""
        init_manager()  # Reset

        response = client.post('/read_msg_', data={
            'dlg_name': 'nonexistent',
            'n': '0',
            'relative': 'false'
        })
        data = response.json()
        assert 'error' in data

    def test_invalid_message_id(self, client, setup_manager):
        """Test accessing non-existent message."""
        response = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': '_nonexistent123',
            'n': '0',
            'relative': 'true'
        })
        data = response.json()
        assert 'error' in data

    def test_str_replace_not_found(self, client, setup_manager):
        """Test string replace when string not found."""
        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Hello',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Try to replace non-existent string
        response2 = client.post('/msg_str_replace_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'old_str': 'notfound',
            'new_str': 'replacement'
        })
        data = response2.json()
        assert 'error' in data
