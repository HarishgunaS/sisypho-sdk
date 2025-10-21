#!/usr/bin/env python3
"""
Persistent MCP Client for macOS Accessibility Server

This module provides a persistent MCP client that can be used by the executor
to maintain a long-running connection to the MCP server.
"""

import json
import subprocess
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Represents an MCP tool with its metadata."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class PersistentMCPClient:
    """
    Persistent MCP Client that maintains a long-running connection to the MCP server.
    
    This client is designed to be used by the executor and provides a simple interface
    for tool listing and calling.
    """
    
    def __init__(self, server_path: str):
        """
        Initialize the persistent MCP client.
        
        Args:
            server_path: Path to the MCP server executable
        """
        self.server_path = server_path
        self.process = None
        self.request_id = 0
        self.tools: List[Tool] = []
        self.initialized = False
        
    def _get_next_id(self) -> int:
        """Get the next request ID."""
        self.request_id += 1
        return self.request_id
    
    def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message to the server."""
        if not self.process:
            raise RuntimeError("Server process not started")
        
        message_str = json.dumps(message) + "\n"
        self.process.stdin.write(message_str.encode('utf-8'))
        self.process.stdin.flush()
        logger.debug(f"Sent: {message_str.strip()}")
    
    def _receive_message(self) -> Dict[str, Any]:
        """Receive a JSON-RPC message from the server."""
        if not self.process:
            raise RuntimeError("Server process not initialized")
        
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Server closed connection")
        
        message = json.loads(line.decode('utf-8').strip())
        logger.debug(f"Received: {message}")
        return message
    
    def start(self) -> None:
        """Start the MCP server process and initialize the connection."""
        if self.initialized:
            return
        
        try:
            # Start the server process
            # Split the server path into command and arguments
            cmd_parts = self.server_path.split()
            self.process = subprocess.Popen(
                cmd_parts,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # Suppress subprocess stderr output
                text=False,  # Use binary mode for better control
                bufsize=0
            )
            
            # Wait a moment for the server to start
            time.sleep(0.1)
            
            # Initialize the connection
            self._initialize()
            
            # List available tools
            self._list_tools()
            
            logger.info("Persistent MCP client started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start persistent MCP client: {e}")
            self.stop()
            raise
    
    def _initialize(self) -> None:
        """Initialize the MCP connection."""
        init_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "persistent-mcp-client",
                    "version": "1.0.0"
                }
            }
        }
        
        self._send_message(init_request)
        response = self._receive_message()
        
        if "error" in response:
            raise RuntimeError(f"Initialization failed: {response['error']}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self._send_message(initialized_notification)
        
        self.initialized = True
        logger.info("MCP connection initialized")
    
    def _list_tools(self) -> None:
        """List available tools from the server."""
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/list"
        }
        
        self._send_message(list_tools_request)
        response = self._receive_message()
        
        if "error" in response:
            logger.warning(f"Failed to list tools: {response['error']}")
            return
        
        tools_data = response.get("result", {}).get("tools", [])
        self.tools = []
        
        for tool_data in tools_data:
            tool = Tool(
                name=tool_data["name"],
                description=tool_data["description"],
                input_schema=tool_data.get("inputSchema", {})
            )
            self.tools.append(tool)
        
        logger.info(f"Found {len(self.tools)} tools")
    
    def get_tools(self) -> List[Tool]:
        """Get the list of available tools."""
        if not self.initialized:
            self.start()
        return self.tools.copy()
    
    def call_tool_structured(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """
        Call a tool with the given arguments and return structured data.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            The result of the tool call as a Python object (dict, list, etc.), or None if failed
        """
        if not self.initialized:
            self.start()
        
        call_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            self._send_message(call_request)
            response = self._receive_message()
            if "error" in response:
                logger.error(f"Tool call failed: {response['error']}")
                return None
            
            result = response.get("result", {})
            content = result.get("content", [])
            
            # Process content items
            if content and len(content) > 0:
                for item in content:
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        # Handle empty or whitespace-only text
                        if not text or text.strip() == "":
                            return None
                        # Try to parse as JSON, return as string if it fails
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            # If it's not valid JSON, return as string
                            return text
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return None

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """
        Call a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            The result of the tool call as a string, or None if failed
        """
        if not self.initialized:
            self.start()
        
        call_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            self._send_message(call_request)
            response = self._receive_message()
            
            if "error" in response:
                logger.error(f"Tool call failed: {response['error']}")
                return None
            
            result = response.get("result", {})
            content = result.get("content", [])
            
            # Process content items
            if content and len(content) > 0:
                for item in content:
                    if item.get("type") == "text":
                        return item.get("text", "")
            
            return ""
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return None
    
    def stop(self) -> None:
        """Stop the MCP client and server process."""
        if self.process:
            try:
                # Send shutdown notification
                shutdown_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/shutdown"
                }
                self._send_message(shutdown_notification)
                
                # Wait a moment for graceful shutdown
                time.sleep(0.1)
                
                # Terminate the process
                self.process.terminate()
                self.process.wait(timeout=5)
                
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.warning(f"Error during shutdown: {e}")
            finally:
                self.process = None
                self.initialized = False
        
        logger.info("Persistent MCP client stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop() 