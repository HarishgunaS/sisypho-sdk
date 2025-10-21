#!/bin/bash

echo "Building AccessibilityMCPServer..."
swiftly run swift build --configuration release

# Build the command line tool
echo "Building EventPollingApp CLI..."
cd EventPollingApp
swiftly run swift build --configuration release

