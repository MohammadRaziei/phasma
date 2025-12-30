import os
import platform
import stat
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence, Union

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
    def download(os_name: str | None = None, arch: str | None = None, force: bool = False):
        return download_driver(dest=DRIVER_PATH, os_name=os_name, arch=arch, force=force)

    def __init__(self):
        # Determine the correct executable name based on the OS
        self.system = platform.system()
        self.exe_name = "phantomjs.exe" if self.system == "Windows" else "phantomjs"

        # Final expected path: <DRIVER_PATH>/bin/<phantomjs or phantomjs.exe>
        self._bin_path = PHASMA_PATH / "bin" / self.exe_name

        # If the binary doesn't exist, download and set it up
        if not self._bin_path.is_file():
            # Download the driver to the root directory first
            self.download(force=True)

        self.get_exe_access()

    def get_exe_access(self):
        # On non-Windows systems, ensure the file is executable
        if self.system == "Windows":
            return

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
        timeout: Optional[float] = 30,
        check: bool = False,
        ssl: bool = False,
        env: Optional[dict] = None,
        cwd: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """
        Execute PhantomJS with the given arguments.

        Args:
            args: Command line arguments as a string or sequence of strings.
            capture_output: If True, capture stdout and stderr.
            timeout: Timeout in seconds.
            check: If True, raise CalledProcessError on non-zero exit code.
            ssl: If False, set OPENSSL_CONF environment variable to empty string.
            env: Optional environment variables dictionary for subprocess.
            cwd: Optional working directory for subprocess.
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

        # Handle SSL environment
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

    def run(self, *args, **kwargs) -> subprocess.CompletedProcess:
        """Alias for exec."""
        return self.exec(*args, **kwargs)

