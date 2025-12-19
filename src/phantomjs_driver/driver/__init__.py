import os
import platform
from pathlib import Path
import stat
from typing import List

from .download import download_driver, DRIVER_PATH, DRIVER_VERSION

PHANTOMJS_DRIVER_PATH = DRIVER_PATH / "phantomjs"


class Driver:
    """
    Manages the PhantomJS executable path in an OS-aware manner.
    - Always expects the binary inside a `bin/` subdirectory.
    - Uses `phantomjs.exe` on Windows and `phantomjs` on Unix-like systems.
    - Ensures the binary is executable (applies chmod +x on non-Windows).
    - Downloads the driver automatically if not present.
    """

    def __init__(self):
        # Determine the correct executable name based on the OS
        system = platform.system()
        exe_name = "phantomjs.exe" if system == "Windows" else "phantomjs"

        # Final expected path: <DRIVER_PATH>/bin/<phantomjs or phantomjs.exe>
        self._bin_path = PHANTOMJS_DRIVER_PATH / "bin" / exe_name

        # If the binary doesn't exist, download and set it up
        if not self._bin_path.is_file():
            # Download the driver to the root directory first
            download_driver(dest=DRIVER_PATH)


        # On non-Windows systems, ensure the file is executable
        if system != "Windows":
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
        return PHANTOMJS_DRIVER_PATH / "examples"
    

    @property
    def examples_list(self) -> List:
        return list(self.examples_path.iterdir())

    
    @property
    def version(self) -> str:
        return DRIVER_VERSION