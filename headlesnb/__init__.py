"""HeadlesNB - Headless Notebook Server with MCP Support"""

# Patch execnb.shell.CaptureShell with missing methods
from execnb.shell import CaptureShell
import threading

if not hasattr(CaptureShell, '_stop_execution'):
    CaptureShell._stop_execution = False
    CaptureShell._execution_lock = threading.Lock()

if not hasattr(CaptureShell, 'stop_execution'):
    def _stop_execution_method(self):
        """Request to stop the current execution"""
        self._stop_execution = True
    CaptureShell.stop_execution = _stop_execution_method

if not hasattr(CaptureShell, 'restart_kernel'):
    def _restart_kernel_method(self):
        """Restart the kernel by resetting the namespace"""
        self.reset(new_session=True)
        self.exc = None
        self.result = None
        self._stop_execution = False
    CaptureShell.restart_kernel = _restart_kernel_method

from .nb_manager import NotebookManager
from .base import BaseManager, ManagedItemInfo
from .tools import *

# DialogManager imports
from .dialogmanager import (
    DialogManager,
    DialogInfo,
    Message,
    generate_msg_id,
    dialog_to_notebook,
    notebook_to_dialog,
)

__version__ = "0.1.0"
__all__ = [
    'NotebookManager',
    'BaseManager',
    'ManagedItemInfo',
    'DialogManager',
    'DialogInfo',
    'Message',
    'generate_msg_id',
    'dialog_to_notebook',
    'notebook_to_dialog',
]
