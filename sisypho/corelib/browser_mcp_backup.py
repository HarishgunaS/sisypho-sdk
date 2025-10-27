"""
Core library for interacting with the browser.
"""

from typing import Dict, Any, Optional, Union, List
import logging

logger = logging.getLogger(__name__)

from sisypho.execution.persistent_mcp_client import PersistentMCPClient

def _get_chrome_mcp_client():
    """Get MCP client for Chrome extension bridge."""
    chrome_server_path = "../integrations/chrome/chrome-extension-bridge-mcp/dist/server.js"
    mcp_client = PersistentMCPClient(chrome_server_path)
    mcp_client.start()
    return mcp_client

# Click Actions
# 
# API Design Decision: We provide three separate click functions instead of one generic function:
# - click_link(): Matches links by visible text OR href, intuitive for "click the About link"
# - click_button(): Matches buttons by text OR ID, common pattern for form interactions  
# - click_element(): Requires precise CSS selectors, most flexible for any element
# This separation provides both convenience (text-based) and power (CSS selectors) while
# maintaining semantic clarity about what type of element is being targeted.

def click_link(identifier: str) -> bool:
    """
    Click a link by its text content or href.
    
    Args:
        identifier: Link text content or href attribute to match.
        
    Returns:
        True if the link was clicked successfully, False otherwise.
        
    Examples:
        >>> click_link("About Us")
        True
        >>> click_link("https://example.com/contact")
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        result = mcp_client.call_tool_structured("clickLink", {"identifier": identifier})
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to click link '{identifier}': {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from clickLink")
            return False
    except Exception as e:
        logger.error(f"Failed to click link '{identifier}': {e}")
        return False

def click_button(identifier: str) -> bool:
    """
    Click a button by its text content or ID.
    
    Args:
        identifier: Button text content or ID attribute to match.
        
    Returns:
        True if the button was clicked successfully, False otherwise.
        
    Examples:
        >>> click_button("Submit")
        True
        >>> click_button("login-btn")
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        result = mcp_client.call_tool_structured("clickButton", {"identifier": identifier})
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to click button '{identifier}': {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from clickButton")
            return False
    except Exception as e:
        logger.error(f"Failed to click button '{identifier}': {e}")
        return False

def click_element(selector: str) -> bool:
    """
    Click any element using a CSS selector.
    
    Args:
        selector: CSS selector to identify the element to click.
        
    Returns:
        True if the element was clicked successfully, False otherwise.
        
    Examples:
        >>> click_element("div.card:first-child")
        True
        >>> click_element("#menu-toggle")
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        result = mcp_client.call_tool_structured("clickElement", {"selector": selector})
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to click element '{selector}': {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from clickElement")
            return False
    except Exception as e:
        logger.error(f"Failed to click element '{selector}': {e}")
        return False

# Form Interaction
def type_text(selector: str, text: str, delay: Optional[int] = None, submit_after: bool = False) -> bool:
    """
    Type text into a form field identified by CSS selector.
    
    Args:
        selector: CSS selector to identify the input field.
        text: Text to type into the field.
        delay: Optional delay between keystrokes in milliseconds.
        submit_after: Whether to submit the form after typing.
        
    Returns:
        True if text was typed successfully, False otherwise.
        
    Examples:
        >>> type_text("input[name='email']", "user@example.com")
        True
        >>> type_text("#search-box", "python tutorials", delay=50, submit_after=True)
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        
        options = {}
        if delay is not None:
            options["delay"] = delay
        if submit_after:
            options["submitAfter"] = submit_after
            
        args = {"selector": selector, "text": text}
        if options:
            args["options"] = options
            
        result = mcp_client.call_tool_structured("typeText", args)
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to type text in '{selector}': {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from typeText")
            return False
    except Exception as e:
        logger.error(f"Failed to type text in '{selector}': {e}")
        return False

def submit_form(selector: str) -> bool:
    """
    Submit a form by its ID or containing element selector.
    
    Args:
        selector: CSS selector to identify the form element.
        
    Returns:
        True if the form was submitted successfully, False otherwise.
        
    Examples:
        >>> submit_form("#login-form")
        True
        >>> submit_form("form.contact-form")
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        result = mcp_client.call_tool_structured("submitForm", {"selector": selector})
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to submit form '{selector}': {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from submitForm")
            return False
    except Exception as e:
        logger.error(f"Failed to submit form '{selector}': {e}")
        return False

# Navigation
def navigate(url: str) -> bool:
    """
    Navigate to a specific URL.
    
    Args:
        url: The URL to navigate to.
        
    Returns:
        True if navigation was successful, False otherwise.
        
    Examples:
        >>> navigate("https://example.com")
        True
        >>> navigate("https://github.com/user/repo")
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        result = mcp_client.call_tool_structured("navigate", {"url": url})
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to navigate to '{url}': {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from navigate")
            return False
    except Exception as e:
        logger.error(f"Failed to navigate to '{url}': {e}")
        return False

def go_back() -> bool:
    """
    Navigate back in browser history.
    
    Returns:
        True if navigation was successful, False otherwise.
        
    Examples:
        >>> go_back()
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        result = mcp_client.call_tool_structured("goBack", {})
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to go back: {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from goBack")
            return False
    except Exception as e:
        logger.error(f"Failed to go back: {e}")
        return False

def go_forward() -> bool:
    """
    Navigate forward in browser history.
    
    Returns:
        True if navigation was successful, False otherwise.
        
    Examples:
        >>> go_forward()
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        result = mcp_client.call_tool_structured("goForward", {})
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to go forward: {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from goForward")
            return False
    except Exception as e:
        logger.error(f"Failed to go forward: {e}")
        return False

def reload(bypass_cache: bool = False) -> bool:
    """
    Reload the current page.
    
    Args:
        bypass_cache: Whether to bypass the browser cache when reloading.
        
    Returns:
        True if reload was successful, False otherwise.
        
    Examples:
        >>> reload()
        True
        >>> reload(bypass_cache=True)
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        
        args = {}
        if bypass_cache:
            args["options"] = {"bypassCache": bypass_cache}
            
        result = mcp_client.call_tool_structured("reload", args)
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to reload page: {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from reload")
            return False
    except Exception as e:
        logger.error(f"Failed to reload page: {e}")
        return False

# Scrolling
def scroll(target: Union[str, Dict[str, int]]) -> bool:
    """
    Scroll the page to a specific position or target.
    
    Args:
        target: Either "top", "bottom", or a dict with x,y coordinates like {"x": 0, "y": 500}.
        
    Returns:
        True if scrolling was successful, False otherwise.
        
    Examples:
        >>> scroll("top")
        True
        >>> scroll("bottom")
        True
        >>> scroll({"x": 0, "y": 500})
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        result = mcp_client.call_tool_structured("scroll", {"target": target})
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to scroll to {target}: {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from scroll")
            return False
    except Exception as e:
        logger.error(f"Failed to scroll to {target}: {e}")
        return False

# Wait and Timing
def wait_for_element(selector: str, timeout: Optional[int] = None, visible: bool = True) -> bool:
    """
    Wait for an element to appear in the DOM.
    
    Args:
        selector: CSS selector to identify the element to wait for.
        timeout: Maximum time to wait in milliseconds (default: 5000).
        visible: Whether to wait for the element to be visible (default: True).
        
    Returns:
        True if the element appeared within the timeout, False otherwise.
        
    Examples:
        >>> wait_for_element("#loading-spinner")
        True
        >>> wait_for_element(".modal", timeout=10000, visible=True)
        True
    """
    try:
        mcp_client = _get_chrome_mcp_client()
        
        args = {"selector": selector}
        options = {}
        if timeout is not None:
            options["timeout"] = timeout
        if not visible:  # Only add if different from default
            options["visible"] = visible
        if options:
            args["options"] = options
            
        result = mcp_client.call_tool_structured("waitForElement", args)
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success"
            if not success:
                logger.error(f"Failed to wait for element '{selector}': {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from waitForElement")
            return False
    except Exception as e:
        logger.error(f"Failed to wait for element '{selector}': {e}")
        return False