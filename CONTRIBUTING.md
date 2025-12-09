# Contributing to HeadlesNB

Thank you for considering contributing to HeadlesNB! This document provides guidelines and instructions for contributing.

## Before You Start

### Understanding the Codebase

Before making changes, please read:

1. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Start here! Explains what each component does, how it works, and **why** it was designed that way.
2. **[docs/API.md](docs/API.md)** - API reference and design principles
3. **Tests** in `tests/` - Show expected behavior

### Design Philosophy

HeadlesNB follows these principles:

- **No Jupyter Server**: We use IPython directly for lighter weight
- **Command Pattern**: All modifications are reversible commands
- **Separate Concerns**: NotebookManager and DialogManager have different semantics
- **Compatibility**: .ipynb format for Jupyter interoperability

If your change conflicts with these principles, please discuss in an issue first.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/headlesnb/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and environment details
   - Code samples if applicable

### Suggesting Enhancements

1. Check if the enhancement has already been suggested
2. Create a new issue with:
   - Clear title and description
   - Use case and motivation
   - Proposed solution (if any)
   - Alternative solutions considered

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add or update tests as needed
5. Ensure all tests pass (`pytest tests/`)
6. Update documentation if needed
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/headlesnb.git
cd headlesnb

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=headlesnb --cov-report=html

# Run specific test file
pytest tests/test_manager.py -v

# Run specific test
pytest tests/test_manager.py::TestNotebookManager::test_use_notebook_connect -v
```

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Follow existing test structure
- Use fixtures for common setup

## Code Style

### Python Style

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for public functions and classes
- Keep functions focused and concise

### Example

```python
def insert_cell(
    self,
    cell_index: int,
    cell_type: str,
    cell_source: str
) -> str:
    """
    Insert a cell at specified position.

    Args:
        cell_index: Target index for insertion (0-based)
        cell_type: Type of cell ("code" or "markdown")
        cell_source: Source content for the cell

    Returns:
        Success message with surrounding cell structure
    """
    # Implementation
```

## Documentation

### Updating Documentation

When making changes, update relevant documentation:

| Document | When to Update |
|----------|----------------|
| `docs/ARCHITECTURE.md` | Architecture changes, new design decisions |
| `docs/API.md` | API changes, new methods |
| `docs/DIALOGMANAGER.md` | DialogManager features |
| `docs/DIALOGHELPER_SERVER.md` | HTTP server changes |
| `docs/MCP_SERVER.md` | MCP tool changes |
| `README.md` | Major features, getting started |
| `CHANGELOG.md` | Every release |

### Writing Documentation

- Be clear and concise
- Include code examples
- **Explain the "why" not just the "what"** - This is critical for maintainability
- Link to related sections
- Include design trade-offs when relevant

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Reference issues when applicable (#123)

Examples:
```
Add support for raw cell type
Fix timeout handling in execute_cell
Update documentation for MCP server
```

## Project Structure

```
headlesnb/
├── execnb/              # Core execution library
├── headlesnb/           # Main package
├── tests/               # Test suite
├── examples/            # Usage examples
├── docs/                # Documentation
└── pyproject.toml       # Project configuration
```

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag
4. Push tag to GitHub
5. Create release on GitHub

## Questions?

Feel free to open an issue for questions or discussions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
