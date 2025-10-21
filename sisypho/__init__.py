"""
Sisypho SDK - Browser automation, workflow recording, and skill execution with MCP integration.

This package provides tools for:
- Browser automation via Playwright
- Workflow recording and playback
- MCP (Model Context Protocol) server integration
- macOS accessibility automation
- Skill execution and management

Modules:
    corelib: Core library with browser, Excel, Gmail, Google Drive, and OS utilities
    execution: Recording and skill execution functionality
    integrations: Platform-specific integrations (macOS, Chrome, etc.)
    utils: Utility functions and helper classes
"""

__version__ = "0.1.0"
__author__ = "Harishguna S"

# Import key modules for convenience
from . import corelib
from . import execution
from . import integrations
from . import utils

__all__ = [
    "corelib",
    "execution", 
    "integrations",
    "utils",
]

