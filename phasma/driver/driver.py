import os
import platform
import stat
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Union

# Handle relative import when script is run directly
if __package__ is None:
    # Add src directory to sys.path to allow absolute imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from download import DRIVER_PATH, DRIVER_VERSION, download_driver
else:
    from .download import DRIVER_PATH, DRIVER_VERSION, download_driver

PHASMA_PATH = DRIVER_PATH / "phantomjs"


class Driver:
    """
    Manages the PhantomJS executable path in an OS-aware manner.
    - Always expects the binary inside a `bin/` subdirectory.
    - Uses `phantomjs.exe` on Windows and `phantomjs` on Unix-like systems.
    - Ensures the binary is executable (applies chmod +x on non-Windows).
    - Downloads the driver automatically if not present.
    """

    @staticmethod
    def download(os_name: str | None = None, arch: str | None = None):
        return download_driver(dest=DRIVER_PATH, os_name=os_name, arch=arch)

    def __init__(self):
        # Determine the correct executable name based on the OS
        self.system = platform.system()
        self.exe_name = "phantomjs.exe" if self.system == "Windows" else "phantomjs"

        # Final expected path: <DRIVER_PATH>/bin/<phantomjs or phantomjs.exe>
        self._bin_path = PHASMA_PATH / "bin" / self.exe_name

        # If the binary doesn't exist, download and set it up
        if not self._bin_path.is_file():
            # Download the driver to the root directory first
            self.download()

        self.get_exe_access()

    def get_exe_access(self):
        # On non-Windows systems, ensure the file is executable
        if self.system != "Windows":
            if not os.access(self._bin_path, os.X_OK):
                try:
                    current_mode = self._bin_path.stat().st_mode
                    self._bin_path.chmod(current_mode | stat.S_IEXEC)
                except OSError:
                    # Ignore if permission cannot be changed (e.g., read-only FS)
                    pass

    @property
    def bin_path(self) -> Path:
        """Returns the absolute path to the PhantomJS executable."""
        return self._bin_path

    @property
    def examples_path(self) -> Path:
        return PHASMA_PATH / "examples"

    @property
    def examples_list(self) -> List:
        return list(self.examples_path.iterdir())

    @property
    def version(self) -> str:
        return DRIVER_VERSION

    def exec(
        self,
        args: Union[str, Sequence[str]],
        *,
        capture_output: bool = False,
        timeout: Optional[float] = None,
        check: bool = False,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """
        Execute PhantomJS with the given arguments.

        Args:
            args: Command line arguments as a string or sequence of strings.
            capture_output: If True, capture stdout and stderr.
            timeout: Timeout in seconds.
            check: If True, raise CalledProcessError on non-zero exit code.
            **kwargs: Additional arguments passed to subprocess.run.

        Returns:
            subprocess.CompletedProcess instance.

        Example:
            >>> driver = Driver()
            >>> result = driver.exec(["--version"])
            >>> print(result.stdout)
        """
        if isinstance(args, str):
            # Split by spaces (simple split, no quoted string handling)
            args = args.split()

        cmd = [str(self.bin_path), *list(args)]
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            timeout=timeout,
            check=check,
            **kwargs,
        )

    def run(self, *args, **kwargs) -> subprocess.CompletedProcess:
        """Alias for exec."""
        return self.exec(*args, **kwargs)


if __name__ == "__main__":
    import argparse
    import os
    import sys

    # Add src directory to sys.path to allow relative imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    parser = argparse.ArgumentParser(
        description="Run PhantomJS via Driver", epilog="Example: python -m phasma.driver.driver --version"
    )
    parser.add_argument("args", nargs="*", help="Arguments to pass to PhantomJS (e.g., '--version', 'script.js')")
    parser.add_argument("--capture-output", action="store_true", help="Capture stdout and stderr")
    parser.add_argument("--timeout", type=float, help="Timeout in seconds")
    parser.add_argument("--check", action="store_true", help="Raise CalledProcessError on non-zero exit code")
    parsed, unknown = parser.parse_known_args()

    driver = Driver()
    try:
        # Combine known positional args with unknown args (which are likely PhantomJS options)
        all_args = parsed.args + unknown
        result = driver.exec(
            all_args,
            capture_output=parsed.capture_output,
            timeout=parsed.timeout,
            check=parsed.check,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if parsed.capture_output:
        if result.stdout:
            sys.stdout.buffer.write(result.stdout)
        if result.stderr:
            sys.stderr.buffer.write(result.stderr)
    sys.exit(result.returncode)
