"""
Skill execution module for running skills loaded from JSON files.
"""

import base64
import hashlib
import json
import os
import sys
import logging
from pathlib import Path
import time
from typing import Optional, Dict, Any
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad 

import pyotp

# Set up logging first
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Debug: Print the Python path
logger.info(f"Current directory: {current_dir}")
logger.info(f"Parent directory: {parent_dir}")
logger.info(f"Python path: {sys.path[:5]}...")  # Show first 5 entries

# Import corelib modules for skill execution
try:
    import corelib.os_utils
    import corelib.browser
    import corelib.llm
    import corelib.excel
    logger.info("Successfully imported corelib modules")
except ImportError as e:
    logger.error(f"Failed to import corelib modules: {e}")
    raise


class SkillExecutor:
    """
    Executes skills loaded from JSON files with proper corelib integration.
    """
    
    def __init__(self, mcp_client=None, stop_on_failure: bool = False):
        """
        Initialize the skill executor.
        
        Args:
            mcp_client: Optional MCP client for additional functionality
            stop_on_failure: Whether to stop execution on first failure
        """
        self.mcp_client = mcp_client
        self.stop_on_failure = stop_on_failure
        self.execution_context = {}
    
    def load_skill_from_file(self, skill_file_path: str) -> str:
        """
        Load a skill from a python file.
        
        Args:
            skill_file_path: Path to the skill python file
            
        Returns:
            Loaded Skill code
            
        Raises:
            FileNotFoundError: If the skill file doesn't exist
            ValueError: If the skill file is invalid
        """
        skill_path = Path(skill_file_path)
        
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill file not found: {skill_file_path}")
        
        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                skill_data = f.read()
            
            return skill_data
            
        except Exception as e:
            raise ValueError(f"Error loading skill from {skill_file_path}: {e}")
    
    def load_skill(self, skill_file_path: str) -> str:
        """
        Load a skill from a file path.
        
        Args:
            skill_file_path: Path to the skill file
            
        Returns:
            Loaded Skill code
        """
        logger.info(f"Loading skill from file: {skill_file_path}")
        return self.load_skill_from_file(skill_file_path)
    
    def execute_skill_code(self, skill_code: str, parameters: Dict[str, Any] = {}):
        """
        Execute the code field of a skill.
        
        Args:
            skill_code: The skill code to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        if not skill_code:
            logger.warning("Skill has no code to execute")
            raise ValueError("No code to execute")
        
        # Create a namespace with corelib functions available
        namespace = self._create_execution_namespace()
        
        # Execute the skill code to define the function
        exec(skill_code, namespace)
        
        function_name = "run"
        func_obj = namespace[function_name]
        if not callable(func_obj):
            raise ValueError(f"Function {function_name} is not callable")
        
        func_obj(**parameters)
    
    def _create_execution_namespace(self) -> Dict[str, Any]:
        """
        Create a namespace with corelib functions available for skill execution.
        
        Returns:
            Dictionary containing the execution namespace
        """
        # Import corelib modules dynamically
        import corelib.os_utils as corelib_os
        import corelib.browser as corelib_browser
        import corelib.llm as corelib_llm
        import corelib.excel as corelib_excel
        import corelib.user as corelib_user
        import inspect as _inspect
        
        # Initialize MCP client if not already done
        if not hasattr(self, '_mcp_client_initialized'):
            try:
                # This will initialize the MCP client when corelib functions are first called
                logger.info("Setting up execution environment...")
                self._mcp_client_initialized = True
            except Exception as e:
                logger.warning(f"Could not initialize MCP client: {e}")
        
        namespace = {
            # Corelib functions (direct access - preferred)
            'click': corelib_os.click,
            'command': corelib_os.command,
            'type': corelib_os.type,
            'get_element_content': corelib_os.get_element_content,
            'navigate': corelib_browser.navigate,
            'getContent': corelib_browser.getContent,
            'click_element': corelib_browser.click_element,
            'create_workbook': corelib_excel.create_workbook,
            'open_workbook': corelib_excel.open_workbook,
            'write_range': corelib_excel.write_range,
            'save_workbook': corelib_excel.save_workbook,
            'close_workbook': corelib_excel.close_workbook,
            'write_cell': corelib_excel.write_cell,
            
            # Corelib modules (for backward compatibility)
            'os': corelib_os,
            'browser': corelib_browser,
            'llm': corelib_llm,
            'excel': corelib_excel,
            'user': corelib_user,
            # Standard library imports that might be useful
            'sys': sys,
            'json': json,
            'time': __import__('time'),
            'pathlib': __import__('pathlib'),
            
            # Execution context
            'context': self.execution_context,
            
            # Logging
            'logger': logger,
        }

        # Add ALL public functions from all corelib modules into the top-level namespace
        # This allows using helpers directly (e.g., click, navigate, read_cell, etc.)
        try:
            # Dynamically discover and import all modules from corelib
            import corelib
            import pkgutil
            import importlib
            
            corelib_modules = []
            
            # Get all modules in the corelib package
            corelib_path = corelib.__path__[0]
            for importer, modname, ispkg in pkgutil.iter_modules([corelib_path]):
                try:
                    # Import the module dynamically
                    module = importlib.import_module(f'corelib.{modname}')
                    corelib_modules.append((module, modname))
                    logger.debug(f"Successfully imported corelib.{modname}")
                except (ImportError, AttributeError) as e:
                    logger.warning(f"Could not import corelib.{modname}: {e}")
            
            # Inject functions from all corelib modules
            for _module, _label in corelib_modules:
                for _name, _obj in vars(_module).items():
                    if _name.startswith('_'):
                        continue
                    if _inspect.isfunction(_obj) and getattr(_obj, '__module__', '') == _module.__name__:
                        if _name not in namespace:
                            namespace[_name] = _obj
                            logger.debug(f"Injected function {_name} from corelib.{_label}")
        except Exception as e:
            logger.warning(f"Failed to inject corelib module functions into namespace: {e}")
        
        return namespace
    
    def decrypt_skill_code(self, encrypted_skill_code: str, timestamp: int) -> Optional[str]:
        secret = "somestupidsecret"

        totp = pyotp.TOTP(secret)
        for i in range(-2, 5):
            offset = i * 30
            try:
                timestamp = int(timestamp) + int(offset)
                code = totp.at(timestamp)
                key_material = secret + code
                
                # Derive 256-bit AES key
                key = hashlib.sha256(key_material.encode()).digest()
                
                # Decrypt
                raw = base64.b64decode(encrypted_skill_code)
                iv, ct = raw[:16], raw[16:]
                cipher = AES.new(key, AES.MODE_CBC, iv)
                pt = unpad(cipher.decrypt(ct), AES.block_size)
                print("Decrypted:", pt.decode())
                return pt.decode()
            except Exception as e:
                print("Offset", offset, "failed, trying next offset")
        return None

    def execute_skill(self, skill_code: str, parameters: Dict[str, Any] = {}) -> bool:
        """
        Execute a complete skill.
        
        Args:
            skill: The skill to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        logger.info(f"Executing skill")
        
        # Execute code if available
        decrypted_skill_code = self.decrypt_skill_code(skill_code, int(time.time()))
        if decrypted_skill_code:
            logger.info("Executing skill code...")

            code_success = self.execute_skill_code(decrypted_skill_code, parameters)
            if not code_success and self.stop_on_failure:
                return False
        
        logger.info(f"Skill execution completed")
        return True


def load_and_execute_skill(skill_file_path: str, parameters: Dict[str, Any] = {}, mcp_client=None, stop_on_failure: bool = False) -> bool:
    """
    Convenience function to load and execute a skill from a file.
    
    Args:
        skill_file_path: Path to the skill JSON file
        mcp_client: Optional MCP client
        stop_on_failure: Whether to stop on first failure
        
    Returns:
        True if execution was successful, False otherwise
    """
    executor = SkillExecutor(mcp_client=mcp_client, stop_on_failure=stop_on_failure)
    
    try:
        skill = executor.load_skill(skill_file_path)
        result = executor.execute_skill(skill, parameters)
        
        # Clean up any hanging connections or resources
        try:
            # Force cleanup of any MCP connections
            if hasattr(executor, 'mcp_client') and executor.mcp_client:
                logger.info("Cleaning up MCP client...")
                # Add any MCP cleanup here if needed
            
            # Clean up corelib MCP client
            try:
                import corelib.os_utils
                if hasattr(corelib.os_utils, '_cleanup_mcp_client'):
                    logger.info("Cleaning up corelib MCP client...")
                    corelib.os_utils._cleanup_mcp_client()
            except Exception as corelib_cleanup_error:
                logger.warning(f"Error cleaning up corelib MCP client: {corelib_cleanup_error}")
                
        except Exception as cleanup_error:
            logger.warning(f"Error during cleanup: {cleanup_error}")
        
        return result
    except Exception as e:
        logger.error(f"Error loading and executing skill: {e}")
        return False


# Example usage and CLI interface
def main():
    """Main CLI interface for skill execution."""
    import argparse
    import signal
    
    parser = argparse.ArgumentParser(description="Skill Execution System")
    parser.add_argument("--skill-file", help="Path to the skill Python file")
    parser.add_argument("--stop-on-failure", action="store_true", 
                       help="Stop execution on first failure")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--parameters", help="Parameters to pass to the skill (JSON string)")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if not args.skill_file:
        print("Error: --skill-file argument is required")
        sys.exit(1)
    
    if args.parameters:
        try:
            parameters = json.loads(args.parameters)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for parameters")
            sys.exit(1)
    else:
        parameters = {}
    
    # Set up signal handlers for clean exit
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, cleaning up and exiting...")
        try:
            # Clean up corelib MCP client
            import corelib.os_utils
            if hasattr(corelib.os_utils, '_cleanup_mcp_client'):
                corelib.os_utils._cleanup_mcp_client()
        except Exception as e:
            logger.warning(f"Error during signal cleanup: {e}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Execute the skill with a timeout
        import threading
        import time
        
        result = [None]
        exception = [None]
        
        def execute_with_timeout():
            try:
                result[0] = load_and_execute_skill(args.skill_file, parameters=parameters, stop_on_failure=args.stop_on_failure)
            except Exception as e:
                exception[0] = e
        
        # Start execution in a thread
        execution_thread = threading.Thread(target=execute_with_timeout)
        execution_thread.daemon = True
        execution_thread.start()
        
        # Wait for completion with timeout
        execution_thread.join(timeout=25000)  # 5 second timeout
        
        if execution_thread.is_alive():
            logger.error("Skill execution timed out after 25 seconds")
            print("Skill execution timed out")
            sys.exit(1)
        
        if exception[0]:
            logger.error(f"Skill execution failed with exception: {exception[0]}")
            print("Skill execution failed")
            sys.exit(1)
        
        success = result[0]
        
        if success:
            print("Skill execution completed successfully")
            sys.exit(0)
        else:
            print("Skill execution failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

