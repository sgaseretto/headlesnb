# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-XX-XX

### Added
- **DialogManager** for AI-assisted dialog conversations stored as Jupyter notebooks
  - Message-based conversation management with support for code, note, prompt, and raw message types
  - LLM integration with abstract `LLMClient` interface
  - `MockLLMClient` for testing without API calls
  - `ContextBuilder` for smart context window management with token budgets
  - Support for pinned messages (always included in LLM context)
  - Support for skipped messages (excluded from LLM context)
  - Bidirectional serialization between Dialog and Notebook formats
  - Separator pattern for prompt content/output in notebook cells

- **New Dialog Management Tools**
  - `use_dialog` - Create or connect to dialog notebooks
  - `unuse_dialog` - Disconnect from dialogs
  - `list_dialogs` - List active dialogs
  - `set_active_dialog` / `get_active_dialog` - Dialog switching

- **Message Management Tools**
  - `add_message` - Add messages with type and metadata
  - `read_message` - Read message content and output
  - `update_message` - Modify message content and attributes
  - `delete_message` - Remove messages from dialog
  - `list_messages` - List all messages with optional content/output
  - `move_message` - Move message to new position
  - `swap_messages` - Swap two messages

- **Execution Tools**
  - `execute_code` (DialogManager) - Execute code in dialog kernel
  - `execute_prompt` - Execute prompt with LLM, building context from prior messages

- **Undo/Redo for Dialogs**
  - Command pattern implementation for all message operations
  - Full undo/redo support with `undo()`, `redo()`, `get_history()`, `clear_history()`

- **LLM Client Infrastructure**
  - `LLMClient` abstract base class
  - `LLMResponse` dataclass with content, tool_calls, usage, model, stop_reason
  - `MockLLMClient` for testing with predefined responses
  - `MockLLMResponse` for configurable mock responses with tool calls
  - `create_mock_for_tool_use` helper function
  - `ContextBuilder` with token budget management

### Changed
- Renamed `manager.py` to `nb_manager.py` to avoid naming conflicts
- Added `BaseManager` abstract base class and `ManagedItemInfo` dataclass for shared functionality
- Updated imports throughout codebase to use new module names

### Documentation
- Added DialogManager section to README.md
- Added DialogManager examples to QUICKSTART.md
- Added DialogManager API reference to docs/API.md
- Added comprehensive DialogManager guide (docs/DIALOGMANAGER.md)
- Updated architecture documentation

### Testing
- Added 46 new tests for DialogManager functionality
- Tests cover: Message, Serialization, DialogManager, MessageOperations, UndoRedo, MockLLMClient, PromptExecution, ContextBuilder, CodeExecution, Integration
- Total test count: 180 tests

---

## [0.1.1] - 2024-XX-XX

### Added
- Cell reordering functionality
  - `move_cell` - Move a cell from one position to another
  - `swap_cells` - Swap two cells in the notebook
  - `reorder_cells` - Reorder all cells according to a new sequence
- Comprehensive undo/redo functionality with Command Pattern
  - Support for insert, delete, overwrite, move, swap, and reorder operations
  - `undo()` and `redo()` methods with optional step count
  - `get_history()` to view operation history
  - `clear_history()` to reset history

### Documentation
- Updated API documentation for cell reordering
- Added examples for undo/redo operations

---

## [0.1.0] - 2024-01-XX

### Added
- Initial release of HeadlesNB
- NotebookManager for programmatic notebook manipulation
- Support for managing multiple notebooks simultaneously
- Server management tools (list_files, list_kernels)
- Multi-notebook management tools (use_notebook, list_notebooks, restart_notebook, unuse_notebook, read_notebook)
- Cell operation tools (insert_cell, overwrite_cell_source, execute_cell, insert_execute_code_cell, read_cell, delete_cell, execute_code)
- Kernel control features (restart kernel, stop execution)
- MCP (Model Context Protocol) server implementation
- Comprehensive test suite with 100+ test cases
- Full documentation and examples
- Support for:
  - Code and markdown cells
  - Cell execution with timeout
  - Direct code execution without saving
  - File system operations with pagination
  - Multiple independent kernels
  - Magic commands and shell commands

### Documentation
- Complete API reference
- MCP server integration guide
- Usage examples for common scenarios
- Architecture overview

### Testing
- Unit tests for NotebookManager
- Unit tests for execnb components
- Unit tests for tool schemas
- Integration tests for full workflows
