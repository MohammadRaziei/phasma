from .driver import Driver
from pathlib import Path
from typing import Optional, Union
import tempfile
import os
import sys


def _run_phantomjs_script(script: str, args=None):
    """Run a PhantomJS script via a temporary file."""
    driver = Driver()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(script)
        temp_file = f.name
    try:
        result = driver.exec(["--ssl-protocol=any", "--ignore-ssl-errors=true", temp_file] + (args or []),
                             capture_output=True)
        return result
    finally:
        os.unlink(temp_file)


def download_driver(os_name: Optional[str] = None, arch: Optional[str] = None) -> bool:
    """
    Download the PhantomJS driver.

    Args:
        os_name: Operating system name (e.g., 'windows', 'linux', 'darwin').
        arch: Architecture ('32bit' or '64bit').

    Returns:
        bool: True if download successful.
    """
    return Driver.download(os_name=os_name, arch=arch)


def render_page(
    page: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    viewport_size: str = "1024x768",
    wait_time: int = 100,
    **kwargs,
) -> str:
    """
    Render an HTML page and return its rendered content.

    Args:
        page: HTML file path or HTML string.
        output: Optional output file path to save rendered content.
        viewport_size: Viewport size (e.g., '1024x768').
        wait_time: Time to wait after page load in milliseconds.
        **kwargs: Additional arguments passed to PhantomJS.

    Returns:
        Rendered HTML as string.
    """
    # Read HTML content
    if isinstance(page, Path) or (isinstance(page, str) and os.path.isfile(page)):
        with open(page, 'r', encoding='utf-8') as f:
            html_content = f.read()
    else:
        html_content = page

    # Create a temporary script for PhantomJS using setContent and evaluate to run JS
    # Escape newlines and quotes for JavaScript string
    escaped = html_content.replace('\\', '\\\\').replace('`', '\\`').replace('\n', '\\n').replace('\r', '\\r').replace('"', '\\"')
    script = f"""
    var page = require('webpage').create();
    page.viewportSize = {{ width: {viewport_size.split('x')[0]}, height: {viewport_size.split('x')[1]} }};
    // Enable JavaScript and other settings
    page.settings.javascriptEnabled = true;
    page.settings.localToRemoteUrlAccess = true;
    page.content = "{escaped}";
    // Give some time for JS to execute
    window.setTimeout(function() {{
        // Evaluate any inline scripts
        var result = page.evaluate(function() {{
            return document.documentElement.outerHTML;
        }});
        console.log(result);
        phantom.exit();
    }}, {wait_time});
    """

    result = _run_phantomjs_script(script)
    rendered = result.stdout.decode().strip() if result.stdout else ""

    if output:
        Path(output).write_text(rendered)

    return rendered


def render_url(
    url: str,
    output: Optional[Union[str, Path]] = None,
    viewport_size: str = "1024x768",
    wait_time: int = 0,
    **kwargs,
) -> str:
    """
    Render a URL and return its rendered content.

    Args:
        url: URL to render.
        output: Optional output file path to save rendered content.
        viewport_size: Viewport size (e.g., '1024x768').
        wait_time: Time to wait after page load in milliseconds.
        **kwargs: Additional arguments passed to PhantomJS.

    Returns:
        Rendered HTML as string.
    """
    script = f"""
    var page = require('webpage').create();
    page.viewportSize = {{ width: {viewport_size.split('x')[0]}, height: {viewport_size.split('x')[1]} }};
    page.open('{url}', function(status) {{
        if (status === 'success') {{
            window.setTimeout(function() {{
                console.log(page.content);
                phantom.exit();
            }}, {wait_time});
        }} else {{
            console.error('Failed to load URL');
            phantom.exit(1);
        }}
    }});
    """

    result = _run_phantomjs_script(script)
    rendered = result.stdout.decode().strip() if result.stdout else ""

    if output:
        Path(output).write_text(rendered)

    return rendered


def execjs(
    script: str,
    args: Optional[list] = None,
    **kwargs,
) -> str:
    """
    Execute JavaScript code in PhantomJS context.

    Args:
        script: JavaScript code to execute.
        args: Optional arguments to pass to the script.
        **kwargs: Additional arguments passed to PhantomJS.

    Returns:
        The output from the script (stdout).
    """
    # Wrap script to capture output and ensure exit
    wrapped = f"""
    var system = require('system');
    var args = system.args;
    (function() {{
        {script}
    }})();
    phantom.exit();
    """
    result = _run_phantomjs_script(wrapped, args)
    return result.stdout.decode().strip() if result.stdout else ""
