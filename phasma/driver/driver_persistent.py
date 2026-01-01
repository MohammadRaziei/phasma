import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
from .driver import Driver


class DriverPersistent(Driver):
    """
    A persistent driver that maintains a single PhantomJS process for multiple operations,
    similar to Playwright's persistent context approach.
    """

    def __init__(self):
        super().__init__()
        self._process = None
        self._is_closed = False
        self._temp_scripts = []
        self._command_file = None
        self._response_file = None
        self._last_response_time = 0

    def start_persistent_session(self, args: Optional[Sequence[str]] = None):
        """
        Start a persistent PhantomJS session that can handle multiple commands.
        Uses file-based communication to avoid stdin/stdout issues.
        """
        if self._process is not None and self._process.poll() is None:
            return  # Already running

        # Create temporary files for command and response communication
        self._command_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".cmd")
        self._response_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".rsp")

        self._temp_scripts.extend([self._command_file.name, self._response_file.name])

        # Create a persistent script that reads commands from a file and writes responses to another file
        persistent_script = f"""var page = require('webpage').create();
var fs = require('fs');
var system = require('system');

page.viewportSize = {{ width: 1024, height: 768 }};
page.settings.javascriptEnabled = true;
page.settings.localToRemoteUrlAccess = true;

// File-based communication
var commandFile = '{self._command_file.name}';
var responseFile = '{self._response_file.name}';

// Output a ready message to indicate the process is listening
console.log('READY');

// Function to read and process commands
function processCommands() {{
    try {{
        if (fs.exists(commandFile)) {{
            var content = fs.read(commandFile);
            if (content && content.trim() !== '') {{
                var command = JSON.parse(content.trim());
                var action = command.action;
                var params = command.params || {{}};

                // Clear the command file
                fs.write(commandFile, '', 'w');

                if (action === 'navigate') {{
                    page.open(params.url, function(status) {{
                        if (status === 'success') {{
                            window.setTimeout(function() {{
                                var content = page.evaluate(function() {{
                                    return document.documentElement.outerHTML;
                                }});
                                var response = JSON.stringify({{ type: 'result', data: content }});
                                fs.write(responseFile, response, 'w');
                            }}, 100); // Small delay to ensure page is loaded
                        }} else {{
                            var response = JSON.stringify({{ type: 'error', message: 'Failed to load URL' }});
                            fs.write(responseFile, response, 'w');
                        }}
                    }});
                }} else if (action === 'evaluate') {{
                    var result = page.evaluate(function(expression) {{
                        return eval(expression);
                    }}, params.expression);
                    var response = JSON.stringify({{ type: 'result', data: result }});
                    fs.write(responseFile, response, 'w');
                }} else if (action === 'click') {{
                    var success = page.evaluate(function(selector) {{
                        var el = document.querySelector(selector);
                        if (el) {{
                            var event = document.createEvent('MouseEvent');
                            event.initMouseEvent('click', true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                            el.dispatchEvent(event);
                            return true;
                        }}
                        return false;
                    }}, params.selector);
                    var response = JSON.stringify({{ type: 'result', data: success }});
                    fs.write(responseFile, response, 'w');
                }} else if (action === 'fill') {{
                    var success = page.evaluate(function(selector, value) {{
                        var el = document.querySelector(selector);
                        if (el) {{
                            el.value = value;
                            // Trigger input and change events
                            var inputEvent = document.createEvent('Event');
                            inputEvent.initEvent('input', true, true);
                            el.dispatchEvent(inputEvent);

                            var changeEvent = document.createEvent('Event');
                            changeEvent.initEvent('change', true, true);
                            el.dispatchEvent(changeEvent);

                            return true;
                        }}
                        return false;
                    }}, params.selector, params.value);
                    var response = JSON.stringify({{ type: 'result', data: success }});
                    fs.write(responseFile, response, 'w');
                }} else if (action === 'screenshot') {{
                    page.render(params.path);
                    var response = JSON.stringify({{ type: 'result', data: 'Screenshot saved' }});
                    fs.write(responseFile, response, 'w');
                }} else if (action === 'close') {{
                    phantom.exit();
                }}
            }}
        }}
    }} catch (e) {{
        var response = JSON.stringify({{ type: 'error', message: e.message }});
        fs.write(responseFile, response, 'w');
    }}

    // Schedule next check
    setTimeout(processCommands, 50); // Check every 50ms
}}

// Start processing commands
processCommands();

// Keep the process alive by not exiting
"""

        # Write the persistent script to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(persistent_script)
            temp_script = f.name

        self._temp_scripts.append(temp_script)

        # Start the persistent PhantomJS process
        # Set environment to avoid SSL configuration issues
        env = os.environ.copy()
        env["OPENSSL_CONF"] = ""  # or "" to disable OpenSSL config

        cmd = [str(self.bin_path), "--ssl-protocol=any", "--ignore-ssl-errors=true", temp_script]
        if args:
            cmd.extend(list(args))

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=env
        )


        # On Linux/Mac, we can use select, but on Windows we need a different approach
        # For cross-platform compatibility, let's use a simple timeout approach
        start_time = time.time()
        ready_received = False

        # Poll for the ready message
        while time.time() - start_time < 10:  # 10 second timeout
            # Check if the process is still alive
            if self._process.poll() is not None:
                # Process has exited, get any error output
                stderr_output = self._process.stderr.read() if hasattr(self._process.stderr, 'read') else ''
                raise RuntimeError(f"Persistent session process exited early. STDERR: {stderr_output}")

            # Try to read the output
            try:
                # Use a small timeout to avoid blocking
                ready_output = self._process.stdout.readline()
                if "READY" in ready_output:
                    ready_received = True
                    break
            except:
                # If readline fails (e.g., due to buffering), continue
                time.sleep(0.1)
                continue

        if not ready_received:
            raise RuntimeError("Persistent session failed to start properly - no READY message received within timeout")

    def send_command(self, action: str, params: Optional[Dict] = None, timeout: float = 60.0) -> Any:
        """
        Send a command to the persistent PhantomJS process via file-based communication.

        Args:
            action: The action to perform (e.g., 'navigate', 'evaluate', 'click')
            params: Parameters for the action
            timeout: Timeout for the command execution

        Returns:
            The result of the command
        """
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("Persistent session not started or already closed")

        if self._is_closed:
            raise RuntimeError("Driver has been closed")

        command = {
            "action": action,
            "params": params or {}
        }

        # Write command to the command file
        with open(self._command_file.name, 'w') as f:
            f.write(json.dumps(command))

        # Wait for response with timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if response file has content
            try:
                with open(self._response_file.name, 'r') as f:
                    response_content = f.read().strip()

                if response_content:
                    # Clear the response file for next use
                    with open(self._response_file.name, 'w') as f:
                        f.write('')

                    result = json.loads(response_content)

                    if result["type"] == "error":
                        raise RuntimeError(f"PhantomJS error: {result['message']}")
                    elif result["type"] == "result":
                        return result["data"]
            except json.JSONDecodeError:
                # Response not ready yet, continue waiting
                time.sleep(0.05)
                continue

            # Small delay to prevent busy waiting
            time.sleep(0.05)

        raise TimeoutError(f"Command '{action}' timed out after {timeout} seconds")

    def exec(
        self,
        args: Union[str, Sequence[str]],
        *,
        capture_output: bool = False,
        timeout: Optional[float] = 60,  # Increased timeout for persistent operations
        check: bool = False,
        ssl: bool = False,
        env: Optional[dict] = None,
        cwd: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """
        Execute PhantomJS with the given arguments using the persistent session.
        For simple commands like --version, falls back to original method.
        For script files, also falls back to maintain compatibility for complex operations.
        """
        # Check if this is a script execution (contains a .js file)
        if isinstance(args, str):
            args_list = [args]
        else:
            args_list = list(args)

        # Check if any argument is a JavaScript file (temporary script)
        has_js_file = any(arg.endswith('.js') for arg in args_list)

        if has_js_file:
            # For script files, fall back to the original implementation
            # This maintains compatibility for complex operations like PDF generation
            return super().exec(
                args,
                capture_output=capture_output,
                timeout=timeout,
                check=check,
                ssl=ssl,
                env=env,
                cwd=cwd,
                **kwargs
            )
        else:
            # For simple commands, use the persistent session approach
            if self._process is None or self._process.poll() is not None:
                self.start_persistent_session()

            # If args is a simple command, we'll convert it to a command for the persistent session
            if isinstance(args, str):
                # For persistent sessions, we need to handle this differently
                # This is a simplified approach - in practice, you'd want to parse the command
                # and convert it to appropriate persistent commands
                if args.strip() == "--version":
                    # Handle version command specially
                    cmd = [str(self.bin_path), "--version"]

                    if not ssl:
                        if env is None:
                            env = os.environ.copy()
                        env["OPENSSL_CONF"] = ""

                    return subprocess.run(
                        cmd,
                        capture_output=capture_output,
                        timeout=timeout,
                        check=check,
                        env=env,
                        cwd=cwd,
                        **kwargs,
                    )
                else:
                    # For other commands, we'll need to parse and convert to persistent commands
                    # This is a simplified implementation - a full implementation would need
                    # to parse PhantomJS command line arguments and convert them to appropriate
                    # persistent session commands
                    raise NotImplementedError(f"Command '{args}' not supported in persistent mode. Use specific methods like navigate(), evaluate(), etc.")
            else:
                # Handle sequence of args
                args_list = list(args)
                if "--version" in args_list:
                    cmd = [str(self.bin_path), "--version"]

                    if not ssl:
                        if env is None:
                            env = os.environ.copy()
                        env["OPENSSL_CONF"] = ""

                    return subprocess.run(
                        cmd,
                        capture_output=capture_output,
                        timeout=timeout,
                        check=check,
                        env=env,
                        cwd=cwd,
                        **kwargs,
                    )
                else:
                    raise NotImplementedError(f"Command '{args}' not supported in persistent mode. Use specific methods like navigate(), evaluate(), etc.")

    def navigate(self, url: str, timeout: float = 60.0) -> str:
        """Navigate to a URL using the persistent session."""
        return self.send_command("navigate", {"url": url}, timeout=timeout)

    def evaluate(self, expression: str, timeout: float = 60.0) -> Any:
        """Evaluate a JavaScript expression using the persistent session."""
        return self.send_command("evaluate", {"expression": expression}, timeout=timeout)

    def click(self, selector: str, timeout: float = 60.0) -> bool:
        """Click an element using the persistent session."""
        return self.send_command("click", {"selector": selector}, timeout=timeout)

    def fill(self, selector: str, value: str, timeout: float = 60.0) -> bool:
        """Fill an input field using the persistent session."""
        return self.send_command("fill", {"selector": selector, "value": value}, timeout=timeout)

    def take_screenshot(self, path: Union[str, Path], timeout: float = 60.0) -> str:
        """Take a screenshot using the persistent session."""
        return self.send_command("screenshot", {"path": str(path)}, timeout=timeout)

    def close(self):
        """Close the persistent session."""
        if self._process and self._process.poll() is None:
            try:
                # Send close command to the process
                self.send_command("close", timeout=5.0)
            except:
                # If sending close command fails, terminate the process
                self._process.terminate()
                try:
                    self._process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    self._process.kill()

        # Clean up temporary files
        for script in self._temp_scripts:
            try:
                if os.path.exists(script):
                    os.unlink(script)
            except OSError:
                pass  # Ignore errors when cleaning up temp files

        self._is_closed = True
        self._process = None
        # Close file handles if they exist
        if hasattr(self, '_command_file') and self._command_file:
            try:
                self._command_file.close()
            except:
                pass
        if hasattr(self, '_response_file') and self._response_file:
            try:
                self._response_file.close()
            except:
                pass

    def __del__(self):
        """Cleanup when the object is destroyed."""
        if not self._is_closed and self._process:
            self.close()