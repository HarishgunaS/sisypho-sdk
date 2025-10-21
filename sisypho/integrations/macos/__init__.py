"""macOS-specific integrations for Sisypho SDK."""

import os
import stat
from pathlib import Path


def _ensure_executable(path: Path) -> None:
    """
    Ensure a file has executable permissions.
    
    This fixes a common issue where wheel files don't preserve execute permissions.
    """
    if path.exists():
        st = os.stat(path)
        if not (st.st_mode & stat.S_IXUSR):
            try:
                os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                # Permission fix failed, but don't crash - let the user know later
                pass


def get_servers_dir() -> Path:
    """
    Get the absolute path to the integrations/macos/servers directory.
    
    This works both in development and when the package is installed.
    
    Returns:
        Path: Absolute path to the servers directory
        
    Example:
        >>> from sisypho.integrations.macos import get_servers_dir
        >>> servers_dir = get_servers_dir()
        >>> accessibility_server = servers_dir / ".build/arm64-apple-macosx/release/AccessibilityMCPServer"
    """
    # Get the directory where this __init__.py file is located
    macos_dir = Path(__file__).parent.resolve()
    servers_dir = macos_dir / "servers"
    
    if not servers_dir.exists():
        raise FileNotFoundError(
            f"Servers directory not found at {servers_dir}. "
            "Make sure the package was installed correctly."
        )
    
    return servers_dir


def get_accessibility_server_path() -> Path:
    """
    Get the path to the AccessibilityMCPServer executable.
    
    Tries common build locations in order:
    1. arm64 release build (Apple Silicon)
    2. x86_64 release build (Intel)
    3. Generic release build
    
    Returns:
        Path: Absolute path to the AccessibilityMCPServer executable
        
    Raises:
        FileNotFoundError: If the server executable is not found
        
    Example:
        >>> from integrations.macos import get_accessibility_server_path
        >>> server_path = get_accessibility_server_path()
        >>> print(server_path)
    """
    servers_dir = get_servers_dir()
    
    # Try different build locations
    possible_paths = [
        servers_dir / ".build/arm64-apple-macosx/release/AccessibilityMCPServer",
        servers_dir / ".build/x86_64-apple-macosx/release/AccessibilityMCPServer",
        servers_dir / ".build/release/AccessibilityMCPServer",
    ]
    
    for path in possible_paths:
        if path.exists():
            _ensure_executable(path)
            return path
    
    raise FileNotFoundError(
        f"AccessibilityMCPServer not found in any of the expected locations:\n" +
        "\n".join(f"  - {p}" for p in possible_paths) +
        f"\n\nServers directory: {servers_dir}\n" +
        "You may need to build the server first. See the README for instructions."
    )


def get_event_polling_cli_path() -> Path:
    """
    Get the path to the event-polling-cli executable.
    
    Tries common build locations in order:
    1. arm64 release build (Apple Silicon)
    2. x86_64 release build (Intel)
    3. Generic release build
    
    Returns:
        Path: Absolute path to the event-polling-cli executable
        
    Raises:
        FileNotFoundError: If the executable is not found
        
    Example:
        >>> from integrations.macos import get_event_polling_cli_path
        >>> cli_path = get_event_polling_cli_path()
        >>> print(cli_path)
    """
    servers_dir = get_servers_dir()
    
    # Try different build locations
    possible_paths = [
        servers_dir / "EventPollingApp/.build/arm64-apple-macosx/release/event-polling-cli",
        servers_dir / "EventPollingApp/.build/x86_64-apple-macosx/release/event-polling-cli",
        servers_dir / "EventPollingApp/.build/release/event-polling-cli",
    ]
    
    for path in possible_paths:
        if path.exists():
            _ensure_executable(path)
            return path
    
    raise FileNotFoundError(
        f"event-polling-cli not found in any of the expected locations:\n" +
        "\n".join(f"  - {p}" for p in possible_paths) +
        f"\n\nServers directory: {servers_dir}\n" +
        "You may need to build the CLI first. See the README for instructions."
    )


# Expose the main functions
__all__ = [
    "get_servers_dir",
    "get_accessibility_server_path",
    "get_event_polling_cli_path",
]
