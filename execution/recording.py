#!/usr/bin/env python3
"""
Record - Multi-MCP Server Manager

This module provides functionality to load and manage multiple MCP servers
using persistent_mcp_client, similar to composer.py and executor.py.
"""

import argparse
import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.persistent_mcp_client import PersistentMCPClient, Tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPRecordManager:
    """
    Manages multiple MCP server connections for recording and monitoring purposes.

    This class provides functionality to:
    - Load multiple MCP servers from an array of paths
    - List available tools from all servers
    - Call tools across different servers
    - Monitor and record server interactions
    """

    def __init__(self, mcp_server_paths: List[str] = None):
        """
        Initialize the MCP Record Manager.

        Args:
            mcp_server_paths: List of paths to MCP server executables
        """
        self.mcp_server_paths = mcp_server_paths or []
        self.clients: Dict[str, PersistentMCPClient] = {}
        self.server_names: Dict[str, str] = {}
        self.initialized = False

    def add_server(self, server_path: str, server_name: Optional[str] = None) -> bool:
        """
        Add an MCP server to the manager.

        Args:
            server_path: Path to the MCP server executable
            server_name: Optional name for the server (defaults to path basename)

        Returns:
            True if server was added successfully, False otherwise
        """
        if not server_name:
            server_name = Path(server_path).stem

        if server_name in self.clients:
            logger.warning(f"Server '{server_name}' already exists")
            return False

        try:
            print(f"DEBUG: Creating PersistentMCPClient for server path: {server_path}")
            client = PersistentMCPClient(server_path)
            self.clients[server_name] = client
            self.server_names[server_path] = server_name
            logger.info(f"Added MCP server '{server_name}' from path: {server_path}")
            print(f"DEBUG: Successfully added server '{server_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to add server '{server_path}': {e}")
            print(f"DEBUG: Failed to add server '{server_path}': {e}")
            return False

    def initialize_all(self) -> bool:
        """
        Initialize all MCP servers.

        Returns:
            True if all servers initialized successfully, False otherwise
        """
        if self.initialized:
            return True

        print(f"DEBUG: Initializing {len(self.clients)} servers")
        success = True
        for server_name, client in self.clients.items():
            try:
                print(f"DEBUG: Starting server '{server_name}'")
                client.start()
                logger.info(f"Initialized server '{server_name}'")
                print(f"DEBUG: Successfully initialized server '{server_name}'")
            except Exception as e:
                logger.error(f"Failed to initialize server '{server_name}': {e}")
                print(f"DEBUG: Failed to initialize server '{server_name}': {e}")
                success = False

        self.initialized = success
        print(f"DEBUG: All servers initialized: {success}")
        return success

    def get_all_tools(self) -> Dict[str, List[Tool]]:
        """
        Get all available tools from all servers.

        Returns:
            Dictionary mapping server names to lists of available tools
        """
        if not self.initialized:
            self.initialize_all()

        all_tools = {}
        for server_name, client in self.clients.items():
            try:
                tools = client.get_tools()
                all_tools[server_name] = tools
                # logger.info(f"Server '{server_name}' has {len(tools)} tools")
            except Exception as e:
                logger.error(f"Failed to get tools from server '{server_name}': {e}")
                all_tools[server_name] = []

        return all_tools

    def find_tool_server(self, tool_name: str) -> Optional[str]:
        """
        Find which server provides a specific tool.

        Args:
            tool_name: Name of the tool to find

        Returns:
            Server name that provides the tool, or None if not found
        """
        all_tools = self.get_all_tools()

        for server_name, tools in all_tools.items():
            for tool in tools:
                if tool.name == tool_name:
                    return server_name

        return None

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_name: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Call a tool from a specific server or auto-detect the server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            server_name: Optional server name (if not provided, will auto-detect)

        Returns:
            The result of the tool call, or None if failed
        """
        if not self.initialized:
            self.initialize_all()

        # If server name not provided, try to find it
        if not server_name:
            server_name = self.find_tool_server(tool_name)
            if not server_name:
                logger.error(f"Tool '{tool_name}' not found in any server")
                return None

        if server_name not in self.clients:
            logger.error(f"Server '{server_name}' not found")
            return None

        try:
            client = self.clients[server_name]
            result = client.call_tool_structured(tool_name, arguments)
            # logger.info(f"Successfully called tool '{tool_name}' on server '{server_name}'")
            return result
        except Exception as e:
            logger.error(
                f"Failed to call tool '{tool_name}' on server '{server_name}': {e}"
            )
            return None

    def list_servers(self) -> List[Dict[str, Any]]:
        """
        List all registered servers with their status.

        Returns:
            List of server information dictionaries
        """
        servers = []
        for server_name, client in self.clients.items():
            server_info = {
                "name": server_name,
                "initialized": client.initialized,
                "tools_count": len(client.tools) if client.initialized else 0,
            }
            servers.append(server_info)

        return servers

    def record_interaction(
        self, tool_name: str, arguments: Dict[str, Any], result: Any, server_name: str
    ) -> None:
        """
        Record a tool interaction for logging/monitoring purposes.

        Args:
            tool_name: Name of the tool that was called
            arguments: Arguments that were passed to the tool
            result: Result returned by the tool
            server_name: Name of the server that handled the call
        """
        interaction = {
            "timestamp": self._get_timestamp(),
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
            "server_name": server_name,
        }

        # Log the interaction
        logger.info(f"Recorded interaction: {tool_name} on {server_name}")

        # Here you could save to a file, database, etc.
        # For now, just log it
        print(f"RECORD: {json.dumps(interaction, indent=2)}")

    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime

        return datetime.now().isoformat()

    def cleanup(self) -> None:
        """Clean up all MCP client connections."""
        for server_name, client in self.clients.items():
            try:
                client.stop()
                logger.info(f"Stopped server '{server_name}'")
            except Exception as e:
                logger.error(f"Error stopping server '{server_name}': {e}")

        self.clients.clear()
        self.server_names.clear()
        self.initialized = False
        logger.info("All MCP clients cleaned up")

    def __enter__(self):
        """Context manager entry."""
        self.initialize_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP Record Manager - Load and manage multiple MCP servers"
    )
    parser.add_argument("--output-dir", "-o", help="Output directory for recordings")
    parser.add_argument(
        "--server-paths", "-s", nargs="+", help="Array of MCP server executable paths"
    )
    return parser.parse_args()


def record_mode(manager: MCPRecordManager, output_dir: str = None):
    """Run record mode for recording interactions."""
    from datetime import datetime
    from pathlib import Path

    # Set up output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"skills/{timestamp}")

    output_path.mkdir(parents=True, exist_ok=True)
    recording_file = output_path / "recording.jsonl"

    print(f"Starting recording in directory: {output_path}")
    print("Perform your task now!")
    print("Press Ctrl+C to stop recording...")

    # Clear any existing events and start fresh
    manager.call_tool("clear_captured_events", {})
    manager.call_tool("retrieve_write_interaction_queue", {})

    # Counter for periodic clearing
    poll_count = 0
    clear_interval = 10  # Clear events every 10 polls

    with open(recording_file, "w") as f:
        print("Recording started...")

        try:
            while True:
                # Poll for events with error handling
                try:
                    chrome_events = manager.call_tool(
                        "retrieve_write_interaction_queue", {}
                    )
                except Exception as e:
                    error_msg = str(e)
                    if (
                        "timeout" in error_msg.lower()
                        or "connection" in error_msg.lower()
                    ):
                        print(f"Chrome extension disconnected: {error_msg}")
                        print("Stopping polling - extension is no longer available")
                        break
                    else:
                        print(f"Error polling chrome events: {error_msg}")
                        chrome_events = {"interactions": []}

                # Poll for AX events with better error handling
                try:
                    ax_events = manager.call_tool("get_captured_events", {})
                except Exception as e:
                    print(f"Error polling AX events: {e}")
                    ax_events = None

                # Periodic clearing to prevent memory issues
                poll_count += 1
                if poll_count % clear_interval == 0:
                    print(f"Clearing events after {clear_interval} polls")
                    try:
                        manager.call_tool("clear_captured_events", {})
                    except Exception as e:
                        print(f"Error clearing events: {e}")

                # Collect and save events
                all_events = []

                # Process Chrome events
                if (
                    isinstance(chrome_events, dict)
                    and "interactions" in chrome_events
                    and len(chrome_events["interactions"]) > 0
                ):
                    print(
                        f"Number of Chrome events: {len(chrome_events['interactions'])}"
                    )
                    for event in chrome_events["interactions"]:
                        del event["domState"]
                        event["source"] = "chrome"
                        all_events.append(event)

                # Process AX events with better type checking
                if ax_events is not None:
                    if isinstance(ax_events, list) and len(ax_events) > 0:
                        print(f"Number of AX events: {len(ax_events)}")
                        for event in ax_events:
                            if type(event) != dict:
                                print(f"Event is not a dict: {event}")
                                continue
                            if event.get("type") == "scroll":
                                # print(f"Skipping scroll event: {event.get('type')}")
                                continue
                            # Clean up paths that can be large
                            if "details" in event:
                                event["details"].pop("element_semantic_path", None)
                                event["details"].pop("element_path", None)

                                if isinstance(event["details"], dict):
                                    details = event["details"].copy()
                                    for key, value in event["details"].items():
                                        if value == "None" or value == "Unknown":
                                            print(
                                                f"Removing key {key} from event since value is {value}"
                                            )
                                            details.pop(key)
                                    event["details"] = details

                            event_record = {
                                "timestamp": event.get(
                                    "timestamp", datetime.now().isoformat()
                                ),
                                "source": event["details"].get(
                                    "source", "accessibility"
                                )
                                if "details" in event
                                else "accessibility",
                                "event": event,
                            }
                            all_events.append(event_record)
                            print(f"Added AX event: {event.get('type', 'unknown')}")
                    elif isinstance(ax_events, dict):
                        if ax_events.get("success") == False:
                            print(
                                f"AX events error: {ax_events.get('message', 'Unknown error')}"
                            )
                        else:
                            print(f"AX events response: {ax_events}")
                    elif isinstance(ax_events, str):
                        print(f"AX events returned string: {ax_events}")
                    else:
                        print(f"AX events returned unexpected type: {type(ax_events)}")
                else:
                    print("AX events is None - EventPollingApp may not be running")

                # Sort by timestamp and write
                all_events.sort(key=lambda x: x["timestamp"])
                print(f"Writing {len(all_events)} events to file")
                for event_record in all_events:
                    f.write(json.dumps(event_record) + "\n")
                    f.flush()

                time.sleep(1)

        except KeyboardInterrupt:
            print("\nRecording stopped by user.")
            # Ensure any remaining buffered data is written to file
            f.flush()
            print("Recording data saved to file.")

    print("Recording complete!")
    print(f"Output directory: {output_path}")


def main():
    """Main entry point."""
    args = parse_args()

    # Use provided server paths or fall back to defaults
    if args.server_paths:
        server_paths = args.server_paths
        print(f"Using provided server paths: {server_paths}")
    else:
        # Default server paths if none provided
        default_servers = [
            "integrations/macos/servers/.build/arm64-apple-macosx/release/AccessibilityMCPServer",
            "integrations/chrome/chrome-extension-bridge-mcp/node_modules/.bin/tsx integrations/chrome/chrome-extension-bridge-mcp/examples/mcp.ts",
        ]
        server_paths = default_servers
        print(f"Using default server paths: {server_paths}")

    # Create and initialize the manager
    manager = MCPRecordManager()

    # Add all servers
    for server_path in server_paths:
        manager.add_server(server_path)

    # Note: EventPollingApp CLI tool is started by the Electron main process
    # before calling this recording script

    try:
        # Initialize all servers
        if not manager.initialize_all():
            print("Failed to initialize some servers")
            return

        record_mode(manager, args.output_dir)

    finally:
        manager.cleanup()


if __name__ == "__main__":
    main()
