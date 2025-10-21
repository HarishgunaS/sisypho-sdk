#!/usr/bin/env python3
"""
Diagnostic script to check MCP server installation and permissions.
Run this on the target computer after installing sisypho to diagnose issues.
"""

import os
import stat
import platform
import subprocess
from pathlib import Path

def check_macos():
    """Check if running on macOS."""
    if platform.system() != "Darwin":
        print("❌ ERROR: This package only works on macOS")
        print(f"   Current OS: {platform.system()}")
        return False
    print(f"✓ Running on macOS ({platform.mac_ver()[0]})")
    return True

def check_architecture():
    """Check CPU architecture."""
    arch = platform.machine()
    print(f"✓ Architecture: {arch}")
    if arch not in ["arm64", "x86_64"]:
        print(f"  ⚠ Unusual architecture: {arch}")
    return arch

def check_path_helpers():
    """Check if path helpers work."""
    print("\n" + "="*60)
    print("Testing Path Helpers")
    print("="*60)
    
    try:
        from sisypho.integrations.macos import (
            get_servers_dir,
            get_accessibility_server_path,
            get_event_polling_cli_path
        )
        print("✓ Path helper imports successful")
        
        # Check servers directory
        try:
            servers_dir = get_servers_dir()
            print(f"✓ Servers directory: {servers_dir}")
            print(f"  Exists: {servers_dir.exists()}")
        except Exception as e:
            print(f"❌ Failed to get servers directory: {e}")
            return False
        
        # Check AccessibilityMCPServer
        try:
            server_path = get_accessibility_server_path()
            print(f"\n✓ AccessibilityMCPServer path: {server_path}")
            print(f"  Exists: {server_path.exists()}")
            
            if server_path.exists():
                check_executable(server_path)
            else:
                print(f"  ❌ File does not exist!")
                list_build_dirs(servers_dir)
                return False
                
        except FileNotFoundError as e:
            print(f"❌ AccessibilityMCPServer not found: {e}")
            list_build_dirs(servers_dir)
            return False
        
        # Check event-polling-cli
        try:
            cli_path = get_event_polling_cli_path()
            print(f"\n✓ event-polling-cli path: {cli_path}")
            print(f"  Exists: {cli_path.exists()}")
            
            if cli_path.exists():
                check_executable(cli_path)
            else:
                print(f"  ❌ File does not exist!")
                return False
                
        except FileNotFoundError as e:
            print(f"❌ event-polling-cli not found: {e}")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import path helpers: {e}")
        return False

def check_executable(file_path: Path):
    """Check if a file is executable and try to fix permissions."""
    st = os.stat(file_path)
    is_executable = bool(st.st_mode & stat.S_IXUSR)
    
    print(f"  Executable: {is_executable}")
    print(f"  Permissions: {oct(st.st_mode)[-3:]}")
    
    if not is_executable:
        print(f"  ⚠ File is not executable! Attempting to fix...")
        try:
            os.chmod(file_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"  ✓ Fixed permissions: now {oct(os.stat(file_path).st_mode)[-3:]}")
        except Exception as e:
            print(f"  ❌ Failed to fix permissions: {e}")
            print(f"  Manual fix: chmod +x {file_path}")
            return False
    
    # Try to get file info
    try:
        result = subprocess.run(
            ['file', str(file_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  File type: {result.stdout.strip().split(':', 1)[1].strip()}")
    except Exception as e:
        print(f"  Could not determine file type: {e}")
    
    return is_executable

def list_build_dirs(servers_dir: Path):
    """List available build directories to help diagnose issues."""
    print(f"\n  Available build directories:")
    build_dir = servers_dir / ".build"
    if build_dir.exists():
        for item in build_dir.iterdir():
            if item.is_dir():
                print(f"    - {item.name}")
                release_dir = item / "release"
                if release_dir.exists():
                    for file in release_dir.iterdir():
                        if not file.name.startswith('.'):
                            print(f"      - {file.name}")

def test_server_execution():
    """Try to execute the AccessibilityMCPServer."""
    print("\n" + "="*60)
    print("Testing Server Execution")
    print("="*60)
    
    try:
        from sisypho.integrations.macos import get_accessibility_server_path
        server_path = get_accessibility_server_path()
        
        print(f"Attempting to run: {server_path}")
        
        # Try to run with --version or --help to see if it responds
        try:
            result = subprocess.run(
                [str(server_path), '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"Exit code: {result.returncode}")
            if result.stdout:
                print(f"stdout: {result.stdout[:200]}")
            if result.stderr:
                print(f"stderr: {result.stderr[:200]}")
                
        except subprocess.TimeoutExpired:
            print("⚠ Server didn't respond within 5 seconds (might be waiting for input)")
        except Exception as e:
            print(f"❌ Failed to execute server: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test server execution: {e}")
        return False
    
    return True

def main():
    print("="*60)
    print("Sisypho MCP Server Diagnostic Tool")
    print("="*60)
    
    # Check OS
    if not check_macos():
        return 1
    
    # Check architecture
    arch = check_architecture()
    
    # Check path helpers
    if not check_path_helpers():
        print("\n❌ Path helper checks failed!")
        return 1
    
    # Test server execution
    test_server_execution()
    
    print("\n" + "="*60)
    print("Diagnostic Complete")
    print("="*60)
    print("\n✅ If all checks passed, the servers should work.")
    print("If there were permission errors, try running again or manually:")
    print("  chmod +x /path/to/AccessibilityMCPServer")
    print("  chmod +x /path/to/event-polling-cli")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())

