import os
import stat
from pathlib import Path

import pytest

from phasma.driver import Driver


class TestDriver:
    """Simple test suite for the Driver class without mocking."""

    def test_driver_initialization(self):
        """Test that Driver can be initialized without errors."""
        driver = Driver()
        assert driver is not None
        assert isinstance(driver, Driver)

    def test_bin_path_exists(self):
        """Test that bin_path points to an existing file."""
        driver = Driver()
        bin_path = driver.bin_path

        assert isinstance(bin_path, Path)
        assert bin_path.exists(), f"Binary file does not exist: {bin_path}"

    def test_bin_file_is_executable(self):
        """Test that the binary file is executable (on non-Windows systems)."""
        import platform

        driver = Driver()
        bin_path = driver.bin_path

        # Skip executable check on Windows
        if platform.system() == "Windows":
            pytest.skip("Executable permission check not applicable on Windows")

        # Check if file is executable
        assert os.access(bin_path, os.X_OK), f"Binary file is not executable: {bin_path}"

        # Also check file mode
        mode = bin_path.stat().st_mode
        assert mode & stat.S_IEXEC, f"Binary file does not have execute permission: {bin_path} (mode: {oct(mode)})"

    def test_examples_path_exists(self):
        """Test that examples_path points to an existing directory."""
        driver = Driver()
        examples_path = driver.examples_path

        assert isinstance(examples_path, Path)
        assert examples_path.exists(), f"Examples directory does not exist: {examples_path}"
        assert examples_path.is_dir(), f"Examples path is not a directory: {examples_path}"

    def test_examples_list_not_empty(self):
        """Test that examples_list is not empty."""
        driver = Driver()
        examples_list = driver.examples_list

        assert isinstance(examples_list, list)
        assert len(examples_list) > 0, "Examples list should not be empty"

        # Check that all items in the list are Path objects
        for example in examples_list:
            assert isinstance(example, Path)

    def test_version_is_string(self):
        """Test that version property returns a string."""
        driver = Driver()
        version = driver.version

        assert isinstance(version, str)
        assert len(version) > 0
        # Version should be in format like "2.1.1"
        assert "." in version, f"Version should contain dots: {version}"

    def test_platform_specific_executable_name(self):
        """Test that executable name is correct for the current platform."""
        import platform

        driver = Driver()
        bin_path = driver.bin_path

        system = platform.system()
        if system == "Windows":
            assert bin_path.name == "phantomjs.exe"
        else:
            assert bin_path.name == "phantomjs"

    def test_exec_method(self):
        """Test that exec method runs phantomjs and returns output."""
        driver = Driver()

        # Run phantomjs --version which should output version string
        result = driver.exec(["--version"], capture_output=True)

        # Check that process completed successfully
        assert result.returncode == 0
        assert result.stdout is not None
        # Version output should contain numbers and dots
        assert any(char.isdigit() for char in result.stdout.decode())

        # Test with string argument
        result2 = driver.exec("--version", capture_output=True)
        assert result2.returncode == 0

        # Test alias run method
        result3 = driver.run("--version", capture_output=True)
        assert result3.returncode == 0
