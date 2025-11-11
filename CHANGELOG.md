# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
