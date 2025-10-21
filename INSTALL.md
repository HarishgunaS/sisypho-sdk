# Sisypho Installation Guide

## Requirements

- **macOS only** (macOS 11.0 or later)
- Python 3.8 or later
- For Apple Silicon Macs: arm64 binaries
- For Intel Macs: x86_64 binaries (may need to build from source)

## Installation

### Step 1: Install the Package

```bash
pip install sisypho-0.1.0-py3-none-any.whl
```

Or if uploading to PyPI:

```bash
pip install sisypho
```

### Step 2: Verify Installation

Run the diagnostic script to check everything is set up correctly:

```bash
python -m sisypho.setup_servers
```

Or run the full diagnostic:

```python
python << 'EOF'
from sisypho.integrations.macos import get_servers_dir, get_accessibility_server_path
import os

# Check if servers are found
try:
    servers_dir = get_servers_dir()
    print(f"✓ Servers directory: {servers_dir}")

    server_path = get_accessibility_server_path()
    print(f"✓ AccessibilityMCPServer: {server_path}")
    print(f"✓ Executable: {os.access(server_path, os.X_OK)}")

    print("\n✅ Installation successful!")

except Exception as e:
    print(f"❌ Installation check failed: {e}")
    print("\nTry running: python -m sisypho.setup_servers")
EOF
```

### Step 3: Test with a Simple Script

```python
from sisypho.utils import RecorderContext

with RecorderContext() as recorder:
    print("Recording started...")
    # Your automation code here

recording = recorder.get_recording()
print(f"Recording complete: {len(recording)} events")
```

## Troubleshooting

### "Starting failed" or "MCP server not found"

This usually means the server binaries don't have executable permissions. Fix it:

```bash
# Automatic fix
python -m sisypho.setup_servers

# Manual fix (if automatic fails)
find $(python -c "from sisypho.integrations.macos import get_servers_dir; print(get_servers_dir())") -name "AccessibilityMCPServer" -o -name "event-polling-cli" | xargs chmod +x
```

### Architecture Mismatch

If you're on an Intel Mac and the package includes only arm64 binaries, you'll need to build from source:

```bash
# Get the source
pip download sisypho --no-binary :all:
tar -xzf sisypho-0.1.0.tar.gz
cd sisypho-0.1.0

# Build the servers
cd sisypho/integrations/macos/servers
swift build --configuration release

# Install the package
cd ../../../..
pip install -e .
```

### Diagnostic Script

For detailed diagnostics, use the included script:

```bash
# Save this from the repo or create it
python check_mcp_servers.py
```

This will check:

- ✓ OS compatibility
- ✓ Architecture
- ✓ Server paths
- ✓ Executable permissions
- ✓ Server execution

### Common Issues

1. **Permission Denied**: Run `python -m sisypho.setup_servers` or manually `chmod +x` the binaries

2. **File Not Found**: The server binary for your architecture may not be included. Build from source.

3. **Wrong Architecture**: On Intel Macs, you may need to build x86_64 binaries

4. **Security Prompt**: First run may show a security prompt. Go to System Preferences > Security & Privacy to allow

## Getting Help

If you continue to have issues:

1. Run the diagnostic: `python check_mcp_servers.py`
2. Check the output of: `python -c "from sisypho.integrations.macos import get_accessibility_server_path; print(get_accessibility_server_path())"`
3. Verify permissions: `ls -l /path/to/server/binary`
4. Check architecture: `file /path/to/server/binary`

## Success!

Once installed correctly, you can import and use sisypho:

```python
import sisypho
from sisypho.corelib import browser, os_utils
from sisypho.utils import RecorderContext
from sisypho.integrations.macos import get_servers_dir

print(f"Sisypho {sisypho.__version__} ready!")
```
