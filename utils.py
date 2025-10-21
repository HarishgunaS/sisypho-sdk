import uuid
import threading
import sys
import io
import ctypes
import logging
from datetime import datetime
from typing import Optional
from typing import Callable
from execution.recording import record_mode, MCPRecordManager
from execution.skill import SkillExecutor
import requests
import json
import subprocess
import time
import socket
import os
from pathlib import Path


def is_port_in_use(port: int, host: str = 'localhost') -> bool:
    """Check if a port is in use by attempting to connect to it."""
    try:
        response = requests.get(f'http://{host}:{port}/count', timeout=2)
        return response.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False


def find_event_polling_binary() -> Optional[str]:
    """Find the event-polling-cli binary path."""
    try:
        from integrations.macos import get_event_polling_cli_path
        return str(get_event_polling_cli_path())
    except (ImportError, FileNotFoundError) as e:
        return None


def start_event_polling_cli() -> Optional[subprocess.Popen]:
    """Start the event-polling-cli binary if not already running."""
    # Check if already running
    if is_port_in_use(8080):
        print("Event polling CLI is already running on port 8080")
        return None
    
    # Find the binary
    binary_path = find_event_polling_binary()
    if not binary_path:
        print("ERROR: event-polling-cli binary not found. Please build it first:")
        print("  cd integrations/macos/servers/EventPollingApp")
        print("  swift build --configuration release")
        raise FileNotFoundError("event-polling-cli binary not found")
    
    print(f"Starting event-polling-cli from: {binary_path}")
    
    # Start the process
    try:
        process = subprocess.Popen(
            [binary_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=dict(os.environ, PARENT_PROCESS_ID=str(os.getpid()))
        )
        
        # Wait a bit for the server to start
        max_wait = 10  # seconds
        wait_interval = 0.5
        elapsed = 0
        
        while elapsed < max_wait:
            if is_port_in_use(8080):
                print("✓ Event polling CLI started successfully")
                return process
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            # Check if process died
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"ERROR: event-polling-cli process died during startup")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                raise RuntimeError("event-polling-cli failed to start")
        
        # Timeout waiting for server to respond
        print("WARNING: event-polling-cli started but not responding on port 8080")
        return process
        
    except Exception as e:
        print(f"ERROR: Failed to start event-polling-cli: {e}")
        raise


class RecorderContext:
    def __init__(self):
        # Get accessibility server path dynamically
        try:
            from integrations.macos import get_accessibility_server_path
            accessibility_server = str(get_accessibility_server_path())
        except (ImportError, FileNotFoundError):
            # Fallback to hardcoded path for development
            accessibility_server = "integrations/macos/servers/.build/arm64-apple-macosx/release/AccessibilityMCPServer"
        
        self.default_servers = [
            accessibility_server,
            "integrations/chrome/chrome-extension-bridge-mcp/node_modules/.bin/tsx integrations/chrome/chrome-extension-bridge-mcp/examples/mcp.ts",
        ]
        self.servers = self.default_servers
        self.manager = MCPRecordManager()
        self.recording_thread = None
        self.stdout_capture = io.StringIO()
        self.stderr_capture = io.StringIO()
        self.event_polling_process = None  # Store the event-polling-cli process
        
        # Save original stdout/stderr so main thread can still print
        self.original_stdout = sys.__stdout__
        self.original_stderr = sys.__stderr__
        
        # Start event-polling-cli before initializing MCP servers
        print("Checking event-polling-cli status...")
        try:
            self.event_polling_process = start_event_polling_cli()
        except Exception as e:
            print(f"Failed to start event-polling-cli: {e}")
            raise
        
        # Suppress output during initialization as well
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        # Create logging handler for initialization
        init_stderr_capture = io.StringIO()
        string_handler = logging.StreamHandler(init_stderr_capture)
        string_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        string_handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers.copy()
        
        try:
            # Redirect all output during initialization
            sys.stdout = io.StringIO()
            sys.stderr = init_stderr_capture
            root_logger.handlers = [string_handler]
            
            for server in self.servers:
                self.manager.add_server(server)

            if not self.manager.initialize_all():
                raise Exception("Failed to initialize some servers")
        finally:
            # Restore output
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            root_logger.handlers = original_handlers
        

    def __enter__(self):
        # Use original stdout to ensure message is visible
        sys.__stdout__.write("Recording started\n")
        sys.__stdout__.flush()
        
        # Define a wrapper function that captures stdout and stderr
        def run_recording():
            # Save original stdout/stderr
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            
            # Create a logging handler that writes to our stderr capture
            string_handler = logging.StreamHandler(self.stderr_capture)
            string_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
            string_handler.setFormatter(formatter)
            
            # Get the root logger and recording logger
            root_logger = logging.getLogger()
            recording_logger = logging.getLogger('execution.recording')
            
            # Save original handlers
            original_handlers = root_logger.handlers.copy()
            original_recording_handlers = recording_logger.handlers.copy()
            
            try:
                # Redirect stdout and stderr to StringIO buffers
                sys.stdout = self.stdout_capture
                sys.stderr = self.stderr_capture
                
                # Replace logging handlers with our captured handler
                root_logger.handlers = [string_handler]
                recording_logger.handlers = [string_handler]
                
                try:
                    record_mode(self.manager, output_dir="recording")
                except KeyboardInterrupt:
                    # Expected when we stop the recording
                    pass
                finally:
                    # Restore stdout/stderr
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
                    
                    # Restore logging handlers
                    root_logger.handlers = original_handlers
                    recording_logger.handlers = original_recording_handlers
            except Exception as e:
                # Restore before printing error
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                root_logger.handlers = original_handlers
                recording_logger.handlers = original_recording_handlers
                sys.__stderr__.write(f"Recording thread error: {e}\n")
                sys.__stderr__.flush()
        
        # Start recording in a background thread
        self.recording_thread = threading.Thread(target=run_recording, daemon=True)
        self.recording_thread.start()
        return self

    def _raise_exception_in_thread(self, thread_id, exception_type):
        """Raise an exception in a thread by its thread ID."""
        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread_id), ctypes.py_object(exception_type)
        )
        if ret == 0:
            raise ValueError("Invalid thread ID")
        elif ret > 1:
            # If more than one thread was affected, revert the action
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
            raise SystemError("Failed to raise exception in thread")

    def __exit__(self, exc_type, exc_value, traceback):
        # Use original stdout to ensure message is visible
        sys.__stdout__.write("Recording stopped\n")
        sys.__stdout__.flush()
        
        # Stop the recording thread by sending KeyboardInterrupt
        if self.recording_thread and self.recording_thread.is_alive():
            try:
                # Raise KeyboardInterrupt in the recording thread
                self._raise_exception_in_thread(self.recording_thread.ident, KeyboardInterrupt)
                # Wait for the thread to finish
                self.recording_thread.join(timeout=3.0)
                if self.recording_thread.is_alive():
                    sys.__stdout__.write("Warning: Recording thread did not stop gracefully\n")
                    sys.__stdout__.flush()
            except Exception as e:
                sys.__stdout__.write(f"Error stopping recording thread: {e}\n")
                sys.__stdout__.flush()
            
        self.manager.cleanup()
        
        # Stop event-polling-cli if we started it
        if self.event_polling_process is not None:
            try:
                sys.__stdout__.write("Stopping event-polling-cli...\n")
                sys.__stdout__.flush()
                self.event_polling_process.terminate()
                # Wait for graceful shutdown
                try:
                    self.event_polling_process.wait(timeout=5.0)
                    sys.__stdout__.write("✓ Event polling CLI stopped\n")
                    sys.__stdout__.flush()
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop gracefully
                    self.event_polling_process.kill()
                    self.event_polling_process.wait()
                    sys.__stdout__.write("✓ Event polling CLI force stopped\n")
                    sys.__stdout__.flush()
            except Exception as e:
                sys.__stdout__.write(f"Error stopping event-polling-cli: {e}\n")
                sys.__stdout__.flush()
        
        # Print captured output summary if desired
        captured_stdout = self.stdout_capture.getvalue()
        captured_stderr = self.stderr_capture.getvalue()
        
        # if captured_stdout:
        #     sys.__stdout__.write(f"\n--- Captured stdout ({len(captured_stdout)} chars) ---\n")
        #     sys.__stdout__.flush()
        #     # Optionally print or save this somewhere
        
        # if captured_stderr:
        #     sys.__stdout__.write(f"\n--- Captured stderr ({len(captured_stderr)} chars) ---\n")
        #     sys.__stdout__.flush()
        #     # Optionally print or save this somewhere

    def get_recording(self) -> str:
        with open("recording/recording.jsonl", "r") as f:
            recording = f.read()
            return recording
    
    def get_captured_output(self) -> tuple[str, str]:
        """
        Get the captured stdout and stderr from the recording thread.
        
        Returns:
            Tuple of (stdout, stderr) strings
        """
        return (self.stdout_capture.getvalue(), self.stderr_capture.getvalue())


def await_task_completion():
    # Write directly to the original stdout to bypass any redirection from recording thread
    sys.__stdout__.write("\nPress Enter to stop recording...")
    sys.__stdout__.flush()
    input()

class Workflow:
    def __init__(self, api_key: str, recording: str, task_prompt: str):
        self.recording = recording
        self.task_prompt = task_prompt
        self.code = ""
        self.api_key = api_key

    def generate_code(self):
        # TODO: add api key!!!

        data = {
            "prompt": f"Create a skill that performs the following task: {self.task_prompt}",
            "recording": self.recording
        }
    
        print("Generating skill...")
        response = requests.post(
            "http://localhost:8000/api/v1/generate-skill",
            json=data
        )
    
        print(f"Generate Skill: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Skill Name: {result['skill']['name']}")
            print(f"Verification Passed: {result['verification_passed']}")
            if result.get('verification_errors'):
                print(f"Verification Errors: {result['verification_errors']}")
            print(f"Code Preview (first 200 chars):\n{result['skill']['code'][:200]}...")
            self.code = result['skill']['code']
        else:
            print(json.dumps(response.json(), indent=2))
            self.code = ""
        print()

        

    def run_workflow(self, fallback_cua: Optional[Callable[[str], str]] = None) -> bool:
        # TODO: implement this
        try:
            SkillExecutor().execute_skill_code(self.code)
        except Exception as e:
            if fallback_cua:
                return fallback_cua(self.fallback_cua_prompt(str(e)))
            else:
                raise e


    def fallback_cua_prompt(self, execution_error: Optional[str] = None) -> str:
        return f"""
        You are a helpful computer use agent. You are being used as a fallback for a failed desktop automation workflow.
        
        The task description is as follows:

        {self.task_prompt}

        The code for the workflow is as follows:

        {self.code}

        {f"The execution error is as follows: {execution_error}" if execution_error else ""}

        """


    def amend(self, message: str, recording: Optional[str] = None):
        # TODO: implement this
        raise NotImplementedError("Amend is not implemented")

    def save(self):
        with open("workflow.json", "w") as f:
            json.dump(self.__dict__, f)
    
    def load(path: str) -> 'Workflow':
        with open(path, "r") as f:
            data = json.load(f)
            workflow = Workflow(data['api_key'], data['recording'], data['task_prompt'])
            if 'code' in data:
                workflow.code = data['code']
            return workflow
            