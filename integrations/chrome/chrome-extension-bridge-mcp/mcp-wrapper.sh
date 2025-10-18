#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Try to find Node.js in common locations
NODE_PATHS=(
    "/usr/local/bin/node"
    "/opt/homebrew/bin/node"
    "/usr/bin/node"
    "$(which node)"
)

NODE_PATH=""
for path in "${NODE_PATHS[@]}"; do
    if [ -x "$path" ]; then
        NODE_PATH="$path"
        break
    fi
done

if [ -z "$NODE_PATH" ]; then
    echo "ERROR: Node.js not found. Please install Node.js and try again." >&2
    exit 1
fi

# Run the compiled JavaScript file
exec "$NODE_PATH" "$SCRIPT_DIR/dist/examples/mcp.js" "$@"
