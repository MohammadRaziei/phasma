"""Nox configuration for phasma without virtual environments."""

import nox
from pathlib import Path
import sys
import subprocess
import os

# Disable virtual environment creation completely
nox.options.reuse_existing_virtualenvs = True
nox.options.default_venv_backend = None

# Default sessions to run when no session is specified
nox.options.sessions = ["test", "lint", "format"]

# Package directory
PACKAGE_DIR = Path("src/phasma")


def run_command(cmd, cwd=None, env=None):
    """Run a command and print output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    result.check_returncode()
    return result


@nox.session(python=False)
def download(session: nox.Session) -> None:
    """Download the PhantomJS driver."""
    # Use system Python to run the download script
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    run_command([
        sys.executable,
        "-m",
        "phasma.driver.download",
        "--dest",
        str(PACKAGE_DIR / "driver"),
        "--os", "linux",
        "--arch", "64bit",
    ], env=env)


@nox.session(python=False)
def test(session: nox.Session) -> None:
    """Run tests with pytest."""
    # Install test dependencies if needed (optional)
    # run_command([sys.executable, "-m", "pip", "install", "pytest"])
    
    # Run pytest
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    run_command([
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        *session.posargs,
    ], env=env)


@nox.session(python=False)
def lint(session: nox.Session) -> None:
    """Run linting with ruff."""
    # Install ruff if needed (optional)
    # run_command([sys.executable, "-m", "pip", "install", "ruff"])
    
    run_command([
        sys.executable,
        "-m",
        "ruff",
        "check",
        "src",
        "tests",
        "noxfile.py",
    ])


@nox.session(python=False)
def format(session: nox.Session) -> None:
    """Format code with black and ruff."""
    # Install black and ruff if needed (optional)
    # run_command([sys.executable, "-m", "pip", "install", "black", "ruff"])
    
    run_command([
        sys.executable,
        "-m",
        "black",
        "src",
        "tests",
        "noxfile.py",
    ])
    run_command([
        sys.executable,
        "-m",
        "ruff",
        "format",
        "src",
        "tests",
        "noxfile.py",
    ])


@nox.session(python=False)
def build(session: nox.Session) -> None:
    """Build distribution packages (wheel and sdist)."""
    # Install build if needed (optional)
    # run_command([sys.executable, "-m", "pip", "install", "build", "wheel"])
    
    run_command([
        sys.executable,
        "-m",
        "build",
    ])


@nox.session(python=False)
def coverage(session: nox.Session) -> None:
    """Run tests with coverage report."""
    # Install coverage if needed (optional)
    # run_command([sys.executable, "-m", "pip", "install", "coverage"])
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    run_command([
        sys.executable,
        "-m",
        "coverage",
        "run",
        "-m",
        "pytest",
        "tests/",
    ], env=env)
    run_command([sys.executable, "-m", "coverage", "report"])
    run_command([sys.executable, "-m", "coverage", "html"])


@nox.session(python=False)
def clean(session: nox.Session) -> None:
    """Clean up build artifacts and downloaded drivers."""
    # Remove build directories
    for dir_name in ["build", "dist", "*.egg-info", "coverage_html_report"]:
        if Path(dir_name).exists():
            run_command(["rm", "-rf", dir_name])
    
    # Remove downloaded driver files
    driver_dir = PACKAGE_DIR / "driver" / "phantomjs"
    if driver_dir.exists():
        run_command(["rm", "-rf", str(driver_dir)])
    
    # Remove __pycache__ directories
    run_command(["find", ".", "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"])
    run_command(["find", ".", "-type", "f", "-name", "*.pyc", "-delete"])
    run_command(["find", ".", "-type", "f", "-name", "*.pyo", "-delete"])
    run_command(["find", ".", "-type", "f", "-name", "*.pyd", "-delete"])
    run_command(["find", ".", "-type", "f", "-name", ".coverage", "-delete"])


@nox.session(python=False)
def dev(session: nox.Session) -> None:
    """Set up development environment."""
    # Install development dependencies
    run_command([
        sys.executable,
        "-m",
        "pip",
        "install",
        "-e",
        ".[test]",
        "black",
        "ruff",
        "coverage",
        "build",
        "wheel",
    ])


@nox.session(python=False)
def all(session: nox.Session) -> None:
    """Run all checks: lint, format, test, and build."""
    session.notify("lint")
    session.notify("format")
    session.notify("test")
    session.notify("build")
