"""Integration tests for dialoghelper client + fasthtml server.

These tests verify that the dialoghelper Python client library
works correctly with our FastHTML backend server.
"""

import pytest
import asyncio
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from starlette.testclient import TestClient

# Import the server
from headlesnb.dialoghelper_server import app, init_manager, get_manager

# Import dialoghelper client
from dialoghelper.core import dh_settings


@pytest.fixture
def temp_dir():
    """Create temporary directory for dialog files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def setup_server(temp_dir):
    """Setup server for testing with dialoghelper client."""
    # Initialize manager
    mgr = init_manager(root_path=temp_dir)
    mgr.use_dialog('test_dialog', 'test.ipynb', mode='create')

    # Create test client
    client = TestClient(app)

    yield client, mgr, temp_dir

    # Cleanup
    if 'test_dialog' in mgr.dialogs:
        mgr.unuse_dialog('test_dialog')


class TestDialoghelperClientCompatibility:
    """Test that dialoghelper client functions work with our server."""

    def test_curr_dialog_format(self, setup_server):
        """Test that curr_dialog_ returns expected format."""
        client, mgr, _ = setup_server

        response = client.post('/curr_dialog_', data={
            'dlg_name': 'test_dialog',
            'with_messages': 'false'
        })

        # dialoghelper expects: {'name': str, 'mode': str}
        data = response.json()
        assert 'name' in data
        assert 'mode' in data
        assert isinstance(data['name'], str)
        assert isinstance(data['mode'], str)

    def test_msg_idx_format(self, setup_server):
        """Test that msg_idx_ returns expected format."""
        client, mgr, _ = setup_server

        # Add a message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'test',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        response2 = client.post('/msg_idx_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id
        })

        # dialoghelper expects: {'msgid': int}
        data = response2.json()
        assert 'msgid' in data
        assert isinstance(data['msgid'], int)

    def test_find_msgs_format(self, setup_server):
        """Test that find_msgs_ returns expected format."""
        client, mgr, _ = setup_server

        # Add messages
        client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'test message',
            'placement': 'at_end',
            'msg_type': 'note'
        })

        response = client.post('/find_msgs_', data={
            'dlg_name': 'test_dialog',
            're_pattern': 'test'
        })

        # dialoghelper expects: {'msgs': list[dict]}
        data = response.json()
        assert 'msgs' in data
        assert isinstance(data['msgs'], list)
        if data['msgs']:
            msg = data['msgs'][0]
            assert 'id' in msg
            assert 'content' in msg
            assert 'msg_type' in msg

    def test_read_msg_format(self, setup_server):
        """Test that read_msg_ returns expected format."""
        client, mgr, _ = setup_server

        # Add message
        client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'line1\nline2\nline3',
            'placement': 'at_end',
            'msg_type': 'note'
        })

        response = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'n': '-1',
            'relative': 'false'
        })

        # dialoghelper expects: {'msg': dict}
        data = response.json()
        assert 'msg' in data
        assert isinstance(data['msg'], dict)
        assert 'content' in data['msg']
        assert 'id' in data['msg']

    def test_read_msg_with_nums_format(self, setup_server):
        """Test line numbering format matches dialoghelper expectations."""
        client, mgr, _ = setup_server

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
        content = data['msg']['content']

        # Should have line numbers like "     1 │ line1"
        assert '1' in content
        assert '│' in content

    def test_add_relative_returns_id(self, setup_server):
        """Test that add_relative_ returns message ID."""
        client, mgr, _ = setup_server

        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'test content',
            'placement': 'at_end',
            'msg_type': 'note'
        })

        # dialoghelper expects plain text message ID
        msg_id = response.text
        assert msg_id.startswith('_')
        assert len(msg_id) == 9  # '_' + 8 hex chars

    def test_update_msg_returns_id(self, setup_server):
        """Test that update_msg_ returns message ID."""
        client, mgr, _ = setup_server

        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'original',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Update
        response2 = client.post('/update_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'content': 'updated'
        })

        # dialoghelper expects plain text message ID
        returned_id = response2.text
        assert returned_id == msg_id

    def test_text_edit_success_format(self, setup_server):
        """Test text edit endpoints return success format."""
        client, mgr, _ = setup_server

        # Add message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Hello world',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Test msg_str_replace_
        response2 = client.post('/msg_str_replace_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'old_str': 'world',
            'new_str': 'universe'
        })

        # dialoghelper expects: {'success': str}
        data = response2.json()
        assert 'success' in data
        assert isinstance(data['success'], str)

    def test_msg_strs_replace_format(self, setup_server):
        """Test msg_strs_replace_ returns expected format."""
        client, mgr, _ = setup_server

        # Add message with multiple strings to replace
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Hello world, foo bar',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response1.text

        # Test msg_strs_replace_ with JSON arrays
        import json
        response2 = client.post('/msg_strs_replace_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'old_strs': json.dumps(['world', 'foo']),
            'new_strs': json.dumps(['universe', 'baz'])
        })

        # dialoghelper expects: {'success': str}
        data = response2.json()
        assert 'success' in data
        assert isinstance(data['success'], str)

        # Verify content was updated
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        content = response3.json()['msg']['content']
        assert 'universe' in content
        assert 'baz' in content
        assert 'world' not in content
        assert 'foo' not in content

    def test_add_runq_api_format(self, setup_server):
        """Test add_runq_ returns expected format."""
        client, mgr, _ = setup_server

        # Add code message
        response1 = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': '1+1',
            'placement': 'at_end',
            'msg_type': 'code'
        })
        msg_id = response1.text

        response2 = client.post('/add_runq_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'api': 'true'
        })

        # dialoghelper expects: {"status": "queued"}
        data = response2.json()
        assert data == {"status": "queued"}


class TestMessageTypeHandling:
    """Test all message types are handled correctly."""

    def test_code_message(self, setup_server):
        """Test code message handling."""
        client, _, _ = setup_server

        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'print("hello")',
            'placement': 'at_end',
            'msg_type': 'code'
        })
        msg_id = response.text

        # Verify type
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response2.json()
        assert data['msg']['msg_type'] == 'code'

    def test_note_message(self, setup_server):
        """Test note message handling."""
        client, _, _ = setup_server

        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': '# A markdown note',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response.text

        # Verify type
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response2.json()
        assert data['msg']['msg_type'] == 'note'

    def test_prompt_message(self, setup_server):
        """Test prompt message handling."""
        client, _, _ = setup_server

        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'What is the meaning of life?',
            'placement': 'at_end',
            'msg_type': 'prompt'
        })
        msg_id = response.text

        # Verify type
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response2.json()
        assert data['msg']['msg_type'] == 'prompt'


class TestMessageMetadata:
    """Test message metadata fields."""

    def test_skipped_field(self, setup_server):
        """Test skipped field handling."""
        client, _, _ = setup_server

        # Add with skipped=1
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'skipped message',
            'placement': 'at_end',
            'msg_type': 'note',
            'skipped': '1'
        })
        msg_id = response.text

        # Verify
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response2.json()
        assert data['msg']['skipped'] == 1

    def test_pinned_field(self, setup_server):
        """Test pinned field handling."""
        client, _, _ = setup_server

        # Add with pinned=1
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'pinned message',
            'placement': 'at_end',
            'msg_type': 'note',
            'pinned': '1'
        })
        msg_id = response.text

        # Verify
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response2.json()
        assert data['msg']['pinned'] == 1

    def test_collapsed_fields(self, setup_server):
        """Test collapsed field handling."""
        client, _, _ = setup_server

        # Add with collapsed fields
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'collapsed message',
            'placement': 'at_end',
            'msg_type': 'note',
            'i_collapsed': '1',
            'o_collapsed': '1'
        })
        msg_id = response.text

        # Verify
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response2.json()
        assert data['msg']['i_collapsed'] == 1
        assert data['msg']['o_collapsed'] == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_content(self, setup_server):
        """Test adding message with empty content."""
        client, _, _ = setup_server

        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': '',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response.text
        assert msg_id.startswith('_')

    def test_multiline_content(self, setup_server):
        """Test handling multiline content."""
        client, _, _ = setup_server

        content = "def foo():\n    print('hello')\n    return 42"
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': content,
            'placement': 'at_end',
            'msg_type': 'code'
        })
        msg_id = response.text

        # Verify content preserved
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response2.json()
        assert data['msg']['content'] == content

    def test_unicode_content(self, setup_server):
        """Test handling unicode content."""
        client, _, _ = setup_server

        content = "Hello 世界 🌍 émojis"
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': content,
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response.text

        # Verify content preserved
        response2 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response2.json()
        assert data['msg']['content'] == content

    def test_special_characters_in_replace(self, setup_server):
        """Test string replace with special characters."""
        client, _, _ = setup_server

        # Add message with special chars
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Hello $world$ [test]',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response.text

        # Replace with special chars
        response2 = client.post('/msg_str_replace_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'old_str': '$world$',
            'new_str': '@universe@'
        })

        # Verify
        response3 = client.post('/read_msg_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'n': '0',
            'relative': 'true'
        })
        data = response3.json()
        assert '@universe@' in data['msg']['content']

    def test_msg_strs_replace_mismatched_arrays(self, setup_server):
        """Test msg_strs_replace_ with mismatched array lengths returns error."""
        client, _, _ = setup_server
        import json

        # Add message
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Hello world foo',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response.text

        # Try replacing with mismatched arrays
        response2 = client.post('/msg_strs_replace_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'old_strs': json.dumps(['world', 'foo']),
            'new_strs': json.dumps(['universe'])  # Only one replacement
        })

        # Should return error
        data = response2.json()
        assert 'error' in data

    def test_msg_strs_replace_empty_arrays(self, setup_server):
        """Test msg_strs_replace_ with empty arrays succeeds."""
        client, _, _ = setup_server
        import json

        # Add message
        response = client.post('/add_relative_', data={
            'dlg_name': 'test_dialog',
            'content': 'Hello world',
            'placement': 'at_end',
            'msg_type': 'note'
        })
        msg_id = response.text

        # Replace with empty arrays (no-op)
        response2 = client.post('/msg_strs_replace_', data={
            'dlg_name': 'test_dialog',
            'msgid': msg_id,
            'old_strs': json.dumps([]),
            'new_strs': json.dumps([])
        })

        # Should succeed
        data = response2.json()
        assert 'success' in data
