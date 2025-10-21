"""
Core library for interacting with the browser using Playwright with robust Chrome management.
Supports seamless integration with user's Chrome instance including saved passwords, cache, and history.
"""

from typing import Dict, Any, Optional, Union, List, Tuple
import logging
import os
import platform
import subprocess
import time
import json
import shutil
import tempfile
import socket
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext, Playwright

# Optional dependency - psutil for process monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.debug("psutil not available - process monitoring disabled")

logger = logging.getLogger(__name__)

# Global browser management
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None
_chrome_manager: Optional['ChromeManager'] = None

class ChromeManager:
    """Manages Chrome browser instances with user profile support and robust fallback."""
    
    def __init__(self):
        self.chrome_path: Optional[str] = None
        self.user_data_dir: Optional[str] = None
        self.debug_port: Optional[int] = None
        self.chrome_process: Optional[subprocess.Popen] = None
        self.session_start_time: Optional[float] = None
        
    def find_chrome_installation(self) -> Optional[str]:
        """Find Chrome installation path on macOS."""
        possible_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
            "/usr/local/bin/google-chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                logger.info(f"Found Chrome at: {path}")
                return path
        
        logger.warning("Chrome not found in standard locations")
        return None
    
    def get_user_chrome_profile_dir(self) -> Optional[str]:
        """Get user's default Chrome profile directory."""
        if platform.system() == "Darwin":  # macOS
            profile_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")
        elif platform.system() == "Windows":
            profile_dir = os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default")
        else:  # Linux
            profile_dir = os.path.expanduser("~/.config/google-chrome/Default")
        
        if os.path.isdir(profile_dir):
            logger.info(f"Found user Chrome profile at: {profile_dir}")
            return profile_dir
        
        logger.warning("User Chrome profile not found")
        return None
    
    def is_chrome_profile_locked(self, profile_dir: str) -> bool:
        """Check if Chrome profile is currently in use."""
        lock_file = os.path.join(os.path.dirname(profile_dir), "SingletonLock")
        if os.path.exists(lock_file):
            if PSUTIL_AVAILABLE:
                try:
                    # Try to check if the lock is active by looking for Chrome processes
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                            if proc.info['cmdline'] and any(profile_dir in arg for arg in proc.info['cmdline']):
                                logger.info("Chrome profile is locked by running instance")
                                return True
                except Exception as e:
                    logger.debug(f"Error checking Chrome processes: {e}")
            else:
                # Fallback: assume locked if lock file exists
                logger.debug("psutil not available, assuming profile is locked based on lock file")
                return True
        
        return False
    
    def create_temp_profile_copy(self, source_profile: str) -> Optional[str]:
        """Create a temporary copy of user's Chrome profile with debugging-friendly settings."""
        try:
            temp_dir = tempfile.mkdtemp(prefix="sisypho_chrome_")
            temp_profile = os.path.join(temp_dir, "Default")
            
            # Copy essential profile data (not everything to save time/space)
            essential_files = [
                "Cookies", "Login Data", "Web Data", "History", 
                "Bookmarks", "Preferences"
            ]
            
            os.makedirs(temp_profile, exist_ok=True)
            
            for file_name in essential_files:
                source_file = os.path.join(source_profile, file_name)
                if os.path.exists(source_file):
                    dest_file = os.path.join(temp_profile, file_name)
                    if os.path.isfile(source_file):
                        try:
                            shutil.copy2(source_file, dest_file)
                            logger.debug(f"Copied {file_name} to temp profile")
                        except Exception as e:
                            logger.debug(f"Could not copy {file_name}: {e}")
            
            # Create a debugging-friendly Preferences file
            self._create_debug_friendly_preferences(temp_profile)
            
            # Return the parent directory for --user-data-dir
            logger.info(f"Created temp profile copy at: {temp_dir}")
            return temp_profile
            
        except Exception as e:
            logger.error(f"Failed to create temp profile copy: {e}")
            return None
    
    def _create_debug_friendly_preferences(self, profile_path: str):
        """Create Chrome preferences that allow debugging."""
        try:
            import json
            
            preferences = {
                "profile": {
                    "default_content_setting_values": {
                        "notifications": 2  # Block notifications
                    },
                    "default_content_settings": {
                        "popups": 2  # Block popups
                    }
                },
                "browser": {
                    "check_default_browser": False,
                    "show_home_button": False
                },
                "distribution": {
                    "make_chrome_default_for_user": False,
                    "system_level": False
                },
                "first_run_tabs": [],
                "homepage_is_newtabpage": True,
                "session": {
                    "restore_on_startup": 1  # Open new tab page
                }
            }
            
            prefs_file = os.path.join(profile_path, "Preferences")
            with open(prefs_file, 'w') as f:
                json.dump(preferences, f, indent=2)
            
            logger.debug("Created debugging-friendly preferences")
            
        except Exception as e:
            logger.debug(f"Could not create preferences: {e}")
    
    def find_available_port(self, start_port: int = 9222) -> int:
        """Find an available port for Chrome debugging."""
        for port in range(start_port, start_port + 20):  # Try 20 ports
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    logger.debug(f"Found available port: {port}")
                    return port
                except OSError:
                    continue
        
        logger.warning(f"No available ports found starting from {start_port}")
        return start_port  # Fallback to requested port
    
    def is_port_open(self, port: int) -> bool:
        """Check if a port is currently in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(('localhost', port))
                return True
            except ConnectionRefusedError:
                return False
    
    def launch_chrome_with_debugging(self, chrome_path: str, profile_dir: str, port: int) -> bool:
        """Launch Chrome with debugging enabled."""
        try:
            # Use the parent directory of the profile for user-data-dir
            # For example: if profile_dir is "/path/to/Chrome/Default"
            # then user_data_dir should be "/path/to/Chrome"
            user_data_dir = os.path.dirname(profile_dir)
            
            chrome_args = [
                chrome_path,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={user_data_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--disable-features=VizDisplayCompositor",
                "--disable-hang-monitor",
                "--disable-prompt-on-repost",
                # Removed --disable-web-security as it conflicts with user-data-dir
                # Removed --no-sandbox and --disable-dev-shm-usage for better compatibility
            ]
            
            logger.info(f"Launching Chrome with debugging on port {port}")
            logger.info(f"User data directory: {user_data_dir}")
            logger.debug(f"Chrome command: {' '.join(chrome_args)}")
            
            # Launch Chrome process with better error capture
            self.chrome_process = subprocess.Popen(
                chrome_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                text=True
            )
            
            # Wait for Chrome to start up with better error reporting
            max_wait = 15  # Increased timeout to 15 seconds
            for i in range(max_wait * 10):  # Check every 100ms
                if self.is_port_open(port):
                    self.debug_port = port
                    self.session_start_time = time.time()
                    logger.info(f"Chrome successfully started on port {port}")
                    return True
                
                # Check if process has crashed
                if self.chrome_process.poll() is not None:
                    stdout, stderr = self.chrome_process.communicate()
                    logger.error(f"Chrome process exited early. Exit code: {self.chrome_process.returncode}")
                    logger.error(f"Chrome stdout: {stdout}")
                    logger.error(f"Chrome stderr: {stderr}")
                    return False
                
                time.sleep(0.1)
            
            # Chrome didn't start in time - get any error output
            if self.chrome_process.poll() is None:
                # Process is still running but port not available
                logger.error(f"Chrome process running but port {port} not available after {max_wait} seconds")
                logger.error("This might indicate Chrome is starting without debugging enabled")
                # Try to get any output
                try:
                    stdout, stderr = self.chrome_process.communicate(timeout=1)
                    if stdout:
                        logger.error(f"Chrome stdout: {stdout}")
                    if stderr:
                        logger.error(f"Chrome stderr: {stderr}")
                except subprocess.TimeoutExpired:
                    logger.error("Chrome process still running but unresponsive")
            else:
                stdout, stderr = self.chrome_process.communicate()
                logger.error(f"Chrome process exited. Exit code: {self.chrome_process.returncode}")
                if stdout:
                    logger.error(f"Chrome stdout: {stdout}")
                if stderr:
                    logger.error(f"Chrome stderr: {stderr}")
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            return False
    
    def close_existing_chrome_instances(self) -> bool:
        """Close existing Chrome instances to allow clean launch with debugging."""
        try:
            if PSUTIL_AVAILABLE:
                closed_any = False
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                            # Check if it's the main Chrome process (not helper processes)
                            if proc.info['cmdline'] and any('--type=' in arg for arg in proc.info['cmdline']):
                                continue  # Skip helper processes
                            
                            logger.info(f"Terminating Chrome process (PID: {proc.info['pid']})")
                            proc.terminate()
                            closed_any = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                if closed_any:
                    # Wait for processes to actually close
                    time.sleep(2)
                    logger.info("Chrome instances closed")
                return True
            else:
                # Fallback: try to close Chrome using AppleScript on macOS
                try:
                    import subprocess
                    applescript = '''
                    tell application "Google Chrome"
                        quit
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', applescript], 
                                 capture_output=True, timeout=5)
                    time.sleep(2)
                    logger.info("Chrome closed using AppleScript")
                    return True
                except Exception as e:
                    logger.debug(f"Could not close Chrome with AppleScript: {e}")
                    return False
        except Exception as e:
            logger.warning(f"Error closing Chrome instances: {e}")
            return False

    def check_existing_chrome_debug_instances(self) -> Optional[int]:
        """Check if Chrome is already running with debugging enabled."""
        # Try common debugging ports
        common_ports = [9222, 9223, 9224, 9225]
        
        for port in common_ports:
            if self.is_port_open(port):
                try:
                    # Try to connect to see if it's actually Chrome debugging port
                    import urllib.request
                    import json
                    
                    url = f"http://localhost:{port}/json/version"
                    response = urllib.request.urlopen(url, timeout=2)
                    data = json.loads(response.read().decode())
                    
                    if 'Browser' in data and 'chrome' in data['Browser'].lower():
                        logger.info(f"Found existing Chrome debugging instance on port {port}")
                        return port
                        
                except Exception as e:
                    logger.debug(f"Port {port} open but not Chrome debugging: {e}")
                    continue
        
        return None

    def get_chrome_instance(self) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """Get or create a Chrome instance with debugging enabled.
        
        Returns:
            Tuple of (chrome_path, profile_dir, debug_port) or (None, None, None) if failed
        """
        # Find Chrome installation
        if not self.chrome_path:
            self.chrome_path = self.find_chrome_installation()
            if not self.chrome_path:
                logger.error("Chrome installation not found")
                return None, None, None
        
        # Get user profile directory
        if not self.user_data_dir:
            user_profile = self.get_user_chrome_profile_dir()
            if user_profile:
                # Check if Chrome is already running with debugging
                existing_port = self.check_existing_chrome_debug_instances()
                if existing_port:
                    logger.info(f"Using existing Chrome debug instance on port {existing_port}")
                    self.debug_port = existing_port
                    self.user_data_dir = user_profile
                    self.session_start_time = time.time()
                    return self.chrome_path, self.user_data_dir, existing_port
                
                # Always create a temp copy with debugging-friendly settings
                # This avoids conflicts with user's existing Chrome settings
                logger.info("Creating temporary profile copy with user data for debugging")
                self.user_data_dir = self.create_temp_profile_copy(user_profile)
            else:
                logger.warning("User Chrome profile not found")
        
        # Use temp directory if no profile available
        if not self.user_data_dir:
            logger.info("Using temporary profile directory")
            temp_dir = tempfile.mkdtemp(prefix="sisypho_chrome_")
            self.user_data_dir = os.path.join(temp_dir, "Default")
            os.makedirs(self.user_data_dir, exist_ok=True)
        
        # Check if we already have a running instance
        if self.debug_port and self.is_port_open(self.debug_port):
            # Check if instance is too old (restart after 30 minutes)
            if self.session_start_time and (time.time() - self.session_start_time) > 1800:
                logger.info("Chrome instance is old, restarting")
                self.cleanup_chrome_instance()
            else:
                logger.info(f"Reusing existing Chrome instance on port {self.debug_port}")
                return self.chrome_path, self.user_data_dir, self.debug_port
        
        # Launch new Chrome instance
        port = self.find_available_port()
        if self.launch_chrome_with_debugging(self.chrome_path, self.user_data_dir, port):
            return self.chrome_path, self.user_data_dir, port
        
        return None, None, None
    
    def cleanup_chrome_instance(self):
        """Clean up Chrome instance and temporary files."""
        if self.chrome_process:
            try:
                self.chrome_process.terminate()
                self.chrome_process.wait(timeout=5)
                logger.info("Chrome process terminated")
            except subprocess.TimeoutExpired:
                logger.warning("Chrome process didn't terminate gracefully, killing")
                self.chrome_process.kill()
            except Exception as e:
                logger.error(f"Error terminating Chrome process: {e}")
            
            self.chrome_process = None
        
        # Clean up temporary profile if it was created
        if self.user_data_dir and "sisypho_chrome_" in self.user_data_dir:
            try:
                temp_root = os.path.dirname(self.user_data_dir)
                if os.path.exists(temp_root):
                    shutil.rmtree(temp_root)
                    logger.info("Cleaned up temporary profile directory")
            except Exception as e:
                logger.error(f"Error cleaning up temp profile: {e}")
        
        self.debug_port = None
        self.session_start_time = None
        self.user_data_dir = None

def _get_browser_client():
    """Get or create browser client with robust Chrome management and fallback strategy."""
    global _playwright, _browser, _context, _page, _chrome_manager
    
    if _page and not _page.is_closed():
        return _page  # Already initialized and working
    
    # Initialize Playwright
    if not _playwright:
        _playwright = sync_playwright().start()
    
    # Initialize Chrome manager
    if not _chrome_manager:
        _chrome_manager = ChromeManager()
    
    # Try to get Chrome instance with user profile
    chrome_path, profile_dir, debug_port = _chrome_manager.get_chrome_instance()
    
    if chrome_path and debug_port:
        try:
            # Connect to Chrome instance via CDP
            logger.info(f"Connecting to Chrome via CDP on port {debug_port}")
            _browser = _playwright.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
            
            # Get existing context or create new one
            contexts = _browser.contexts
            if contexts:
                _context = contexts[0]
            else:
                _context = _browser.new_context()
            
            # Get existing page or create new one
            pages = _context.pages
            if pages:
                _page = pages[0]
            else:
                _page = _context.new_page()
            
            logger.info("Successfully connected to Chrome with user profile")
            return _page
            
        except Exception as e:
            logger.error(f"Failed to connect to Chrome via CDP: {e}")
            logger.info("Falling back to Playwright Chrome launch...")
    
    # Fallback 1: Try Playwright's Chrome launch with user profile
    if chrome_path and profile_dir:
        try:
            logger.info("Launching Chrome via Playwright with user profile...")
            _browser = _playwright.chromium.launch(
                executable_path=chrome_path,
                headless=False,
                args=[
                    f'--user-data-dir={os.path.dirname(profile_dir)}',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding'
                ]
            )
            _context = _browser.new_context()
            _page = _context.new_page()
            logger.info("Successfully launched Chrome via Playwright with user profile")
            return _page
            
        except Exception as e:
            logger.error(f"Failed to launch Chrome via Playwright with user profile: {e}")
            logger.info("Falling back to standard Chrome launch...")
    
    # Fallback 2: Try Playwright's standard Chrome launch
    if chrome_path:
        try:
            logger.info("Launching Chrome via Playwright (standard)...")
            _browser = _playwright.chromium.launch(
                executable_path=chrome_path,
                headless=False,
                args=[
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            _context = _browser.new_context()
            _page = _context.new_page()
            logger.info("Successfully launched Chrome via Playwright (standard)")
            return _page
            
        except Exception as e:
            logger.error(f"Failed to launch Chrome via Playwright (standard): {e}")
            logger.info("Falling back to Playwright's bundled Chromium...")
    
    # Fallback 3: Use Playwright's bundled Chromium
    try:
        logger.info("Launching Playwright's bundled Chromium...")
        _browser = _playwright.chromium.launch(
            headless=False,
            args=[
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        _context = _browser.new_context()
        _page = _context.new_page()
        logger.info("Successfully launched Playwright's bundled Chromium")
        return _page
        
    except Exception as e:
        logger.error(f"All browser launch methods failed: {e}")
        raise RuntimeError("Unable to launch any browser instance")
    
    return _page

def _cleanup_browser():
    """Clean up browser resources including Chrome instances."""
    global _playwright, _browser, _context, _page, _chrome_manager
    
    try:
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
        if _chrome_manager:
            _chrome_manager.cleanup_chrome_instance()
    except Exception as e:
        logger.debug(f"Error during browser cleanup: {e}")
        pass  # Ignore cleanup errors
    
    _playwright = None
    _browser = None
    _context = None
    _page = None
    _chrome_manager = None

# Register cleanup on module exit
import atexit
atexit.register(_cleanup_browser)

# Public API functions for skill management
def ensure_fresh_browser_session() -> bool:
    """Ensure a fresh browser session for new skill execution.
    
    This function should be called at the start of each skill to ensure
    a clean, reliable browser state.
    
    Returns:
        True if session is ready, False if setup failed
    """
    try:
        # Check if we should restart based on health metrics
        if should_restart_browser_session():
            logger.info("Browser session needs restart based on health metrics")
            _cleanup_browser()
        
        # Ensure we have a working browser instance
        page = _get_browser_client()
        if not page or page.is_closed():
            logger.error("Failed to get working browser instance")
            return False
        
        # Reset session state for clean start
        reset_browser_session()
        
        logger.info("Fresh browser session ready")
        return True
        
    except Exception as e:
        logger.error(f"Failed to ensure fresh browser session: {e}")
        return False

def get_browser_status() -> Dict[str, Any]:
    """Get comprehensive browser status for monitoring and debugging.
    
    Returns:
        Dictionary with browser status information
    """
    try:
        health_info = get_browser_health_info()
        
        # Add Chrome manager specific info
        if _chrome_manager:
            health_info.update({
                "chrome_path": _chrome_manager.chrome_path,
                "chrome_process_running": _chrome_manager.chrome_process is not None,
                "chrome_process_pid": _chrome_manager.chrome_process.pid if _chrome_manager.chrome_process else None
            })
        
        # Add Playwright info
        health_info.update({
            "playwright_active": _playwright is not None,
            "browser_object_active": _browser is not None,
            "context_active": _context is not None
        })
        
        return health_info
        
    except Exception as e:
        logger.error(f"Error getting browser status: {e}")
        return {"error": str(e)}

def _print_dom_on_failure(action_name: str, target: str = ""):
    """
    Print the current DOM structure when a browser action fails.
    
    Args:
        action_name: Name of the action that failed (e.g., "click", "type")
        target: The target selector/identifier that failed
    """
    try:
        page = _get_browser_client()
        logger.error(f"=== DOM DEBUG: {action_name} failed for '{target}' ===")
        
        # Get current URL and title for context
        current_url = page.url
        page_title = page.title()
        logger.error(f"URL: {current_url}")
        logger.error(f"Title: {page_title}")
        
        # Get the full DOM content
        # dom_content = page.content()
        # logger.error("=== FULL DOM CONTENT ===")
        # logger.error(dom_content)
        # logger.error("=== END DOM DEBUG ===")
        
    except Exception as e:
        logger.error(f"Failed to print DOM debug info: {e}")
        # Fallback: try to get basic page info
        try:
            page = _get_browser_client()
            logger.error(f"Fallback info - URL: {page.url}, Title: {page.title()}")
        except:
            logger.error("Could not retrieve any DOM information")

def _fuzzy_click(selector: str) -> bool:
    """
    Click using fuzzy matching: start from child selector and work upward until unique match found.
    
    Args:
        selector: Full CSS selector path
        
    Returns:
        True if clicked successfully, False otherwise
    """
    try:
        page = _get_browser_client()
        
        # Split the selector by ' > ' to get the hierarchy
        parts = selector.split(' > ')
        if not parts:
            return False
        
        # Start from the most specific (rightmost) part and work backward
        for i in range(len(parts)):
            # Build selector from current position to end
            current_selector = ' > '.join(parts[i:])
            
            try:
                # Count how many elements match this selector
                elements = page.locator(current_selector).all()
                element_count = len(elements)
                
                logger.info(f"Selector '{current_selector}' matches {element_count} elements")
                
                if element_count == 1:
                    # Found unique match! Click it
                    logger.info(f"Found unique match with: {current_selector}")
                    page.click(current_selector, timeout=3000)
                    return True
                elif element_count == 0:
                    # No matches, continue to less specific selector
                    continue
                else:
                    # Multiple matches, try less specific selector
                    continue
                    
            except Exception as e:
                logger.debug(f"Error with selector '{current_selector}': {e}")
                continue
        
        # If no unique match found, try the most specific selector anyway
        logger.info("No unique match found, trying most specific selector")
        try:
            most_specific = parts[-1]
            page.click(most_specific, timeout=3000)
            return True
        except:
            pass
            
        logger.error(f"Fuzzy click failed for all selector combinations")
        return False
        
    except Exception as e:
        logger.error(f"Fuzzy click failed: {e}")
        return False

# Click Actions
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
        page = _get_browser_client()
        
        # Try to find link by text content first
        try:
            page.click(f'a:has-text("{identifier}")', timeout=5000)
            return True
        except:
            # Try to find by href attribute
            page.click(f'a[href*="{identifier}"]', timeout=5000)
            return True
            
    except Exception as e:
        logger.error(f"Failed to click link '{identifier}': {e}")
        _print_dom_on_failure("click_link", identifier)
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
        page = _get_browser_client()
        
        # Try to find button by text content first
        try:
            page.click(f'button:has-text("{identifier}")', timeout=5000)
            return True
        except:
            # Try to find by ID
            page.click(f'#{identifier}', timeout=5000)
            return True
            
    except Exception as e:
        logger.error(f"Failed to click button '{identifier}': {e}")
        _print_dom_on_failure("click_button", identifier)
        return False

def click_element(selector: str, wait_for_change: bool = True, change_selector: Optional[str] = None, timeout: int = 5000, force_fresh_session: bool = False) -> bool:
    """
    Click any element using a CSS selector with fuzzy matching fallback and content change detection.
    
    Args:
        selector: CSS selector to identify the element to click.
        wait_for_change: Whether to wait for content changes after clicking (default: True).
        change_selector: Specific selector to monitor for content changes. If None, monitors the whole page body.
        timeout: Maximum time to wait for changes in milliseconds (default: 5000).
        force_fresh_session: Whether to restart browser session if needed (default: False).
        
    Returns:
        True if the element was clicked successfully, False otherwise.
        
    Examples:
        >>> click_element("div.card:first-child")
        True
        >>> click_element("#calendar-day", change_selector=".events-container")
        True
        >>> click_element("#menu-toggle", wait_for_change=False)
        True
        >>> click_element("#refresh-btn", force_fresh_session=True)
        True
    """
    try:
        # Check if we should restart browser session
        if force_fresh_session or should_restart_browser_session():
            logger.info("Restarting browser session for fresh state")
            _cleanup_browser()
        
        page = _get_browser_client()
        
        # First check if the element exists
        try:
            element_exists = page.locator(selector).count() > 0
            if not element_exists:
                logger.warning(f"Element not found: {selector}")
                return False
        except Exception as e:
            logger.debug(f"Error checking element existence: {e}")
        
        # Check if element is already selected/active (for calendar scenarios)
        is_already_active = False
        try:
            # Common patterns for active/selected states
            active_element = page.locator(f"{selector}.active, {selector}.selected, {selector}[aria-selected='true']")
            is_already_active = active_element.count() > 0
            if is_already_active:
                logger.info(f"Element {selector} is already active/selected")
        except Exception as e:
            logger.debug(f"Error checking active state: {e}")
        
        # Capture initial state if waiting for changes
        initial_content_hash = None
        if wait_for_change:
            try:
                # Use entire page HTML hash for reliable change detection
                page_html = page.content()
                initial_content_hash = hash(page_html)
                logger.debug(f"Captured initial page content hash: {initial_content_hash}")
            except Exception as e:
                logger.warning(f"Could not capture initial content state: {e}")
                # Continue without content monitoring
                wait_for_change = False
        
        # Perform the click action
        click_success = False
        
        # Try exact selector first
        try:
            page.click(selector, timeout=3000)
            click_success = True
            logger.info(f"Successfully clicked: {selector}")
        except Exception as click_error:
            logger.info(f"Exact selector failed: {selector}, trying fuzzy matching... ({click_error})")
            # Use fuzzy matching as fallback
            click_success = _fuzzy_click(selector)
        
        if not click_success:
            logger.error(f"All click attempts failed for: {selector}")
            return False
        
        # Wait for DOM stability after click
        if wait_for_change:
            return _wait_for_dom_stability(page, timeout, is_already_active)
        else:
            return True
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to click element '{selector}': {e}")
        _print_dom_on_failure("click_element", selector)
        return False


def reset_browser_session() -> bool:
    """Reset browser session for clean state between skill runs."""
    try:
        page = _get_browser_client()
        
        # Clear browsing data
        try:
            # Clear cookies, localStorage, sessionStorage
            page.evaluate("""
                // Clear localStorage
                if (typeof localStorage !== 'undefined') {
                    localStorage.clear();
                }
                
                // Clear sessionStorage
                if (typeof sessionStorage !== 'undefined') {
                    sessionStorage.clear();
                }
                
                // Clear any cached data
                if ('caches' in window) {
                    caches.keys().then(names => {
                        names.forEach(name => {
                            caches.delete(name);
                        });
                    });
                }
            """)
            
            logger.info("Browser session reset completed")
            return True
            
        except Exception as e:
            logger.warning(f"Partial session reset due to error: {e}")
            return True  # Don't fail completely on reset issues
            
    except Exception as e:
        logger.error(f"Failed to reset browser session: {e}")
        return False

def get_browser_health_info() -> Dict[str, Any]:
    """Get browser instance health information for monitoring."""
    global _chrome_manager, _page, _browser
    
    health_info = {
        "browser_active": False,
        "page_responsive": False,
        "chrome_manager_active": False,
        "session_age_seconds": None,
        "debug_port": None,
        "profile_path": None,
        "memory_usage_mb": None
    }
    
    try:
        # Check if page is active and responsive
        if _page and not _page.is_closed():
            health_info["browser_active"] = True
            try:
                # Quick responsiveness test
                _page.evaluate("document.title")
                health_info["page_responsive"] = True
            except:
                health_info["page_responsive"] = False
        
        # Check Chrome manager status
        if _chrome_manager:
            health_info["chrome_manager_active"] = True
            health_info["debug_port"] = _chrome_manager.debug_port
            health_info["profile_path"] = _chrome_manager.user_data_dir
            
            if _chrome_manager.session_start_time:
                health_info["session_age_seconds"] = int(time.time() - _chrome_manager.session_start_time)
            
            # Get memory usage if Chrome process is available
            if _chrome_manager.chrome_process and PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process(_chrome_manager.chrome_process.pid)
                    health_info["memory_usage_mb"] = round(process.memory_info().rss / 1024 / 1024, 1)
                except Exception as e:
                    logger.debug(f"Error getting memory usage: {e}")
            elif _chrome_manager.chrome_process and not PSUTIL_AVAILABLE:
                health_info["memory_usage_mb"] = "unavailable (psutil not installed)"
        
    except Exception as e:
        logger.debug(f"Error getting browser health info: {e}")
    
    return health_info

def should_restart_browser_session() -> bool:
    """Determine if browser session should be restarted based on health metrics."""
    health = get_browser_health_info()
    
    # Restart if session is older than 30 minutes
    if health["session_age_seconds"] and health["session_age_seconds"] > 1800:
        logger.info("Browser session is old, should restart")
        return True
    
    # Restart if memory usage is too high (>1GB) - only if psutil is available
    if PSUTIL_AVAILABLE and isinstance(health["memory_usage_mb"], (int, float)) and health["memory_usage_mb"] > 1024:
        logger.info(f"High memory usage ({health['memory_usage_mb']}MB), should restart")
        return True
    
    # Restart if browser is not responsive
    if health["browser_active"] and not health["page_responsive"]:
        logger.info("Browser is not responsive, should restart")
        return True
    
    return False

def _wait_for_content_change(page, initial_content_hash: int, timeout: int, is_already_active: bool = False) -> bool:
    """
    Wait for content to change after a click action using page hash comparison.
    
    Args:
        page: Playwright page object
        initial_content_hash: Hash of initial page content
        timeout: Maximum time to wait in milliseconds
        is_already_active: Whether the clicked element was already active
        
    Returns:
        True if content changed or timeout occurred, False on error
    """
    try:
        import time
        start_time = time.time() * 1000  # Convert to milliseconds
        check_interval = 100  # Check every 100ms
        
        logger.info(f"Waiting for page content change (already_active: {is_already_active})")
        logger.debug(f"Initial page hash: {initial_content_hash}")
        
        # If element was already active, do a quick check and shorter wait
        if is_already_active:
            # Quick network wait for any pending requests
            try:
                page.wait_for_load_state("networkidle", timeout=500)
            except:
                pass
            
            # Check once for any changes, then proceed quickly
            try:
                page.wait_for_timeout(200)  # Brief pause
                current_hash = hash(page.content())
                
                if current_hash != initial_content_hash:
                    logger.info(f"Content change detected for already-active element")
                    return True
                else:
                    logger.info(f"No content change for already-active element - proceeding anyway")
                    return True
            except:
                logger.info(f"Could not verify content for already-active element - proceeding anyway")
                return True
        
        # Normal content change monitoring for non-active elements
        while (time.time() * 1000) - start_time < timeout:
            try:
                # Check if page content has changed
                current_hash = hash(page.content())
                
                if current_hash != initial_content_hash:
                    logger.info(f"Page content change detected after {int((time.time() * 1000) - start_time)}ms")
                    return True
                
                # Wait before next check
                page.wait_for_timeout(check_interval)
                
            except Exception as e:
                logger.debug(f"Error during content change check: {e}")
                # Continue checking
                page.wait_for_timeout(check_interval)
        
        # Timeout reached - this is often acceptable in web scraping
        logger.info(f"Content change timeout reached ({timeout}ms) - proceeding anyway")
        return True
        
    except Exception as e:
        logger.error(f"Error waiting for content change: {e}")
        return True  # Return True to not block execution

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
        page = _get_browser_client()
        
        # Clear the field first, then type
        page.fill(selector, "")
        
        if delay:
            page.type(selector, text, delay=delay)
        else:
            page.fill(selector, text)
        
        if submit_after:
            # Try to submit the form containing this element
            page.keyboard.press("Enter")
            
        return True
    except Exception as e:
        logger.error(f"Failed to type text in '{selector}': {e}")
        _print_dom_on_failure("type_text", selector)
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
        page = _get_browser_client()
        # Find the form and submit it
        page.locator(selector).press("Enter")
        return True
    except Exception as e:
        logger.error(f"Failed to submit form '{selector}': {e}")
        _print_dom_on_failure("submit_form", selector)
        return False

# Navigation
def navigate(url: str) -> bool:
    """
    Navigate to a specific URL and wait for page to fully load including AJAX content.
    
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
        page = _get_browser_client()
        logger.info(f"Navigating to: {url}")
        
        # Navigate to the URL
        page.goto(url, timeout=30000)  # 30 second timeout
        
        # Wait for page to fully load
        page.wait_for_load_state("domcontentloaded")
        logger.debug("DOM content loaded")
        
        # Wait for network activity to settle (important for AJAX-heavy sites)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
            logger.debug("Network idle state reached")
        except:
            logger.debug("Network idle timeout - page may still be loading AJAX content")
        
        # Additional wait for DOM stability (similar to click_element)
        try:
            _wait_for_dom_stability(page, timeout=3000, is_already_active=False)
            logger.info("Page navigation completed and DOM stabilized")
        except:
            logger.debug("DOM stability check failed - proceeding anyway")
        
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to '{url}': {e}")
        _print_dom_on_failure("navigate", url)
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
        page = _get_browser_client()
        page.go_back()
        return True
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
        page = _get_browser_client()
        page.go_forward()
        return True
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
        page = _get_browser_client()
        page.reload(wait_until="load")
        return True
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
        page = _get_browser_client()
        
        if target == "top":
            page.evaluate("window.scrollTo(0, 0)")
        elif target == "bottom":
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif isinstance(target, dict) and "x" in target and "y" in target:
            page.evaluate(f"window.scrollTo({target['x']}, {target['y']})")
        else:
            logger.error(f"Invalid scroll target: {target}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Failed to scroll to {target}: {e}")
        return False

# Content Extraction
def getContent(
    rootNode: str = "/",
    removeTags: bool = True,
    fuzzy: bool = False,
    maxResults: int = 1,
) -> List[str]:
    """
    Extract content from the current page.
    
    Args:
        rootNode: XPath expression or CSS selector for the root node to extract content from. 
                 Default "/" returns entire page content.
                 Supports both XPath (starting with "/" or "//") and CSS selectors.
        removeTags: If True, removes HTML tags and returns plain text.
                   If False, returns raw HTML content.
        fuzzy: If True, uses fuzzy matching to find the closest element when exact match fails.
        maxResults: Number of results to return.
                    - 1 returns the first match
                    - N returns up to N matches
                    - -1 returns all matches
    Returns:
        A list of strings with up to maxResults items (or all if maxResults == -1). Returns an empty list if nothing is found.
        
    Examples:
        >>> getContent()  # Get entire page as plain text
        "Welcome to our site..."
        >>> getContent(rootNode="//main", removeTags=True)  # Get main content only
        "Article content here..."
        >>> getContent(rootNode=".content", removeTags=False)  # Get HTML using CSS selector
        "<div class='content'>Article content...</div>"
        >>> getContent(rootNode="//div[@class='content']", fuzzy=True)  # Fuzzy XPath matching
        "Article content..."
        >>> getContent(rootNode=".item", maxResults=-1)  # Get content for all matched elements
        ["Item 1", "Item 2", "Item 3"]
    """
    try:
        page = _get_browser_client()
        
        if rootNode == "/":
            # Get entire page content
            if removeTags:
                # Extract just the text content from body
                content = page.evaluate("document.body.innerText")
            else:
                # Get full HTML
                content = page.content()
            content = [content] if content else []
        else:
            # Determine if it's XPath or CSS selector
            is_xpath = rootNode.startswith("/") or rootNode.startswith("//")
            
            if is_xpath:
                content = _get_content_by_xpath(page, rootNode, removeTags, fuzzy, maxResults)
            else:
                content = _get_content_by_css(page, rootNode, removeTags, fuzzy, maxResults)
        
        # Clean up the content
        if isinstance(content, list):
            import re
            cleaned_list: List[str] = []
            for item in content:
                if not isinstance(item, str):
                    continue
                cleaned = re.sub(r'\n\s*\n', '\n\n', item)
                cleaned = re.sub(r'[ \t]+', ' ', cleaned)
                cleaned = cleaned.strip()
                cleaned_list.append(cleaned)
            # Enforce maxResults limit if needed (except -1)
            if maxResults == -1 or maxResults >= len(cleaned_list):
                return cleaned_list
            return cleaned_list[:maxResults]
        else:
            # Fallback for unexpected types
            return []
            
    except Exception as e:
        logger.error(f"Failed to get content for rootNode '{rootNode}': {e}")
        _print_dom_on_failure("getContent", rootNode)
        return []

def _get_content_by_xpath(
    page,
    xpath: str,
    removeTags: bool,
    fuzzy: bool,
    maxResults: int,
) -> List[str]:
    """Extract content using XPath with optional fuzzy matching."""
    try:
        # Always collect snapshot of nodes and then subset to maxResults
        if removeTags:
            content = page.evaluate(
                """
                (xpath) => {
                    const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    const values = [];
                    for (let i = 0; i < result.snapshotLength; i++) {
                        const node = result.snapshotItem(i);
                        if (node) values.push(node.innerText);
                    }
                    return values;
                }
                """,
                xpath,
            )
        else:
            content = page.evaluate(
                """
                (xpath) => {
                    const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    const values = [];
                    for (let i = 0; i < result.snapshotLength; i++) {
                        const node = result.snapshotItem(i);
                        if (node) values.push(node.innerHTML);
                    }
                    return values;
                }
                """,
                xpath,
            )

        if not isinstance(content, list):
            content = []

        # Enforce maxResults early
        if maxResults != -1 and maxResults >= 0:
            content = content[:maxResults]
        
        # If we got content and fuzzy is disabled, return it
        if not fuzzy:
            return content
            
        # If fuzzy is enabled and no content found, try fuzzy matching
        if fuzzy:
            if len(content) == 0:
                return _fuzzy_xpath_content(page, xpath, removeTags, maxResults)
            
        return content
        
    except Exception as e:
        logger.error(f"XPath evaluation failed for '{xpath}': {e}")
        if fuzzy:
            return _fuzzy_xpath_content(page, xpath, removeTags, maxResults)
        return []

def _get_content_by_css(
    page,
    selector: str,
    removeTags: bool,
    fuzzy: bool,
    maxResults: int,
) -> List[str]:
    """Extract content using CSS selector with optional fuzzy matching."""
    try:
        # Try exact CSS selector first
        elements = page.locator(selector).all()
        if elements:
            results: List[str] = []
            limit = len(elements) if maxResults == -1 else max(0, min(maxResults, len(elements)))
            subset = elements if maxResults == -1 else elements[:limit]
            for el in subset:
                results.append(el.inner_text() if removeTags else el.inner_html())
            return results
        
        # If fuzzy is enabled and no elements found, try fuzzy matching
        if fuzzy:
            return _fuzzy_css_content(page, selector, removeTags, maxResults)
            
        return []
        
    except Exception as e:
        logger.error(f"CSS selector evaluation failed for '{selector}': {e}")
        if fuzzy:
            return _fuzzy_css_content(page, selector, removeTags, maxResults)
        return []

def _fuzzy_xpath_content(page, xpath: str, removeTags: bool, maxResults: int) -> List[str]:
    """Find content using fuzzy XPath matching."""
    try:
        # Split XPath by '/' to get parts
        parts = xpath.split('/')
        if len(parts) <= 1:
            return []
        
        # Strategy 1: Try progressively less specific XPath expressions (removing from beginning)
        for i in range(1, len(parts)):
            # Build XPath from current position to end
            current_xpath = '/' + '/'.join(parts[i:])
            
            try:
                if removeTags:
                    content = page.evaluate(
                        """
                        (xpath) => {
                            const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            const values = [];
                            for (let i = 0; i < result.snapshotLength; i++) {
                                const node = result.snapshotItem(i);
                                if (node) values.push(node.innerText);
                            }
                            return values;
                        }
                        """,
                        current_xpath,
                    )
                else:
                    content = page.evaluate(
                        """
                        (xpath) => {
                            const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            const values = [];
                            for (let i = 0; i < result.snapshotLength; i++) {
                                const node = result.snapshotItem(i);
                                if (node) values.push(node.innerHTML);
                            }
                            return values;
                        }
                        """,
                        current_xpath,
                    )
                if content and len(content) > 0:
                    if maxResults != -1 and maxResults >= 0:
                        content = content[:maxResults]
                    logger.info(f"Found content with fuzzy XPath (strategy 1): {current_xpath}")
                    return content
                    
            except Exception as e:
                logger.debug(f"Fuzzy XPath '{current_xpath}' failed: {e}")
                continue
        
        # Strategy 2: Try partial matches within attributes and tag names
        for i in range(1, len(parts)):
            current_part = parts[i]
            if not current_part:
                continue
                
            # Try different variations of the current part
            variations = _generate_xpath_variations(current_part)
            
            for variation in variations:
                # Build XPath with the variation
                modified_parts = parts.copy()
                modified_parts[i] = variation
                current_xpath = '/' + '/'.join(modified_parts)
                
                try:
                    if removeTags:
                        content = page.evaluate(
                            """
                            (xpath) => {
                                const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                const values = [];
                                for (let i = 0; i < result.snapshotLength; i++) {
                                    const node = result.snapshotItem(i);
                                    if (node) values.push(node.innerText);
                                }
                                return values;
                            }
                            """,
                            current_xpath,
                        )
                    else:
                        content = page.evaluate(
                            """
                            (xpath) => {
                                const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                const values = [];
                                for (let i = 0; i < result.snapshotLength; i++) {
                                    const node = result.snapshotItem(i);
                                    if (node) values.push(node.innerHTML);
                                }
                                return values;
                            }
                            """,
                            current_xpath,
                        )
                    if content and len(content) > 0:
                        if maxResults != -1 and maxResults >= 0:
                            content = content[:maxResults]
                        logger.info(f"Found content with fuzzy XPath (strategy 2): {current_xpath}")
                        return content
                        
                except Exception as e:
                    logger.debug(f"Fuzzy XPath variation '{current_xpath}' failed: {e}")
                    continue
        
        # Strategy 3: Try the most specific part with variations
        most_specific = parts[-1]
        variations = _generate_xpath_variations(most_specific)
        
        for variation in variations:
            try:
                if removeTags:
                    content = page.evaluate(
                        """
                        (xpath) => {
                            const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            const values = [];
                            for (let i = 0; i < result.snapshotLength; i++) {
                                const node = result.snapshotItem(i);
                                if (node) values.push(node.innerText);
                            }
                            return values;
                        }
                        """,
                        f"//{variation}",
                    )
                else:
                    content = page.evaluate(
                        """
                        (xpath) => {
                            const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            const values = [];
                            for (let i = 0; i < result.snapshotLength; i++) {
                                const node = result.snapshotItem(i);
                                if (node) values.push(node.innerHTML);
                            }
                            return values;
                        }
                        """,
                        f"//{variation}",
                    )
                
                if content and len(content) > 0:
                    if maxResults != -1 and maxResults >= 0:
                        content = content[:maxResults]
                    logger.info(f"Found content with fuzzy XPath (strategy 3): //{variation}")
                    return content
                    
            except Exception as e:
                logger.debug(f"Most specific XPath variation '//{variation}' failed: {e}")
        
        return []
        
    except Exception as e:
        logger.error(f"Fuzzy XPath matching failed for '{xpath}': {e}")
        return []

def _generate_xpath_variations(xpath_part: str) -> list:
    """Generate variations of an XPath part for fuzzy matching."""
    variations = []
    
    # If it's just a tag name without attributes, try common variations
    if '[' not in xpath_part:
        variations.append(xpath_part)
        # Try with wildcard
        variations.append(f"{xpath_part}[*]")
        return variations
    
    # Parse the XPath part: tag[@attr='value']
    import re
    
    # Extract tag name and attributes
    tag_match = re.match(r'^([a-zA-Z][a-zA-Z0-9]*)\[?(.*)\]?$', xpath_part)
    if not tag_match:
        variations.append(xpath_part)
        return variations
    
    tag_name = tag_match.group(1)
    attr_part = tag_match.group(2) if tag_match.group(2) else ""
    
    # Add the original
    variations.append(xpath_part)
    
    # Try without attributes
    variations.append(tag_name)
    
    # Try with wildcard attribute
    variations.append(f"{tag_name}[*]")
    
    # If there are attributes, try partial attribute matches
    if attr_part:
        # Extract individual attribute conditions
        attr_conditions = re.findall(r'@([a-zA-Z][a-zA-Z0-9-]*)\s*=\s*[\'"]([^\'"]*)[\'"]', attr_part)
        
        for attr_name, attr_value in attr_conditions:
            # Try partial attribute value matches
            if len(attr_value) > 3:
                # Try first 3 characters
                variations.append(f"{tag_name}[@{attr_name}='{attr_value[:3]}*']")
                # Try first half
                half_len = len(attr_value) // 2
                variations.append(f"{tag_name}[@{attr_name}='{attr_value[:half_len]}*']")
                # Try contains
                variations.append(f"{tag_name}[contains(@{attr_name}, '{attr_value[:3]}')]")
            
            # Try just the attribute name without value
            variations.append(f"{tag_name}[@{attr_name}]")
            
            # Try partial attribute name
            if len(attr_name) > 3:
                partial_attr = attr_name[:3]
                variations.append(f"{tag_name}[@{partial_attr}*]")
    
    # Try common attribute patterns
    variations.append(f"{tag_name}[@class]")
    variations.append(f"{tag_name}[@id]")
    variations.append(f"{tag_name}[@name]")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        if var not in seen:
            seen.add(var)
            unique_variations.append(var)
    
    return unique_variations

def _fuzzy_css_content(page, selector: str, removeTags: bool, maxResults: int) -> List[str]:
    """Find content using fuzzy CSS selector matching."""
    try:
        # Split selector by spaces, dots, and hashes to get parts
        import re
        parts = re.split(r'[\s.#]', selector)
        parts = [p for p in parts if p]  # Remove empty parts
        
        if not parts:
            return []
        
        # Try progressively less specific CSS selectors
        for i in range(len(parts)):
            # Build selector from current position to end
            current_selector = ''.join(parts[i:])
            
            try:
                elements = page.locator(current_selector).all()
                if elements:
                    results: List[str] = []
                    limit = len(elements) if maxResults == -1 else max(0, min(maxResults, len(elements)))
                    subset = elements if maxResults == -1 else elements[:limit]
                    for el in subset:
                        results.append(el.inner_text() if removeTags else el.inner_html())
                    if len(results) > 0:
                        logger.info(f"Found content with fuzzy CSS: {current_selector}")
                        return results
                        
            except Exception as e:
                logger.debug(f"Fuzzy CSS '{current_selector}' failed: {e}")
                continue
        
        # If still no content, try the most specific part
        most_specific = parts[-1]
        try:
            elements = page.locator(f".{most_specific}").all()
            if not elements:
                elements = page.locator(f"#{most_specific}").all()
            
            if elements:
                results: List[str] = []
                limit = len(elements) if maxResults == -1 else max(0, min(maxResults, len(elements)))
                subset = elements if maxResults == -1 else elements[:limit]
                for el in subset:
                    results.append(el.inner_text() if removeTags else el.inner_html())
                if len(results) > 0:
                    logger.info(f"Found content with most specific CSS: {most_specific}")
                    return results
                    
        except Exception as e:
            logger.debug(f"Most specific CSS '{most_specific}' failed: {e}")
        
        return []
        
    except Exception as e:
        logger.error(f"Fuzzy CSS matching failed for '{selector}': {e}")
        return []

def _wait_for_dom_stability(page, timeout: int, is_already_active: bool = False) -> bool:
    """
    Wait for DOM stability after a click action - adapted from async approach.
    Clicks an element, then waits until the page's DOM stops changing.
    
    Args:
        page: Playwright page object
        timeout: Maximum time to wait in milliseconds
        is_already_active: Whether the clicked element was already active
        
    Returns:
        True if DOM stabilized or timeout occurred, False on error
    """
    try:
        import time
        start_time = time.time() * 1000  # Convert to milliseconds
        
        # Configuration
        check_interval = 200  # Check every 200ms (0.2 seconds)
        stable_duration = 800  # DOM must be stable for 800ms (0.8 seconds)
        
        if is_already_active:
            # For already active elements, use shorter intervals
            check_interval = 100
            stable_duration = 400
        
        logger.info(f"Waiting for DOM stability (already_active: {is_already_active})")
        logger.debug(f"Check interval: {check_interval}ms, Stable duration: {stable_duration}ms")
        
        last_html = ""
        stable_time = 0.0
        
        while (time.time() * 1000) - start_time < timeout:
            try:
                # Get current DOM snapshot
                current_html = page.content()
                
                if current_html == last_html:
                    # DOM hasn't changed, accumulate stable time
                    stable_time += check_interval
                else:
                    # DOM changed, reset stable time
                    stable_time = 0.0
                    logger.debug("DOM changed, resetting stability timer")
                
                # Check if we've reached the required stable duration
                if stable_time >= stable_duration:
                    elapsed = int((time.time() * 1000) - start_time)
                    logger.info(f"DOM stabilized after {elapsed}ms (stable for {stable_time}ms)")
                    return True
                
                last_html = current_html
                page.wait_for_timeout(check_interval)
                
            except Exception as e:
                logger.debug(f"Error during DOM stability check: {e}")
                page.wait_for_timeout(check_interval)
        
        # Timeout reached
        elapsed = int((time.time() * 1000) - start_time)
        logger.info(f"DOM stability timeout reached after {elapsed}ms (stable for {stable_time}ms)")
        return True  # Still return True to not block execution
        
    except Exception as e:
        logger.error(f"Error waiting for DOM stability: {e}")
        return True  # Return True to not block execution

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
        page = _get_browser_client()
        timeout_ms = timeout if timeout else 5000
        
        if visible:
            page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
        else:
            page.wait_for_selector(selector, state="attached", timeout=timeout_ms)
        
        return True
    except Exception as e:
        logger.error(f"Failed to wait for element '{selector}': {e}")
        _print_dom_on_failure("wait_for_element", selector)
        return False