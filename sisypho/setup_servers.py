#!/usr/bin/env python3
"""
Post-installation setup script for sisypho MCP servers.
This script ensures the MCP server binaries have executable permissions.
"""

import os
import stat
import sys
from pathlib import Path


def setup_server_permissions():
    """Ensure MCP server binaries have executable permissions."""
    try:
        from .integrations.macos import get_servers_dir
        
        servers_dir = get_servers_dir()
        print(f"Setting up MCP servers in: {servers_dir}")
        
        # Find all executables
        executables = [
            servers_dir / ".build/arm64-apple-macosx/release/AccessibilityMCPServer",
            servers_dir / ".build/x86_64-apple-macosx/release/AccessibilityMCPServer",
            servers_dir / ".build/release/AccessibilityMCPServer",
            servers_dir / "EventPollingApp/.build/arm64-apple-macosx/release/event-polling-cli",
            servers_dir / "EventPollingApp/.build/x86_64-apple-macosx/release/event-polling-cli",
            servers_dir / "EventPollingApp/.build/release/event-polling-cli",
        ]
        
        fixed = 0
        for exe_path in executables:
            if exe_path.exists():
                st = os.stat(exe_path)
                is_executable = bool(st.st_mode & stat.S_IXUSR)
                
                if not is_executable:
                    try:
                        os.chmod(exe_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                        print(f"  ✓ Fixed permissions for: {exe_path.name}")
                        fixed += 1
                    except Exception as e:
                        print(f"  ⚠ Could not fix permissions for {exe_path.name}: {e}", file=sys.stderr)
        
        if fixed > 0:
            print(f"\n✓ Fixed permissions for {fixed} server(s)")
        else:
            print("✓ All servers already have correct permissions")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up servers: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    print("Sisypho MCP Server Setup")
    print("=" * 60)
    
    if not setup_server_permissions():
        print("\nSetup failed. You may need to manually fix permissions:")
        print("  Run: python -m sisypho.setup_servers")
        return 1
    
    print("\n✅ Setup complete! You can now use sisypho.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

