#!/usr/bin/env python
"""Example: Running the dialoghelper FastHTML server.

This script demonstrates how to start the dialoghelper server
and use it with the dialoghelper client library.

Usage:
    1. Run this script to start the server
    2. In another terminal/notebook, use dialoghelper client functions

Example:
    # Terminal 1: Start server
    $ python examples/dialoghelper_server_example.py

    # Terminal 2 or Jupyter notebook: Use client
    >>> from dialoghelper.core import *
    >>> __dialog_name = 'my_dialog'
    >>> __msg_id = '_startup00'
    >>> curr_dialog()
    {'name': 'my_dialog', 'mode': 'default'}
"""

import argparse
from pathlib import Path

from headlesnb.dialoghelper_server import (
    app,
    init_manager,
    serve
)


def setup_demo_dialog(root_path: str = ".", dialog_name: str = "demo"):
    """Create a demo dialog with some initial messages."""
    manager = init_manager(root_path=root_path)

    # Create or connect to dialog
    result = manager.use_dialog(
        dialog_name=dialog_name,
        dialog_path=f"{dialog_name}.ipynb",
        mode="create"
    )
    print(f"Dialog setup: {result}")

    # Add some demo messages
    manager.add_message(
        content="# Welcome to Dialog Helper\n\nThis is a demo dialog.",
        msg_type="note"
    )

    manager.add_message(
        content="import pandas as pd\nimport numpy as np",
        msg_type="code"
    )

    manager.add_message(
        content="What are the main features of pandas?",
        msg_type="prompt"
    )

    print(f"Added 3 demo messages to '{dialog_name}'")

    return manager


def main():
    parser = argparse.ArgumentParser(
        description="Start the dialoghelper FastHTML server"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=5001,
        help="Port to run server on (default: 5001)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--root-path",
        default=".",
        help="Root path for dialog files"
    )
    parser.add_argument(
        "--dialog-name",
        default="demo",
        help="Name of demo dialog to create"
    )
    parser.add_argument(
        "--no-demo",
        action="store_true",
        help="Don't create demo dialog"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    # Ensure root path exists
    root = Path(args.root_path)
    root.mkdir(parents=True, exist_ok=True)

    # Setup demo dialog unless disabled
    if not args.no_demo:
        setup_demo_dialog(
            root_path=str(root),
            dialog_name=args.dialog_name
        )
    else:
        init_manager(root_path=str(root))

    print(f"\n🚀 Starting dialoghelper server on http://{args.host}:{args.port}")
    print("   Press Ctrl+C to stop\n")

    # Start server
    serve(port=args.port, host=args.host, reload=args.reload)


if __name__ == "__main__":
    main()
