"""Pytest configuration and shared fixtures"""

import pytest
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def reset_ipython_instance():
    """Reset IPython instance between tests"""
    from IPython.core.interactiveshell import InteractiveShell

    # Clear any existing instances
    InteractiveShell.clear_instance()

    yield

    # Clean up after test
    InteractiveShell.clear_instance()
