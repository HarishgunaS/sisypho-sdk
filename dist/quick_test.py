#!/usr/bin/env python3
"""
Quick test script for sisypho package.
Run this after installing to verify everything works.
"""

print("Sisypho Quick Test")
print("="*60)

# Test 1: Check imports
print("\n1. Testing imports...")
try:
    import sisypho
    from sisypho.utils import RecorderContext
    from sisypho.integrations.macos import get_accessibility_server_path
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    exit(1)

# Test 2: Check server path
print("\n2. Checking MCP server...")
try:
    import os
    server_path = get_accessibility_server_path()
    print(f"   ✓ Server found: {server_path.name}")
    print(f"   ✓ Executable: {os.access(server_path, os.X_OK)}")
except Exception as e:
    print(f"   ✗ Server check failed: {e}")
    print("   Try running: python -m sisypho.setup_servers")
    exit(1)

# Test 3: Test RecorderContext
print("\n3. Testing RecorderContext...")
try:
    with RecorderContext() as recorder:
        print("   ✓ RecorderContext started")
    print("   ✓ RecorderContext stopped cleanly")
except Exception as e:
    print(f"   ✗ RecorderContext failed: {e}")
    print("\nFor detailed diagnostics, run:")
    print("  python check_mcp_servers.py")
    exit(1)

# Success!
print("\n" + "="*60)
print("✅ All tests passed!")
print("="*60)
print(f"\nSisypho {sisypho.__version__} is ready to use.")
print("\nExample usage:")
print("  from sisypho.utils import RecorderContext")
print("  ")
print("  with RecorderContext() as recorder:")
print("      # Your automation code here")
print("      pass")
print("  ")
print("  recording = recorder.get_recording()")
print("  print(f'Captured {len(recording)} events')")

