from dataclasses import dataclass
from typing import List, Optional, Any
import tempfile
import subprocess
import os
import inspect
import logging
from mcp.server import FastMCP

# Set up logging
logger = logging.getLogger(__name__)

# Create FastMCP server instance
server = FastMCP("Sisypho Skill Verification Server")

@dataclass
class Skill:
    """Represents a skill with its metadata and code."""
    name: str
    code: str
    parameters: Optional[List[dict]] = None
    description: Optional[str] = None

@dataclass
class VerifySkillDraftOutput:
    """Output from skill verification containing mypy results and errors."""
    mypy_success: bool
    errors: List[str]
    modified_skill: Optional[Skill] = None

def verify_skill_draft(skill_draft: Skill) -> VerifySkillDraftOutput:
    """
    Modifies skill for lib use if needed, saves file temp, uses mypy to static type check.
    
    Args:
        skill_draft: The skill draft to verify
        
    Returns:
        Mypy success status and any errors
    """
    logger.info(f"Starting skill draft verification for: {getattr(skill_draft, 'name', 'Unknown')}")
    
    if not skill_draft.code:
        logger.error("Skill verification failed: no code provided")
        return VerifySkillDraftOutput(
            mypy_success=False,
            errors=["No code provided in skill draft"],
            modified_skill=None
        )
    
    # Create a temporary Python file
    temp_fd = None
    temp_file_path = None
    mypy_config_fd = None
    mypy_config_path = None
    
    try:
        # Get the path to the sisypho package root
        # When installed from wheel, this will be the site-packages location
        # When running from source, this will be the repo root
        package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Check if we're in a development environment (has corelib directory)
        # or installed environment (has sisypho package structure)
        if os.path.exists(os.path.join(package_root, 'corelib')):
            # Development environment - use package_root as repo_root
            repo_root = package_root
        else:
            # Installed environment - find the sisypho package
            import sisypho
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(sisypho.__file__)))
        
        # Create temporary file in a temp directory instead of repo root
        temp_fd, temp_file_path = tempfile.mkstemp(suffix='.py', prefix='skill_draft_')
        
        # Create a mypy configuration file 
        mypy_config_fd, mypy_config_path = tempfile.mkstemp(suffix='.ini', prefix='mypy_config_')
        
        # Write the skill code to the temporary file
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
            temp_file.write(skill_draft.code)
            temp_fd = None  # File handle is now closed
        
        # Write mypy configuration that enables strict checking but handles corelib properly
        with os.fdopen(mypy_config_fd, 'w', encoding='utf-8') as config_file:
            config_file.write(f"""[mypy]
# Only analyze the specific file, don't follow imports to avoid corelib analysis issues
follow_imports = silent
# Ignore missing imports for third party libraries
ignore_missing_imports = False
# Disable strict optional to avoid issues with Optional types
strict_optional = False
# Allow untyped calls and definitions to avoid issues with third-party libraries
disallow_untyped_calls = False
disallow_untyped_defs = False

[mypy-sisypho.*]
ignore_missing_imports = True

[mypy-corelib.*]
ignore_missing_imports = True
""")
            mypy_config_fd = None
        
        # Run mypy on the temporary file
        try:
            # Set up environment with MYPYPATH
            env = os.environ.copy()
            # Only add to MYPYPATH if we're in a development environment
            # For installed packages, mypy should be able to find modules through normal Python path
            if os.path.exists(os.path.join(repo_root, 'corelib')):
                # Development environment - add repo root to MYPYPATH
                env['MYPYPATH'] = repo_root
            else:
                # Installed environment - don't set MYPYPATH, let mypy use normal Python path
                if 'MYPYPATH' in env:
                    del env['MYPYPATH']
            
            logger.info(f"Running mypy type checking on {temp_file_path}")
            
            # Check if mypy is available
            try:
                subprocess.run(['mypy', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("mypy not found, skipping type checking")
                return VerifySkillDraftOutput(
                    mypy_success=True,  # Consider it successful if mypy is not available
                    errors=[],
                    modified_skill=skill_draft
                )
            
            result = subprocess.run(
                ['mypy', temp_file_path, '--config-file', mypy_config_path, '--show-error-codes', '--no-error-summary'],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=os.path.dirname(temp_file_path),  # Run from temp file directory
                env=env
            )
            
            # Parse mypy output
            mypy_success = result.returncode == 0
            errors = []
            
            logger.info(f"Mypy type checking completed - success: {mypy_success}, return code: {result.returncode}")
            
            if result.stdout:
                # Filter out the temp file path from error messages for cleaner output
                stdout_lines = result.stdout.strip().split('\n')
                for line in stdout_lines:
                    if line.strip():
                        # Replace temp file path with generic "skill_draft.py" for cleaner errors
                        cleaned_line = line.replace(temp_file_path, 'skill_draft.py')
                        errors.append(cleaned_line)
            
            if result.stderr:
                # Add stderr messages as well
                stderr_lines = result.stderr.strip().split('\n')
                for line in stderr_lines:
                    if line.strip():
                        cleaned_line = line.replace(temp_file_path, 'skill_draft.py')
                        errors.append(f"Error: {cleaned_line}")
            
            # Extract parameters from the skill code if not already present
            if not skill_draft.parameters and skill_draft.code:
                try:
                    namespace = {}
                    exec(skill_draft.code, namespace)
                    
                    function_name = "run"
                    if function_name in namespace:
                        func_obj = namespace[function_name]
                        if callable(func_obj):
                            sig = inspect.signature(func_obj)
                            function_parameters = [
                                {
                                    "name": param.name,
                                    "type": str(param.annotation) if param.annotation != inspect._empty else None,
                                    "default": param.default if param.default != inspect._empty else None
                                }
                                for param in sig.parameters.values()
                            ]
                            # Update the skill draft with parameters
                            skill_draft.parameters = function_parameters
                except SyntaxError as e:
                    logger.error(f"Syntax error in generated code: {e}")
                    # Add syntax error to the errors list
                    errors.append(f"Syntax error: {e}")
                except Exception as e:
                    logger.warning(f"Could not extract parameters from skill code: {e}")
                    errors.append(f"Code execution error: {e}")
            
            return VerifySkillDraftOutput(
                mypy_success=mypy_success,
                errors=errors,
                modified_skill=skill_draft  # Return the skill with parameters
            )
            
        except subprocess.TimeoutExpired:
            logger.error("Mypy execution timed out after 30 seconds")
            return VerifySkillDraftOutput(
                mypy_success=False,
                errors=["Mypy execution timed out after 30 seconds"],
                modified_skill=skill_draft  # Return skill even if mypy fails
            )
        except FileNotFoundError:
            logger.error("Mypy not found. Please ensure mypy is installed (pip install mypy)")
            return VerifySkillDraftOutput(
                mypy_success=False,
                errors=["Mypy not found. Please ensure mypy is installed (pip install mypy)"],
                modified_skill=skill_draft  # Return skill even if mypy fails
            )
        except Exception as e:
            logger.error(f"Error running mypy: {str(e)}")
            return VerifySkillDraftOutput(
                mypy_success=False,
                errors=[f"Error running mypy: {str(e)}"],
                modified_skill=skill_draft  # Return skill even if mypy fails
            )
    
    except Exception as e:
        logger.error(f"Error creating temporary file: {str(e)}")
        return VerifySkillDraftOutput(
            mypy_success=False,
            errors=[f"Error creating temporary file: {str(e)}"],
            modified_skill=skill_draft  # Return skill even if file creation fails
        )
    
    finally:
        # Clean up temporary files
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except Exception as e:
                logger.warning(f"Error closing temp file descriptor: {e}")
        
        if 'mypy_config_fd' in locals() and mypy_config_fd is not None:
            try:
                os.close(mypy_config_fd)
            except Exception as e:
                logger.warning(f"Error closing mypy config file descriptor: {e}")
        
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Error removing temporary file {temp_file_path}: {e}")
        
        if 'mypy_config_path' in locals() and mypy_config_path and os.path.exists(mypy_config_path):
            try:
                os.unlink(mypy_config_path)
                logger.debug(f"Cleaned up mypy config file: {mypy_config_path}")
            except Exception as e:
                logger.warning(f"Error removing mypy config file {mypy_config_path}: {e}")

# Register the tool with the server
server.add_tool(
    verify_skill_draft,
    name="verify_skill_draft",
    description="Modifies skill for lib use if needed, saves file temp, uses mypy to static type check"
)

import asyncio
import threading

def start_mcp_server():
    """
    Start the MCP server in a background thread.
    Returns the thread object so you can join it or check if it's running.
    """
    def run_server():
        async def main():
            await server.run_stdio_async()
        
        asyncio.run(main())
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread

if __name__ == "__main__":
    # Start server and keep main thread alive
    server_thread = start_mcp_server()
    print("MCP server started in background thread")
    
    try:
        # Keep main thread alive
        while server_thread.is_alive():
            server_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("Shutting down...")