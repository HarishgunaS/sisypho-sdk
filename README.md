# Sisypho SDK

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

A powerful automation SDK for macOS that enables seamless workflow recording, skill execution, and intelligent task automation through desktop accessibility APIs and browser integration. Now includes MCP (Model Context Protocol) server support to create custom UI-based tools for computer use agents.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI Interface](#cli-interface)
  - [Desktop Automation](#desktop-automation)
  - [Browser Automation](#browser-automation)
  - [Workflow Recording](#workflow-recording)
  - [Skill Execution](#skill-execution)
  - [MCP Integration](#mcp-integration)
- [API Reference](#api-reference)
- [Chrome Extension](#chrome-extension)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

### **Desktop Automation**
- Native macOS accessibility API integration
- System-wide UI element interaction
- Window management and application control
- Event recording and playback

### **Browser Automation**
- Playwright integration with user's Chrome installation
- Robust Chrome profile management
- Cross-browser compatibility

### **Workflow Recording & Playback**
- Real-time action recording for both desktop and browser
- JSON-based workflow serialization
- Intelligent skill generation from recorded actions
- Automated workflow optimization

### **Agentic AI Integration**
- Built-in MCP (Model Context Protocol) server for computer use agents
- Automatic workflow-to-tool conversion for AI integration
- Custom UI automation tools accessible via MCP protocol
- LLM-powered task execution and workflow generation
- Adaptive skill execution with error handling (WIP)

### **Developer-Friendly**
- Clean Python API with type hints
- Comprehensive CLI interface
- Modular architecture for easy extension
- Rich debugging and logging capabilities

## Architecture

Sisypho SDK follows a modular architecture designed for flexibility and extensibility:

```
sisypho/
├── corelib/           # Core automation utilities
│   ├── browser.py     # Playwright browser management
│   ├── os_utils.py    # macOS system utilities
│   └── user.py        # User interaction helpers
├── execution/         # Workflow execution engine
│   ├── recording.py   # Action recording system
│   └── skill.py       # Skill execution framework
├── integrations/      # Platform-specific integrations
│   ├── macos/         # macOS accessibility servers
│   ├── chrome/        # Chrome extension bridge
│   └── windows/       # Windows support (WIP)
├── agentic/           # AI-powered automation
│   ├── generator.py   # Workflow generation
│   └── tools.py       # MCP tools and verification
├── mcp_server.py      # MCP server for computer use agents
└── cli.py             # Command-line interface
```

## Quick Start

### Prerequisites

- **macOS 11.0+** (required)
- **Python 3.10+** (required)
- **Google Chrome** (for browser automation)

### Installation

```bash
pip install sisypho
```

For detailed installation instructions and troubleshooting, see [INSTALL.md](INSTALL.md).

### Basic Usage

```python
import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

async def main():
    task_prompt = "Open Chrome and navigate to GitHub"
    
    # Record a workflow
    with RecorderContext() as recorder:
        await_task_completion()
    
    recording = recorder.get_recording()
    workflow = Workflow(recording, task_prompt)
    
    await workflow.generate_code()
    result = workflow.run_workflow()
    workflow.save()

# Run the async function
asyncio.run(main())
```

## Usage

### CLI Interface

Sisypho provides a comprehensive command-line interface for workflow creation and execution:

#### Create Workflows

```bash
# Create a workflow from natural language description
python -m sisypho create --task "open chrome and type hello"

# Create with recording enabled
python -m sisypho create --task "open chrome and type hello" --record

# Specify output file
python -m sisypho create --task "download file from website" --output workflow.json
```

#### Execute Workflows

```bash
# Run a saved workflow
python -m sisypho run --workflow workflow.json

# Run in interactive mode
python -m sisypho run --interactive
```

#### Launch MCP Server

```bash
# Launch MCP server with workflows from current directory
python -m sisypho mcp

# Launch MCP server with workflows from specific directory
python -m sisypho mcp --workflow-directory ./my-workflows
```

### Desktop Automation

Desktop automation leverages macOS accessibility APIs through natural language workflows:

```python
import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

async def desktop_automation_example():
    task_prompt = "Open TextEdit, create a new document, and type 'Hello, World!'"
    
    # Record the desktop actions
    with RecorderContext() as recorder:
        await_task_completion()
    
    recording = recorder.get_recording()
    workflow = Workflow(recording, task_prompt)
    
    await workflow.generate_code()
    result = workflow.run_workflow()
    workflow.save("desktop_automation.json")

asyncio.run(desktop_automation_example())
```

### Browser Automation

Browser automation uses Playwright with your existing Chrome installation through workflow recording:

```python
import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

async def browser_automation_example():
    task_prompt = "Open Chrome, navigate to GitHub, and search for 'sisypho'"
    
    # Record the browser actions
    with RecorderContext() as recorder:
        await_task_completion()
    
    recording = recorder.get_recording()
    workflow = Workflow(recording, task_prompt)
    
    await workflow.generate_code()
    result = workflow.run_workflow()
    workflow.save("browser_automation.json")

asyncio.run(browser_automation_example())
```

### Workflow Recording

Record user actions for later playback and analysis:

```python
import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

async def recording_example():
    task_prompt = "Record actions for email automation"
    
    with RecorderContext() as recorder:
        # Perform manual actions - they will be recorded
        await_task_completion()
    
    # Save the recording
    recording = recorder.get_recording()
    workflow = Workflow(recording, task_prompt)
    workflow.save("my_workflow.json")

asyncio.run(recording_example())
```

### MCP Integration

Integrate with MCP servers for enhanced AI capabilities:

```python
import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

async def mcp_integration_example():
    # Use natural language to describe complex workflows
    task_prompt = """Open Excel from Downloads, calculate total sales column, 
    and paste the result into a new Apple Notes entry."""
    
    with RecorderContext() as recorder:
        await_task_completion()
    
    recording = recorder.get_recording()
    workflow = Workflow(recording, task_prompt)
    
    # Generate optimized code using MCP servers
    await workflow.generate_code()
    result = workflow.run_workflow()
    workflow.save("mcp_workflow.json")

asyncio.run(mcp_integration_example())
```

#### MCP Server Setup and Usage

Launch Sisypho as an MCP server to expose your workflows as tools for computer use agents:

```bash
# Start the MCP server
python -m sisypho mcp --workflow-directory ./workflows
```

Connect from your computer use agent or MCP client:

```python
# Example MCP client configuration
from mcp.client import Client

async def use_sisypho_tools():
    # Connect to Sisypho MCP server
    client = Client()
    await client.connect("stdio", command=["python", "-m", "sisypho", "mcp"])
    
    # List available workflow tools
    tools = await client.list_tools()
    print(f"Available automation tools: {[tool.name for tool in tools]}")
    
    # Execute a workflow tool
    result = await client.call_tool("run_workflow_0", {})
    print(f"Workflow result: {result}")
```

Each workflow in your directory becomes an executable tool that computer use agents can call to perform UI automation tasks.

## Custom UI Tools for Computer Use Agents

Sisypho SDK enables you to create reusable UI automation tools that computer use agents can leverage through the MCP protocol. Here's how workflows become powerful automation tools:

### Workflow-to-Tool Conversion

When you launch the MCP server, Sisypho automatically:

1. **Scans** your workflow directory for `.json` workflow files
2. **Registers** each workflow as an MCP tool with its task description
3. **Exposes** the tools via the MCP protocol for agent consumption

```bash
# Directory structure
./automation-tools/
├── gmail_automation.json     # Becomes "run_workflow_0" tool
├── slack_notifications.json  # Becomes "run_workflow_1" tool
└── data_entry.json          # Becomes "run_workflow_2" tool

# Launch MCP server
python -m sisypho mcp --workflow-directory ./automation-tools
```

### Agent Integration Examples

Computer use agents can now call your custom UI tools:

```python
# Agent discovers available tools
tools = await mcp_client.list_tools()
# Returns: [
#   {"name": "run_workflow_0", "description": "Automate Gmail inbox management"},
#   {"name": "run_workflow_1", "description": "Send Slack status updates"},
#   {"name": "run_workflow_2", "description": "Fill customer data forms"}
# ]

# Agent executes UI automation
result = await mcp_client.call_tool("run_workflow_0", {})
# Sisypho performs the recorded Gmail automation workflow
```

### Building Tool Libraries

Create specialized tool libraries for different use cases:

```bash
# Business productivity tools
./business-tools/
├── calendar_management.json
├── email_templates.json
└── report_generation.json

# Development workflow tools  
./dev-tools/
├── github_pr_workflow.json
├── deployment_checks.json
└── code_review_automation.json

# Customer service tools
./support-tools/
├── ticket_routing.json
├── customer_onboarding.json
└── feedback_collection.json
```

Each directory becomes a specialized MCP server providing domain-specific UI automation capabilities to computer use agents.

## API Reference

### Core Modules

#### `sisypho.utils`
- `RecorderContext` - Context manager for recording actions
- `await_task_completion()` - Wait for user to complete manual actions during recording
- `Workflow(recording, task_prompt)` - Main workflow orchestrator
  - `generate_code()` - Generate automation code from recording and prompt
  - `run_workflow()` - Execute the generated workflow
  - `save(path)` - Save workflow to file
  - `load(path)` - Load workflow from file

#### `sisypho.execution.skill`
- `SkillExecutor` - Main class for skill execution
  - `load_skill_from_file(path)` - Load skill from Python file
  - `execute_skill_code(code)` - Execute skill code directly

#### `sisypho.corelib.browser`
- `navigate(url)` - Navigate to a URL
- `click_element(selector)` - Click element by CSS selector
- `type_text(selector, text)` - Type text into form field
- `getContent(rootNode)` - Extract content from page

#### `sisypho.corelib.os_utils`
- `click(app_name, element_descriptor, is_right_click, is_double_click, duration)` - Click UI element
- `type(app_name, text)` - Type text in application
- `command(app_name, element_descriptor, modifier_keys, key)` - Press keyboard command
- `open_app(app_name)` - Open application on macOS

## Chrome Extension

Install the Sisypho Chrome Extension to enable browser action recording:

**[Install from Chrome Web Store](https://chromewebstore.google.com/detail/sisypho-chrome-ext/bllfdccnpfjfdofbepfncfdhbjjcjfcm?utm_source=item-share-cb&pli=1)**

The extension enables:
- Real-time browser action recording
- Seamless integration with Sisypho workflows
- Visual feedback during recording sessions
- Automatic workflow generation from browser interactions

## Examples

### Example 1: Automated Web Form Filling

```python
import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

async def web_form_automation():
    task_prompt = """Navigate to example.com contact form, 
    fill in name as 'John Doe', email as 'john@example.com', 
    message as 'Hello from Sisypho!', and submit the form."""
    
    with RecorderContext() as recorder:
        await_task_completion()
    
    recording = recorder.get_recording()
    workflow = Workflow(recording, task_prompt)
    
    await workflow.generate_code()
    result = workflow.run_workflow()
    workflow.save("web_form_automation.json")

asyncio.run(web_form_automation())
```

### Example 2: Desktop Application Automation

```python
import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

async def desktop_app_automation():
    task_prompt = """Open TextEdit, create a new document, 
    type 'Automated document creation with Sisypho!', 
    save the document as 'automated_document.txt'."""
    
    with RecorderContext() as recorder:
        await_task_completion()
    
    recording = recorder.get_recording()
    workflow = Workflow(recording, task_prompt)
    
    await workflow.generate_code()
    result = workflow.run_workflow()
    workflow.save("desktop_automation.json")

asyncio.run(desktop_app_automation())
```

### Example 3: Complex Multi-App Workflow

```python
import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

async def multi_app_workflow():
    task_prompt = """Open Excel from Downloads, calculate the total sales column, 
    and paste the result into a new Apple Notes entry."""
    
    with RecorderContext() as recorder:
        await_task_completion()
    
    recording = recorder.get_recording()
    workflow = Workflow(recording, task_prompt)
    
    await workflow.generate_code()
    result = workflow.run_workflow()
    workflow.save("multi_app_workflow.json")
    
    print("Multi-app workflow executed successfully!")

asyncio.run(multi_app_workflow())
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Clone the repository
2. Install development dependencies: `pip install -e .[dev]`
3. Build platform servers: `python -m sisypho.setup_servers`
4. Run tests: `pytest`

### Platform Support

- **macOS**: Full support (primary platform)
- **Windows**: Work in progress
- **Linux**: Not currently supported

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Contact

- **Primary**: satgu7[at]gmail[dot]com
- **Secondary**: saumik[dot]13[at]gmail.com

For bug reports and feature requests, please use the [GitHub Issues](https://github.com/HarishgunaS/sisypho-sdk/issues) page.

