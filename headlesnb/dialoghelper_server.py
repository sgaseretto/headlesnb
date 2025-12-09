"""FastHTML backend server for dialoghelper client.

This module provides an HTTP server that implements the endpoints expected by
the dialoghelper Python client library. It wraps the DialogManager to handle
dialog and message operations via HTTP POST requests.

Usage:
    >>> from headlesnb.dialoghelper_server import app, serve
    >>> serve()  # Starts server on port 5001

Endpoints:
    - /curr_dialog_ - Get current dialog info
    - /msg_idx_ - Get message index
    - /find_msgs_ - Find messages matching pattern
    - /add_html_ - Send HTML to browser for OOB swap (SSE)
    - /read_msg_ - Read a message
    - /add_relative_ - Add message relative to another
    - /update_msg_ - Update a message
    - /rm_msg_ - Delete a message
    - /add_runq_ - Add message to run queue
    - /pop_data_blocking_ - Pop data with timeout
    - /msg_insert_line_ - Insert line in message
    - /msg_str_replace_ - String replace in message
    - /msg_strs_replace_ - Multiple string replace
    - /msg_replace_lines_ - Replace lines in message
"""

import re
import json
import asyncio
import threading
from typing import Optional, Dict, Any, List
from collections import defaultdict
from pathlib import Path
from datetime import datetime

from fasthtml.common import (
    FastHTML, fast_app, serve as fh_serve, Script, Div, Safe,
    EventStream, sse_message
)
from starlette.responses import JSONResponse, PlainTextResponse

from .dialogmanager import DialogManager, Message


# Global state
manager: Optional[DialogManager] = None
html_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
data_store: Dict[str, asyncio.Event] = {}
data_values: Dict[str, Any] = {}
run_queue: Dict[str, List[str]] = defaultdict(list)

# Create app with HTMX SSE extension support
app, rt = fast_app(
    hdrs=[Script(src="https://unpkg.com/htmx-ext-sse@2.2.3/sse.js")],
    live=True
)


def init_manager(root_path: str = ".", llm_client=None) -> DialogManager:
    """Initialize the global DialogManager instance.

    Args:
        root_path: Root directory for dialog files.
        llm_client: LLM client for prompt execution.

    Returns:
        The initialized DialogManager instance.
    """
    global manager
    manager = DialogManager(root_path=root_path, default_llm_client=llm_client)
    return manager


def get_manager() -> DialogManager:
    """Get the global DialogManager instance, initializing if needed."""
    global manager
    if manager is None:
        manager = DialogManager()
    return manager


def _get_dialog_name(data: dict) -> Optional[str]:
    """Extract dialog name from request data, falling back to active dialog."""
    dname = data.get('dlg_name', '')
    if not dname:
        mgr = get_manager()
        dname = mgr.active_dialog
    return dname


def _ensure_dialog(dname: str) -> Optional[Dict]:
    """Ensure dialog exists and return error dict if not."""
    mgr = get_manager()
    if dname not in mgr.dialogs:
        return {"error": f"Dialog '{dname}' not found"}
    return None


# ================== Core Endpoints ==================

@rt
async def curr_dialog_(req):
    """Get current dialog info.

    POST /curr_dialog_
    Body: dlg_name, with_messages
    Returns: {name, mode} or {name, mode, messages}
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({})

    mgr = get_manager()
    if err := _ensure_dialog(dname):
        return JSONResponse(err)

    dialog = mgr.dialogs[dname]
    result = {
        'name': dialog.name,
        'mode': dialog.mode
    }

    with_messages = data.get('with_messages', 'false').lower() == 'true'
    if with_messages:
        result['messages'] = [m.to_dict() for m in dialog.messages]

    return JSONResponse(result)


@rt
async def msg_idx_(req):
    """Get absolute index of message in dialog.

    POST /msg_idx_
    Body: dlg_name, msgid
    Returns: {msgid: int}
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({"error": "No dialog specified"})

    mgr = get_manager()
    if err := _ensure_dialog(dname):
        return JSONResponse(err)

    dialog = mgr.dialogs[dname]
    msgid = data.get('msgid', '')

    idx = dialog.get_message_index(msgid)
    if idx is None:
        return JSONResponse({"error": f"Message '{msgid}' not found"})

    return JSONResponse({"msgid": idx})


@rt
async def find_msgs_(req):
    """Find messages matching criteria.

    POST /find_msgs_
    Body: dlg_name, re_pattern, msg_type, limit
    Returns: {msgs: [dict]}
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({"msgs": []})

    mgr = get_manager()
    if err := _ensure_dialog(dname):
        return JSONResponse(err)

    dialog = mgr.dialogs[dname]

    re_pattern = data.get('re_pattern', '')
    msg_type = data.get('msg_type', None)
    if msg_type == 'None' or msg_type == '':
        msg_type = None
    limit = data.get('limit', None)
    if limit and limit != 'None':
        limit = int(limit)
    else:
        limit = None

    # Filter messages
    msgs = dialog.messages
    if msg_type:
        msgs = [m for m in msgs if m.msg_type == msg_type]

    if re_pattern:
        pattern = re.compile(re_pattern, re.DOTALL | re.MULTILINE)
        msgs = [m for m in msgs if pattern.search(m.content)]

    if limit:
        msgs = msgs[:limit]

    return JSONResponse({"msgs": [m.to_dict() for m in msgs]})


@rt
async def add_html_(req):
    """Send HTML to browser for OOB swap.

    POST /add_html_
    Body: dlg_name, content
    Returns: "ok"
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data) or 'default'
    content = data.get('content', '')

    # Queue HTML for SSE delivery
    await html_queues[dname].put(content)

    return PlainTextResponse("ok")


@rt
async def html_stream_(req):
    """SSE endpoint for HTML updates.

    GET /html_stream_?dlg_name=...
    Returns: SSE stream of HTML content
    """
    dname = req.query_params.get('dlg_name', 'default')

    async def generate():
        queue = html_queues[dname]
        while True:
            try:
                content = await asyncio.wait_for(queue.get(), timeout=30)
                yield sse_message(Safe(content))
            except asyncio.TimeoutError:
                # Send heartbeat
                yield sse_message("<!-- heartbeat -->")

    return EventStream(generate())


@rt
async def read_msg_(req):
    """Read a message from the dialog.

    POST /read_msg_
    Body: dlg_name, n, relative, msgid, view_range, nums
    Returns: {msg: dict}
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({"error": "No dialog specified"})

    mgr = get_manager()
    if err := _ensure_dialog(dname):
        return JSONResponse(err)

    dialog = mgr.dialogs[dname]

    n = int(data.get('n', -1))
    relative = data.get('relative', 'true').lower() == 'true'
    msgid = data.get('msgid', '')
    view_range = data.get('view_range', None)
    nums = data.get('nums', 'false').lower() == 'true'

    # Find the message
    if relative and msgid:
        base_idx = dialog.get_message_index(msgid)
        if base_idx is None:
            return JSONResponse({"error": f"Message '{msgid}' not found"})
        target_idx = base_idx + n
    elif msgid and n == 0:
        target_idx = dialog.get_message_index(msgid)
    else:
        # Absolute index
        if n >= 0:
            target_idx = n
        else:
            target_idx = len(dialog.messages) + n

    if target_idx is None or target_idx < 0 or target_idx >= len(dialog.messages):
        return JSONResponse({"error": f"Message index {target_idx} out of range"})

    msg = dialog.messages[target_idx]
    result = msg.to_dict()

    # Apply view_range and nums to content
    content = result['content']
    lines = content.split('\n')

    if view_range:
        try:
            if isinstance(view_range, str):
                view_range = json.loads(view_range)
            start, end = view_range
            if end == -1:
                end = len(lines)
            lines = lines[start-1:end]  # 1-indexed
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    if nums:
        # Add line numbers like cat -n
        numbered_lines = []
        start_num = 1
        if view_range:
            try:
                if isinstance(view_range, str):
                    view_range = json.loads(view_range)
                start_num = view_range[0]
            except:
                pass
        for i, line in enumerate(lines, start=start_num):
            numbered_lines.append(f"{i:>6} │ {line}")
        lines = numbered_lines

    result['content'] = '\n'.join(lines)

    return JSONResponse({"msg": result})


@rt
async def add_relative_(req):
    """Add message relative to another.

    POST /add_relative_
    Body: dlg_name, content, placement, msgid, msg_type, output, run, ...
    Returns: message id (string)
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return PlainTextResponse("Error: No dialog specified")

    mgr = get_manager()
    if dname not in mgr.dialogs:
        return PlainTextResponse(f"Error: Dialog '{dname}' not found")

    # Save current active dialog and switch
    prev_active = mgr.active_dialog
    mgr.active_dialog = dname

    try:
        dialog = mgr.dialogs[dname]

        content = data.get('content', '')
        placement = data.get('placement', 'add_after')
        msgid = data.get('msgid', '')
        msg_type = data.get('msg_type', 'note')
        output = data.get('output', '')
        run = data.get('run', 'false').lower() == 'true'

        # Parse optional int fields
        kwargs = {}
        for field in ['is_exported', 'skipped', 'pinned', 'i_collapsed',
                      'o_collapsed', 'heading_collapsed']:
            if field in data:
                try:
                    kwargs[field] = int(data[field])
                except (ValueError, TypeError):
                    pass

        # Determine insertion index
        if placement == 'at_start':
            index = 0
        elif placement == 'at_end':
            index = -1  # Append
        elif placement in ('add_after', 'add_before'):
            if msgid:
                base_idx = dialog.get_message_index(msgid)
                if base_idx is None:
                    return PlainTextResponse(f"Error: Message '{msgid}' not found")
                if placement == 'add_after':
                    index = base_idx + 1
                else:
                    index = base_idx
            else:
                index = -1
        else:
            index = -1

        # Create and add message
        new_msg_id = mgr.add_message(
            content=content,
            msg_type=msg_type,
            index=index,
            output=output,
            **kwargs
        )

        if new_msg_id.startswith("Error"):
            return PlainTextResponse(new_msg_id)

        # Execute if run=True
        if run:
            if msg_type == 'code':
                mgr.execute_code(msg_id=new_msg_id)
            elif msg_type == 'prompt':
                mgr.execute_prompt(msg_id=new_msg_id)

        return PlainTextResponse(new_msg_id)

    finally:
        mgr.active_dialog = prev_active


@rt
async def update_msg_(req):
    """Update an existing message.

    POST /update_msg_
    Body: dlg_name, msgid, content, output, skipped, pinned, ...
    Returns: message id (string)
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return PlainTextResponse("Error: No dialog specified")

    mgr = get_manager()
    if dname not in mgr.dialogs:
        return PlainTextResponse(f"Error: Dialog '{dname}' not found")

    prev_active = mgr.active_dialog
    mgr.active_dialog = dname

    try:
        msgid = data.get('msgid', '')
        if not msgid:
            return PlainTextResponse("Error: No message ID provided")

        # Build kwargs for update
        kwargs = {}
        if 'content' in data and data['content']:
            kwargs['content'] = data['content']
        if 'output' in data and data['output']:
            kwargs['output'] = data['output']

        for field in ['is_exported', 'skipped', 'pinned', 'i_collapsed',
                      'o_collapsed', 'heading_collapsed', 'msg_type']:
            if field in data and data[field] not in ('', 'None', None):
                try:
                    if field == 'msg_type':
                        kwargs[field] = data[field]
                    else:
                        kwargs[field] = int(data[field])
                except (ValueError, TypeError):
                    pass

        if kwargs:
            result = mgr.update_message(msgid, **kwargs)
            if result.startswith("Error"):
                return PlainTextResponse(result)

        return PlainTextResponse(msgid)

    finally:
        mgr.active_dialog = prev_active


@rt
async def rm_msg_(req):
    """Delete a message from the dialog.

    POST /rm_msg_
    Body: dlg_name, msid (note: typo in original API)
    Returns: "ok"
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return PlainTextResponse("Error: No dialog specified", status_code=400)

    mgr = get_manager()
    if dname not in mgr.dialogs:
        return PlainTextResponse(f"Error: Dialog '{dname}' not found", status_code=404)

    prev_active = mgr.active_dialog
    mgr.active_dialog = dname

    try:
        # Note: original API uses 'msid' (typo for msgid)
        msgid = data.get('msid', '') or data.get('msgid', '')
        if not msgid:
            return PlainTextResponse("Error: No message ID provided", status_code=400)

        result = mgr.delete_message(msgid)
        if result.startswith("Error"):
            return PlainTextResponse(result, status_code=400)

        return PlainTextResponse("ok")

    finally:
        mgr.active_dialog = prev_active


@rt
async def add_runq_(req):
    """Add message to run queue.

    POST /add_runq_
    Body: dlg_name, msgid, api
    Returns: {"status": "queued"} or message output if api=false
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({"error": "No dialog specified"})

    mgr = get_manager()
    if dname not in mgr.dialogs:
        return JSONResponse({"error": f"Dialog '{dname}' not found"})

    msgid = data.get('msgid', '')
    api = data.get('api', 'false').lower() == 'true'

    if not msgid:
        return JSONResponse({"error": "No message ID provided"})

    # Add to run queue
    run_queue[dname].append(msgid)

    if api:
        return JSONResponse({"status": "queued"})

    # Execute immediately if not API mode
    prev_active = mgr.active_dialog
    mgr.active_dialog = dname

    try:
        dialog = mgr.dialogs[dname]
        msg = dialog.get_message_by_id(msgid)

        if not msg:
            return JSONResponse({"error": f"Message '{msgid}' not found"})

        if msg.msg_type == 'code':
            outputs = mgr.execute_code(msg_id=msgid)
            return JSONResponse({"outputs": outputs})
        elif msg.msg_type == 'prompt':
            response = mgr.execute_prompt(msg_id=msgid)
            return JSONResponse({"response": response.content})
        else:
            return JSONResponse({"error": f"Cannot run message of type '{msg.msg_type}'"})

    finally:
        mgr.active_dialog = prev_active


@rt
async def pop_data_blocking_(req):
    """Pop data with blocking and timeout.

    POST /pop_data_blocking_
    Body: data_id, timeout
    Returns: stored data
    """
    data = dict(await req.form())
    data_id = data.get('data_id', '')
    timeout = int(data.get('timeout', 15))

    if not data_id:
        return JSONResponse({"error": "No data_id provided"})

    # Create event if doesn't exist
    if data_id not in data_store:
        data_store[data_id] = asyncio.Event()

    event = data_store[data_id]

    try:
        # Wait for data with timeout
        await asyncio.wait_for(event.wait(), timeout=timeout)

        # Get and remove data
        result = data_values.pop(data_id, {"error": "Data expired"})
        del data_store[data_id]

        return JSONResponse(result)

    except asyncio.TimeoutError:
        # Clean up
        if data_id in data_store:
            del data_store[data_id]
        if data_id in data_values:
            del data_values[data_id]
        return JSONResponse({"error": "timeout"})


@rt
async def push_data_(req):
    """Push data that can be retrieved by pop_data_blocking_.

    POST /push_data_
    Body: data_id, data (JSON string)
    Returns: "ok"
    """
    form_data = dict(await req.form())
    data_id = form_data.get('data_id', '')
    data = form_data.get('data', '{}')

    if not data_id:
        return PlainTextResponse("Error: No data_id provided")

    try:
        data_values[data_id] = json.loads(data)
    except json.JSONDecodeError:
        data_values[data_id] = {"raw": data}

    # Create event if doesn't exist and signal it
    if data_id not in data_store:
        data_store[data_id] = asyncio.Event()
    data_store[data_id].set()

    return PlainTextResponse("ok")


# ================== Text Edit Endpoints ==================

@rt
async def msg_insert_line_(req):
    """Insert text at a specific line number in a message.

    POST /msg_insert_line_
    Body: dlg_name, msgid, insert_line, new_str
    Returns: {success: message}
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({"error": "No dialog specified"})

    mgr = get_manager()
    if dname not in mgr.dialogs:
        return JSONResponse({"error": f"Dialog '{dname}' not found"})

    prev_active = mgr.active_dialog
    mgr.active_dialog = dname

    try:
        dialog = mgr.dialogs[dname]
        msgid = data.get('msgid', '')
        insert_line = int(data.get('insert_line', 0))
        new_str = data.get('new_str', '')

        msg = dialog.get_message_by_id(msgid)
        if not msg:
            return JSONResponse({"error": f"Message '{msgid}' not found"})

        lines = msg.content.split('\n')

        # Insert at line position (0 = before first line)
        if insert_line <= 0:
            lines.insert(0, new_str)
        elif insert_line >= len(lines):
            lines.append(new_str)
        else:
            lines.insert(insert_line, new_str)

        # Update message content
        mgr.update_message(msgid, content='\n'.join(lines))

        return JSONResponse({"success": f"Inserted text after line {insert_line} in message {msgid}"})

    finally:
        mgr.active_dialog = prev_active


@rt
async def msg_str_replace_(req):
    """Replace first occurrence of old_str with new_str in a message.

    POST /msg_str_replace_
    Body: dlg_name, msgid, old_str, new_str
    Returns: {success: message}
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({"error": "No dialog specified"})

    mgr = get_manager()
    if dname not in mgr.dialogs:
        return JSONResponse({"error": f"Dialog '{dname}' not found"})

    prev_active = mgr.active_dialog
    mgr.active_dialog = dname

    try:
        dialog = mgr.dialogs[dname]
        msgid = data.get('msgid', '')
        old_str = data.get('old_str', '')
        new_str = data.get('new_str', '')

        msg = dialog.get_message_by_id(msgid)
        if not msg:
            return JSONResponse({"error": f"Message '{msgid}' not found"})

        if old_str not in msg.content:
            return JSONResponse({"error": f"String not found in message"})

        new_content = msg.content.replace(old_str, new_str, 1)
        mgr.update_message(msgid, content=new_content)

        return JSONResponse({"success": f"Replaced text in message {msgid}"})

    finally:
        mgr.active_dialog = prev_active


@rt
async def msg_strs_replace_(req):
    """Replace multiple strings simultaneously in a message.

    POST /msg_strs_replace_
    Body: dlg_name, msgid, old_strs (JSON array), new_strs (JSON array)
    Returns: {success: message}
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({"error": "No dialog specified"})

    mgr = get_manager()
    if dname not in mgr.dialogs:
        return JSONResponse({"error": f"Dialog '{dname}' not found"})

    prev_active = mgr.active_dialog
    mgr.active_dialog = dname

    try:
        dialog = mgr.dialogs[dname]
        msgid = data.get('msgid', '')

        # Parse arrays
        try:
            old_strs = json.loads(data.get('old_strs', '[]'))
            new_strs = json.loads(data.get('new_strs', '[]'))
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON arrays"})

        if len(old_strs) != len(new_strs):
            return JSONResponse({"error": "old_strs and new_strs must have same length"})

        msg = dialog.get_message_by_id(msgid)
        if not msg:
            return JSONResponse({"error": f"Message '{msgid}' not found"})

        content = msg.content
        for old_str, new_str in zip(old_strs, new_strs):
            content = content.replace(old_str, new_str, 1)

        mgr.update_message(msgid, content=content)

        return JSONResponse({"success": f"Successfully replaced all the strings in message {msgid}"})

    finally:
        mgr.active_dialog = prev_active


@rt
async def msg_replace_lines_(req):
    """Replace a range of lines with new content in a message.

    POST /msg_replace_lines_
    Body: dlg_name, msgid, start_line, end_line, new_content
    Returns: {success: message}
    """
    data = dict(await req.form())
    dname = _get_dialog_name(data)

    if not dname:
        return JSONResponse({"error": "No dialog specified"})

    mgr = get_manager()
    if dname not in mgr.dialogs:
        return JSONResponse({"error": f"Dialog '{dname}' not found"})

    prev_active = mgr.active_dialog
    mgr.active_dialog = dname

    try:
        dialog = mgr.dialogs[dname]
        msgid = data.get('msgid', '')
        start_line = int(data.get('start_line', 1))
        end_line = int(data.get('end_line', 1))
        new_content = data.get('new_content', '')

        msg = dialog.get_message_by_id(msgid)
        if not msg:
            return JSONResponse({"error": f"Message '{msgid}' not found"})

        lines = msg.content.split('\n')

        # 1-based indexing, inclusive
        new_lines = new_content.rstrip('\n').split('\n') if new_content else []

        # Replace lines
        result_lines = lines[:start_line-1] + new_lines + lines[end_line:]

        mgr.update_message(msgid, content='\n'.join(result_lines))

        return JSONResponse({"success": f"Replaced lines {start_line} to {end_line} in message {msgid}"})

    finally:
        mgr.active_dialog = prev_active


# ================== Dialog Management Endpoints ==================

@rt
async def use_dialog_(req):
    """Use/connect to a dialog.

    POST /use_dialog_
    Body: dlg_name, dialog_path, mode
    Returns: {status, message}
    """
    data = dict(await req.form())
    dialog_name = data.get('dlg_name', '')
    dialog_path = data.get('dialog_path', '')
    mode = data.get('mode', 'connect')

    if not dialog_name or not dialog_path:
        return JSONResponse({"error": "dialog_name and dialog_path required"})

    mgr = get_manager()
    result = mgr.use_dialog(dialog_name, dialog_path, mode=mode)

    if result.startswith("Error"):
        return JSONResponse({"error": result})

    return JSONResponse({"status": "ok", "message": result})


@rt
async def unuse_dialog_(req):
    """Release a dialog.

    POST /unuse_dialog_
    Body: dlg_name
    Returns: {status, message}
    """
    data = dict(await req.form())
    dialog_name = data.get('dlg_name', '')

    if not dialog_name:
        return JSONResponse({"error": "dialog_name required"})

    mgr = get_manager()
    result = mgr.unuse_dialog(dialog_name)

    if result.startswith("Error"):
        return JSONResponse({"error": result})

    return JSONResponse({"status": "ok", "message": result})


@rt
async def list_dialogs_(req):
    """List all active dialogs.

    GET/POST /list_dialogs_
    Returns: {dialogs: [{name, path, message_count, mode, is_active}]}
    """
    mgr = get_manager()

    dialogs = []
    for dialog in mgr.dialogs.values():
        dialogs.append({
            'name': dialog.name,
            'path': str(dialog.path) if dialog.path else None,
            'message_count': len(dialog.messages),
            'mode': dialog.mode,
            'is_active': dialog.is_active
        })

    return JSONResponse({"dialogs": dialogs})


# ================== Index/Health Endpoints ==================

@rt
def index():
    """Health check and info page."""
    return Div(
        Div(
            f"DialogHelper Server v1.0",
            Div(f"Active dialogs: {len(get_manager().dialogs)}"),
            Div(f"Current: {get_manager().active_dialog or 'None'}"),
        ),
        id="status"
    )


@rt
def health():
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


def serve(port: int = 5001, host: str = "0.0.0.0", reload: bool = False):
    """Start the dialoghelper server.

    Args:
        port: Port to listen on (default 5001).
        host: Host to bind to (default 0.0.0.0).
        reload: Enable auto-reload for development.
    """
    import uvicorn
    uvicorn.run(app, host=host, port=port, reload=reload)


if __name__ == "__main__":
    serve()
