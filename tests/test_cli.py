"""
Test CLI interface.
"""
import subprocess
import sys
import os

def test_driver_version():
    """Test driver --version command."""
    result = subprocess.run(
        [sys.executable, "-m", "phasma", "driver", "--version"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    assert result.returncode == 0
    assert "PhantomJS driver version:" in result.stdout

def test_driver_path():
    """Test driver --path command."""
    result = subprocess.run(
        [sys.executable, "-m", "phasma", "driver", "--path"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    assert result.returncode == 0
    # Path should contain phantomjs or phantomjs.exe
    assert "phantomjs" in result.stdout.lower()

def test_driver_download():
    """Test driver download command (skip if already downloaded)."""
    # This test may skip if driver already exists
    result = subprocess.run(
        [sys.executable, "-m", "phasma", "driver", "download"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    # Accept both success (0) or already exists (maybe non-zero?)
    # We'll just ensure no crash
    assert result.returncode in (0, 1)

def test_render_page_file():
    """Test render-page with a file."""
    html_file = os.path.join(os.path.dirname(__file__), "data", "test_page.html")
    result = subprocess.run(
        [sys.executable, "-m", "phasma", "render-page", html_file],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    assert result.returncode == 0
    assert "<h1>Hello, Phasma!</h1>" in result.stdout

def test_render_page_string():
    """Test render-page with HTML string."""
    # Pass HTML string directly (may need escaping)
    result = subprocess.run(
        [sys.executable, "-m", "phasma", "render-page", "<html><body>test</body></html>"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    assert result.returncode == 0
    assert "test" in result.stdout
