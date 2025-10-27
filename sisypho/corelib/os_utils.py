"""
Core library for interacting with the operating system.
"""

from typing import List, Union, Dict, Any
import logging

logger = logging.getLogger(__name__)

_current_active_app = None

from sisypho.execution.persistent_mcp_client import PersistentMCPClient

# Global MCP client instance
_mcp_client_instance = None


def _get_mcp_client():
    global _mcp_client_instance
    if _mcp_client_instance is None:
        import os

        # Check if we're in a packaged environment by looking for RESOURCES_PATH
        resources_path = os.environ.get("RESOURCES_PATH")
        if resources_path:
            # In packaged environment, the binary is in the MacOS directory
            server_path = os.path.join(resources_path, "AccessibilityMCPServer")
        else:
            # Use the helper to get the correct path
            try:
                from sisypho.integrations.macos import get_accessibility_server_path
                server_path = str(get_accessibility_server_path())
            except (ImportError, FileNotFoundError):
                # Fallback to hardcoded path
                server_path = (
                    "sisypho/integrations/macos/servers/.build/release/AccessibilityMCPServer"
                )

        _mcp_client_instance = PersistentMCPClient(server_path)
        _mcp_client_instance.start()
    return _mcp_client_instance


def _cleanup_mcp_client():
    """Clean up the global MCP client instance."""
    global _mcp_client_instance
    if _mcp_client_instance:
        try:
            _mcp_client_instance.stop()
        except Exception as e:
            logger.warning(f"Error cleaning up MCP client: {e}")
        finally:
            _mcp_client_instance = None


def get_element_content(app_name: str, element_descriptor: str) -> str:
    """
    Get the content of an element.

    Args:
        app_name: The name of the app to get the content from.
        element_descriptor: The descriptor of the element to get the content from.

    Returns:
        The content of the element.

    Examples:
        >>> get_element_content(app_name="Google Chrome", element_descriptor="AXWindow[{{\"title\":\"Google Chrome\",\"index\":0}}] > AXGroup[{{\"index\":0}}] > AXButton[{{\"label\":\"New Tab\"}}]")
        'New Tab'
    """
    mcp_client = _get_mcp_client()
    return mcp_client.get_element_content(app_name, element_descriptor)


def _ensure_correct_app(app_name: str) -> bool:
    mcp_client = _get_mcp_client()
    global _current_active_app
    if not app_name:
        return True

    if _current_active_app == app_name:
        return True

    try:
        result = mcp_client.call_tool_structured(
            "switch_to_app", {"app_name": app_name}
        )

        if result and isinstance(result, dict) and result.get("success", False):
            _current_active_app = app_name
            import time

            time.sleep(0.2)
            return True
        else:
            message = (
                result.get("message", "Unknown error") if result else "No response"
            )
            logger.error(f"Failed to switch to app '{app_name}': {message}")
            return False
    except Exception as e:
        logger.error(f"Failed to switch to app '{app_name}': {e}")
        return False

    _current_active_app = app_name
    return True


def _preprocess_type_text(text: str) -> Union[str, List[Union[str, Dict[str, Any]]]]:
    """
    Preprocess text to handle special escape sequences.

    Special sequences:
    - "\r" or "\n" -> Enter key
    - "\t" -> Tab key
    - "\\" -> Literal backslash
    - "\s" -> Space key
    - "\b" -> Backspace key

    Returns:
        Either a string (if no special sequences found) or a list of commands
        (strings for text, dicts for keystrokes)
    """
    if "\\" not in text:
        return text

    commands = []
    i = 0
    current_text = ""

    while i < len(text):
        char = text[i]

        if char == "\\" and i + 1 < len(text):
            # Check for escape sequence
            next_char = text[i + 1]

            if next_char == "\\":
                # Literal backslash
                current_text += "\\\\"
                i += 2
            elif next_char == "r" or next_char == "n":
                # Enter key
                if current_text:
                    commands.append(current_text)
                    current_text = ""
                commands.append({"key": "return"})
                i += 2
            elif next_char == "t":
                # Tab key
                if current_text:
                    commands.append(current_text)
                    current_text = ""
                commands.append({"key": "tab"})
                i += 2
            elif next_char == "s":
                # Space key
                if current_text:
                    commands.append(current_text)
                    current_text = ""
                commands.append({"key": "space"})
                i += 2
            elif next_char == "b":
                # Backspace key
                if current_text:
                    commands.append(current_text)
                    current_text = ""
                commands.append({"key": "delete"})
                i += 2
            else:
                # Not a recognized escape sequence, treat as literal "\"
                current_text += "\\"
                i += 1
        else:
            # Regular character
            current_text += char
            i += 1

    # Add any remaining text
    if current_text:
        commands.append(current_text)

    # If we only have one command and it's text, return just the string
    if len(commands) == 1 and isinstance(commands[0], str):
        return commands[0]

    return commands


def type(app_name: str, text: str) -> bool:
    """
    Type a text into an element.

    Args:
        app_name: The name of the app to type in.
        text: The text to type.

    Returns:
        True if the text was typed successfully, False otherwise.

    Examples:
        >>> type(app_name="Google Chrome", text="cat pictures")
    """
    try:
        _ensure_correct_app(app_name)
        processed_text = _preprocess_type_text(text)
        mcp_client = _get_mcp_client()
        # If preprocessing resulted in multiple commands, execute them separately
        if isinstance(processed_text, list):
            for command in processed_text:
                if isinstance(command, str):
                    # Regular text to type
                    arguments = {"text": command}
                    result = mcp_client.call_tool_structured("send_string", arguments)
                else:
                    # Special keystroke command
                    result = mcp_client.call_tool_structured("send_keystroke", command)

                if (
                    not result
                    or not isinstance(result, dict)
                    or not result.get("success", False)
                ):
                    logger.error(f"Failed to execute command: {command}")
                    return False
            return True
        else:
            # Single text string to type
            arguments = {"text": processed_text}
            result = mcp_client.call_tool_structured("send_string", arguments)

        if result and isinstance(result, dict):
            success = result.get("success", False)
            message = result.get("message", "Unknown result")
            logger.info(f"Type action result: {message}")
            return success
        else:
            logger.error("Invalid result format from send_string")
            return False
    except Exception as e:
        logger.error(f"Failed to type text: {e}")
        return False


def click(
    app_name: str,
    element_descriptor: str,
    is_right_click: bool,
    is_double_click: bool,
    duration: int,
) -> bool:
    """
    Click on an element.

    Args:
        app_name: The name of the app to click in.
        element_descriptor: The descriptor of the element to click on.
        is_right_click: Whether the click is a right click.
        is_double_click: Whether the click is a double click.
        duration: The duration of the click in milliseconds.

    Returns:
        True if the click was successful, False otherwise.

    Examples:
        >>> click(app_name="Google Chrome", element_descriptor="AXWindow[{{\"title\":\"Google Chrome\",\"index\":0}}] > AXGroup[{{\"index\":0}}] > AXButton[{{\"label\":\"New Tab\"}}]", is_right_click=False, is_double_click=False, duration=100)
    """
    try:
        _ensure_correct_app(app_name)
        mcp_client = _get_mcp_client()

        # Prepare arguments for perform_action
        arguments: Dict[str, Any] = {"action": "AXPress"}

        # Add path if element_descriptor is provided
        if element_descriptor:
            arguments["path"] = element_descriptor
        if app_name:
            arguments["app_name"] = app_name

        # Add click type modifiers
        if is_right_click:
            arguments["action"] = "AXShowMenu"
        # if is_double_click:
        #     arguments["action"] = "double_click"

        # Call the perform_action tool
        result = mcp_client.call_tool_structured("perform_action", arguments)

        if result and isinstance(result, dict):
            success = result.get("success", False)
            message = result.get("message", "Unknown result")
            logger.info(f"Click action result: {message}")
            return success
        else:
            logger.error("Invalid result format from perform_action")
            return False

    except Exception as e:
        logger.error(f"Error executing click step: {e}")
        return False


def command(
    app_name: str, element_descriptor: str, modifier_keys: List[str], key: str
) -> bool:
    """
    Press a keyboard command.

    Args:
        app_name: The name of the app to press the command in.
        element_descriptor: The descriptor of the element to press the command on.
        modifier_keys: The modifier keys to press.
        key: The key to press.

    Returns:
        True if the command was successful, False otherwise.

    Examples:
        >>> command(app_name="Google Chrome", element_descriptor="AXWindow[{{\"title\":\"Google Chrome\",\"index\":0}}] > AXGroup[{{\"index\":0}}] > AxTextField[{{\"label\":\"Search\"}}]", modifier_keys=["command"], key="c")
    """
    try:
        _ensure_correct_app(app_name)
        mcp_client = _get_mcp_client()

        if not key:
            logger.error("Command step missing required 'key' field")
            return False

        # Prepare arguments for send_keystroke
        arguments: Dict[str, Any] = {"key": key}

        # Add modifiers if provided
        if modifier_keys:
            arguments["modifiers"] = modifier_keys

        # Call the send_keystroke tool
        result = mcp_client.call_tool_structured("send_keystroke", arguments)

        if result and isinstance(result, dict):
            success = result.get("success", False)
            message = result.get("message", "Unknown result")
            logger.info(f"Command action result: {message}")
            return success
        else:
            logger.error("Invalid result format from send_keystroke")
            return False

    except Exception as e:
        logger.error(f"Error executing command step: {e}")
        return False


def open_app(app_name: str):
    """
    Open an app on macOS.
    This is required when users ask to open an app, or use an app on MacOS for automation purposes.

    Args:
        app_name: The name of the app to open.
    """
    command("", "", ["command"], "space")
    type("", app_name)
    command("", "", [], "return")


def open_file_in_finder(file_path: str) -> bool:
    """
    Navigate to and select a file in Finder using the Go to Folder dialog (Command+Shift+G).
    
    This function should ONLY be called when Finder is already open and focused. 
    It is typically used after clicking an attach/upload button in an app which opens Finder,
    or when Finder is directly opened for file selection.
    
    Args:
        file_path: The path to the file to select in Finder. Can be absolute or use ~ for home.
        
    Returns:
        True if the file was successfully navigated to, False otherwise.
        
    Examples:
        >>> # After clicking an attach button that opened Finder:
        >>> open_file_in_finder("~/Documents/report.pdf")
        True
        >>> # With absolute path:
        >>> open_file_in_finder("/Users/john/Downloads/image.png")
        True
    """
    try:
        import time
        
        # Open the Go to Folder dialog using Command+Shift+G
        logger.info(f"Opening Go to Folder dialog to navigate to: {file_path}")
        if not command("Finder", "", ["command", "shift"], "g"):
            logger.error("Failed to open Go to Folder dialog")
            return False
        
        # Small delay to ensure the dialog opens
        time.sleep(0.3)
        
        # Type the file path
        if not type("Finder", file_path):
            logger.error(f"Failed to type file path: {file_path}")
            return False
        
        # Press Enter to navigate to the file
        if not command("Finder", "", [], "return"):
            logger.error("Failed to confirm navigation")
            return False
        
        # Small delay to allow navigation to complete
        time.sleep(0.2)
        
        logger.info(f"Successfully navigated to file: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error in open_file_in_finder: {e}")
        return False

