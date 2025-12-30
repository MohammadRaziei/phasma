"""Nox configuration for phasma without virtual environments."""

import os
import subprocess
import sys
from pathlib import Path

import nox

# Disable virtual environment creation completely
nox.options.reuse_existing_virtualenvs = True
nox.options.default_venv_backend = None

# Default sessions to run when no session is specified
nox.options.sessions = ["test", "lint", "format"]

# Package directory
PACKAGE_DIR = Path(__file__).parent / "phasma"


def run_command(cmd, cwd=None, env=None):
    """Run a command and print output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)
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
    import shutil

    def remove_path(path: Path) -> None:
        """Remove a file or directory if it exists."""
        if not path.exists():
            return
        print(f"Removing {path}")
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)

    def remove_glob(pattern: str) -> None:
        """Remove all files/directories matching a glob pattern."""
        for path in Path(".").glob(pattern):
            remove_path(path)

    def remove_rglob(pattern: str) -> None:
        """Remove all files/directories matching a recursive glob pattern."""
        for path in Path(".").rglob(pattern):
            remove_path(path)

    # Remove build directories
    for dir_name in ["build", "dist", "coverage_html_report"]:
        remove_path(Path(dir_name))

    # Remove *.egg-info directories
    remove_glob("*.egg-info")

    # Remove downloaded driver files
    driver_dir = PACKAGE_DIR / "driver" / "phantomjs"
    # remove_path(driver_dir)

    # Remove __pycache__ directories
    for dir_name in ["__pycache__", ".pytest_cache", ".ruff_cache"]:
        remove_rglob(dir_name)

    # Remove compiled Python files
    for pattern in ["*.pyc", "*.pyo", "*.pyd", ".coverage"]:
        remove_rglob(pattern)


@nox.session(python=False)
def dev(session: nox.Session) -> None:
    """Set up development environment."""
    # Install development dependencies
    run_command([
        sys.executable, "-m","pip","install",
        "-e", ".[test]",
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
