#!/usr/bin/env python3
"""
MCP Server for Sisypho SDK.

This module provides a simple MCP server with dummy tools for testing and demonstration.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional
from mcp.server import FastMCP
import os
import json
from sisypho.utils import Workflow

# Set up logging to stderr to avoid interfering with MCP protocol
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
server = FastMCP("Sisypho MCP Server")

def dummy_tool(message: str) -> str:
    """A dummy tool that returns a simple message."""
    return f"Dummy tool received: {message}"

def get_server_info() -> str:
    """Get information about the MCP server."""
    return "Sisypho MCP Server v1.0.0\nThis is a dummy MCP server for testing purposes."

# Register tools with the server
server.add_tool(
    dummy_tool,
    name="dummy_tool",
    description="A dummy tool that returns a simple message"
)

server.add_tool(
    get_server_info,
    name="get_server_info", 
    description="Get information about the MCP server"
)

def load_workflows(workflow_directory: str = "."):
    """Load workflows from the given directory."""
    workflows = []
    for file in os.listdir(workflow_directory):
        if file.endswith(".json"):
            with open(os.path.join(workflow_directory, file), "r") as f:
                workflow_data = json.load(f)
                workflow = Workflow.from_dict(workflow_data)
                workflows.append(workflow)
    logger.info(f"Loaded {len(workflows)} workflows from {workflow_directory}")
    return workflows

async def run_server(workflow_directory: str = "."):
    """Run the MCP server."""
    logger.info(f"Starting Sisypho MCP Server on stdio")
    workflows = load_workflows(workflow_directory=workflow_directory)
    for i, workflow in enumerate(workflows):
        if len(workflow.code) > 0:
            # Create a wrapper function with proper type annotations
            def create_workflow_runner(wf: Workflow):
                def run_workflow_wrapper() -> str:
                    """Run a specific workflow and return the result."""
                    try:
                        result = wf.run_workflow()
                        return f"Workflow executed successfully: {result}"
                    except Exception as e:
                        return f"Workflow execution failed: {str(e)}"
                return run_workflow_wrapper
            
            server.add_tool(
                create_workflow_runner(workflow),
                name=f"run_workflow_{i}",
                description=workflow.task_prompt
            )

    
    try:
        # Run the server using stdio transport (standard for MCP)
        await server.run_stdio_async()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        pass
    except Exception as e:
        logger.error(f"Server error: {e}")
        pass
        raise

if __name__ == "__main__":
    # Set up basic logging to stderr
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    # Run the server
    asyncio.run(run_server())
