#!/usr/bin/env python3
"""
Command-line interface for Sisypho SDK.

This module provides the main CLI entry point with subcommand support.
"""

import argparse
import asyncio
import sys
from typing import Optional

from .commands import create_command, run_command, mcp_command


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="python -m sisypho",
        description="Sisypho SDK - Browser automation, workflow recording, and skill execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m sisypho create --task "open chrome and type hello"
  python -m sisypho create --task "open chrome and type hello" --record
  python -m sisypho run --workflow workflow.json
  python -m sisypho run --interactive
  python -m sisypho mcp --workflow-directory ./workflows
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True
    )
    
    # Create command
    create_parser = subparsers.add_parser(
        "create",
        help="Create a new workflow (optionally with recording)"
    )
    create_parser.add_argument(
        "--task",
        "-t",
        type=str,
        required=True,
        help="Task description for the workflow to be created"
    )
    create_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path for the workflow (default: auto-generated)"
    )
    create_parser.add_argument(
        "--record",
        "-r",
        action="store_true",
        help="Record user actions while creating the workflow"
    )
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run an existing workflow"
    )
    run_parser.add_argument(
        "--workflow",
        "-w",
        type=str,
        help="Path to the workflow file to run"
    )
    run_parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode (uses default test workflow)"
    )
    run_parser.add_argument(
        "--task",
        "-t",
        type=str,
        help="Task description to execute (overrides workflow task)"
    )
    
    # MCP command
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Launch MCP server"
    )
    mcp_parser.add_argument(
        "--workflow-directory",
        "-w",
        type=str,
        default=".",
        help="Directory to load workflows from (default: current directory)"
    )
    
    return parser


async def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        if args.command == "create":
            await create_command(args)
        elif args.command == "run":
            await run_command(args)
        elif args.command == "mcp":
            await mcp_command(args)
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(f"Error executing command '{args.command}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
