# macOS Integrations

This directory contains macOS-specific integrations for Sisypho SDK, including MCP servers and utilities.

## Path Helpers

The `integrations.macos` module provides helper functions to get correct paths to server binaries and resources, whether running in development or when the package is installed.

### Usage Examples

```python
from integrations.macos import (
    get_servers_dir,
    get_accessibility_server_path,
    get_event_polling_cli_path
)

# Get the servers directory
servers_dir = get_servers_dir()
print(f"Servers directory: {servers_dir}")

# Get the AccessibilityMCPServer path
try:
    server_path = get_accessibility_server_path()
    print(f"Accessibility server: {server_path}")
except FileNotFoundError as e:
    print(f"Server not found: {e}")

# Get the event-polling-cli path
try:
    cli_path = get_event_polling_cli_path()
    print(f"Event polling CLI: {cli_path}")
except FileNotFoundError as e:
    print(f"CLI not found: {e}")
```

### Why Use Path Helpers?

These helpers ensure that your code works correctly both:

- **In development**: When files are in `integrations/macos/servers/`
- **When packaged**: When files are installed in Python's `site-packages/`

Without these helpers, hardcoded paths like `"integrations/macos/servers/.build/release/AccessibilityMCPServer"` will break when the package is installed because they assume you're running from the repository root.

### Available Functions

#### `get_servers_dir() -> Path`

Returns the absolute path to the `servers` directory.

#### `get_accessibility_server_path() -> Path`

Returns the path to the AccessibilityMCPServer executable.
Automatically searches for it in common build locations (arm64, x86_64, generic).

#### `get_event_polling_cli_path() -> Path`

Returns the path to the event-polling-cli executable.
Automatically searches for it in common build locations (arm64, x86_64, generic).

## Building the Servers

Before using the servers, you need to build them:

### AccessibilityMCPServer

```bash
cd integrations/macos/servers
swift build --configuration release
```

### Event Polling CLI

```bash
cd integrations/macos/servers/EventPollingApp
swift build --configuration release
```

## Architecture Support

The servers are built for both Apple Silicon (arm64) and Intel (x86_64) architectures.
The path helpers automatically detect which architecture's binary to use.
