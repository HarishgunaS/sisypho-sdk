# Sisypho - Testing Package

## What Was Fixed

✅ **Chrome extension server made optional** - No longer fails if Chrome extension is not available  
✅ **Better error messages** - Shows actual initialization errors  
✅ **Auto-fix permissions** - Automatically fixes executable permissions for MCP servers  
✅ **Diagnostic tools included** - Easy troubleshooting scripts

## Files to Copy

Copy these files from the `dist/` folder to the other Mac:

```
sisypho-0.1.0-py3-none-any.whl    # Main package (3.4MB)
quick_test.py                      # Quick verification script
check_mcp_servers.py               # Detailed diagnostic tool (optional)
TESTING_INSTRUCTIONS.md            # Detailed instructions (optional)
INSTALL.md                         # Installation guide (optional)
```

## Quick Start (3 Steps)

### 1. Install

```bash
pip install sisypho-0.1.0-py3-none-any.whl
```

### 2. Test

```bash
python quick_test.py
```

Expected output:

```
Sisypho Quick Test
============================================================

1. Testing imports...
   ✓ All imports successful

2. Checking MCP server...
   ✓ Server found: AccessibilityMCPServer
   ✓ Executable: True

3. Testing RecorderContext...
   ✓ RecorderContext started
   ✓ RecorderContext stopped cleanly

============================================================
✅ All tests passed!
============================================================
```

### 3. Use

```python
from sisypho.utils import RecorderContext

with RecorderContext() as recorder:
    print("Recording...")
    # Your automation code here

recording = recorder.get_recording()
print(f"Captured {len(recording)} events")
```

## If You Get Errors

### "Starting failed" or Permission Errors

**Quick fix:**

```bash
python -m sisypho.setup_servers
```

### Want More Details?

**Run full diagnostic:**

```bash
python check_mcp_servers.py
```

This checks:

- OS compatibility
- CPU architecture
- Server paths
- Permissions
- Server execution

### Still Having Issues?

1. Check Python version: `python --version` (needs 3.8+)
2. Check macOS version: `sw_vers` (needs 11.0+)
3. Check architecture: `uname -m` (arm64 or x86_64)
4. Try manual permission fix:
   ```bash
   find "$(python -c 'from sisypho.integrations.macos import get_servers_dir; print(get_servers_dir())')" \
     \( -name "AccessibilityMCPServer" -o -name "event-polling-cli" \) \
     -exec chmod +x {} \;
   ```

## What Changed Since Last Version

### The Problem

- Chrome extension server path was wrong
- It was required, so when it failed, everything failed
- Error messages were hidden

### The Fix

- Chrome extension is now **optional** (only loads if present)
- AccessibilityMCPServer works independently
- Error messages are now **visible**
- Added **automatic permission fixing**

## Architecture Notes

- **Apple Silicon (M1/M2/M3)**: Uses arm64 binaries (included)
- **Intel Macs**: May need to build from source if x86_64 binaries not included

Check your architecture:

```bash
uname -m
# arm64 = Apple Silicon ✓
# x86_64 = Intel
```

## Package Info

- **Name**: sisypho
- **Version**: 0.1.0
- **Size**: 3.4MB
- **Platform**: macOS only (11.0+)
- **Python**: 3.8+

## Import Examples

```python
# Main utilities
from sisypho.utils import RecorderContext, Workflow

# Core libraries
from sisypho.corelib import browser, os_utils, excel

# Execution
from sisypho.execution import SkillExecutor

# macOS integration helpers
from sisypho.integrations.macos import (
    get_servers_dir,
    get_accessibility_server_path,
    get_event_polling_cli_path
)
```

## Success!

If `quick_test.py` passes, you're ready to use sisypho for:

- ✓ Browser automation
- ✓ macOS UI automation
- ✓ Workflow recording
- ✓ Skill execution
- ✓ MCP integration

Happy automating! 🚀
