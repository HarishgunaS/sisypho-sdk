#!/usr/bin/env python3
"""
Command-line interface for Sisypho SDK.

This module allows the sisypho package to be executed as a command-line tool
using: python -m sisypho

Usage:
    python -m sisypho create --task "description" [--record]  # Create workflows
    python -m sisypho run [options]                           # Run workflows
    python -m sisypho --help                                  # Show help
"""

import sys
import asyncio
from .cli import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
