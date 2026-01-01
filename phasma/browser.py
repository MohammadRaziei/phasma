"""
Playwright-like API for phasma with persistent driver support.
This module provides a modern API similar to Playwright for PhantomJS automation.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .driver import DriverPersistent


def _escape_js_string(s):
    """Escape a string for safe insertion into JavaScript code."""
    if s is None:
        return "null"  # Return JavaScript null literal for None values
    if isinstance(s, Path):
        s = str(s)
    # Escape backslashes, single quotes, double quotes, and newlines
    return s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


class Error(Exception):
    """Base error class for phasma browser errors."""
    pass


class TimeoutError(Error):
    """Exception raised when a timeout occurs."""
    pass


class Page:
    """Represents a single page in the browser."""

    def __init__(self, browser_context, page_id: str):
        self._browser_context = browser_context
        self._driver = browser_context._driver
        self._page_id = page_id
        self._url = None
        self._viewport_size = {"width": 1024, "height": 768}

    async def goto(self, url: str, wait_until: str = "load", timeout: int = 30000) -> Optional[str]:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation succeeded ("load", "domcontentloaded", "networkidle")
            timeout: Maximum time to wait for navigation in milliseconds

        Returns:
            HTML content of the page after navigation
        """
        # Use persistent driver
        content = self._driver.navigate(url, timeout=timeout/1000.0)
        self._url = url
        return content

    def _run_phantomjs_script(self, script: str, args=None):
        """Run a PhantomJS script via a temporary file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(script)
            temp_file = f.name
        try:
            result = self._driver.exec(
                ["--ssl-protocol=any", "--ignore-ssl-errors=true", temp_file] + (args or []),
                capture_output=True,
                timeout=60  # Increase timeout for complex operations
            )
            return result
        finally:
            os.unlink(temp_file)

    async def click(self, selector: str):
        """
        Click an element matching the selector.

        Args:
            selector: CSS selector for the element to click
        """
        # Use persistent driver
        success = self._driver.click(selector, timeout=60.0)
        if not success:
            raise Error(f"Element with selector '{selector}' not found")

    async def fill(self, selector: str, value: str):
        """
        Fill an input field with a value.

        Args:
            selector: CSS selector for the input field
            value: Value to fill in the field
        """
        # Use persistent driver
        success = self._driver.fill(selector, value, timeout=60.0)
        if not success:
            raise Error(f"Element with selector '{selector}' not found")

    async def text_content(self, selector: str) -> str:
        """
        Get the text content of an element.

        Args:
            selector: CSS selector for the element

        Returns:
            Text content of the element
        """
        # Use evaluate to get text content
        expression = f"""
        (function() {{
            var el = document.querySelector('{_escape_js_string(selector)}');
            return el ? el.textContent : null;
        }})()
        """
        result = self._driver.evaluate(expression, timeout=60.0)
        if result is None:
            raise Error(f"Element with selector '{selector}' not found")
        return result

    async def inner_html(self, selector: str) -> str:
        """
        Get the inner HTML of an element.

        Args:
            selector: CSS selector for the element

        Returns:
            Inner HTML of the element
        """
        # Use evaluate to get inner HTML
        expression = f"""
        (function() {{
            var el = document.querySelector('{_escape_js_string(selector)}');
            return el ? el.innerHTML : null;
        }})()
        """
        result = self._driver.evaluate(expression, timeout=60.0)
        if result is None:
            raise Error(f"Element with selector '{selector}' not found")
        return result

    async def screenshot(self, path: Union[str, Path], full_page: bool = False, type: str = "png", quality: int = 100) -> bytes:
        """
        Take a screenshot of the page.

        Args:
            path: Path to save the screenshot
            full_page: Whether to take a screenshot of the full page
            type: Image format ('png', 'jpg', 'jpeg', 'pdf')
            quality: Image quality (for JPEG, 1-100)

        Returns:
            Screenshot as bytes
        """
        path = Path(path)

        # Use persistent driver
        self._driver.take_screenshot(path, timeout=60.0)
        # Read the saved image file and return as bytes
        with open(path, "rb") as f:
            return f.read()

    async def pdf(self, path: Union[str, Path],
                  format: str = "A4",
                  landscape: bool = False,
                  margin: Union[str, Dict[str, str]] = "1cm") -> bytes:
        """
        Generate a PDF of the page.

        Args:
            path: Path to save the PDF
            format: Page format ('A3', 'A4', 'A5', 'Letter', 'Legal', etc.)
            landscape: Whether to use landscape orientation
            margin: Page margins (string like '1cm' or dict with 'top', 'bottom', 'left', 'right')

        Returns:
            PDF as bytes
        """
        path = Path(path)

        # Handle margin parameter
        if isinstance(margin, str):
            margin_obj = {"top": margin, "bottom": margin, "left": margin, "right": margin}
        else:
            margin_obj = margin

        # Create a temporary script to generate PDF
        script = f"""
        var page = require('webpage').create();
        page.viewportSize = {{ width: {self._viewport_size['width']}, height: {self._viewport_size['height']} }};
        page.paperSize = {{
            format: '{format}',
            orientation: '{'landscape' if landscape else 'portrait'}',
            margin: {json.dumps(margin_obj)}
        }};
        page.settings.javascriptEnabled = true;
        page.settings.localToRemoteUrlAccess = true;

        page.open('{self._url}', function(status) {{
            if (status === 'success') {{
                window.setTimeout(function() {{
                    page.render('{_escape_js_string(path)}', {{ format: 'pdf' }});
                    console.log('PDF saved');
                    phantom.exit();
                }}, 100);
            }} else {{
                console.error('Failed to load URL');
                phantom.exit(1);
            }}
        }});
        """

        result = self._run_phantomjs_script(script)
        if result.returncode != 0:
            error_msg = result.stderr.decode().strip() if result.stderr else "Unknown error"
            raise Error(f"PDF generation failed: {error_msg}")

        # Read the saved PDF file and return as bytes
        with open(path, "rb") as f:
            return f.read()

    async def eval_on_selector(self, selector: str, expression: str) -> Any:
        """
        Execute a JavaScript expression on the first element matching the selector.

        Args:
            selector: CSS selector for the element
            expression: JavaScript expression to evaluate

        Returns:
            Result of the JavaScript expression
        """
        # Use evaluate to execute expression on selector
        full_expression = f"""
        (function() {{
            var el = document.querySelector('{_escape_js_string(selector)}');
            if (el) {{
                return (function(){{ return {expression}; }}).call(el);
            }}
            return null;
        }})()
        """
        result = self._driver.evaluate(full_expression, timeout=60.0)
        if result is None:
            raise Error(f"Element with selector '{selector}' not found")
        return result

    async def evaluate(self, expression: str) -> Any:
        """
        Execute a JavaScript expression in the page context.

        Args:
            expression: JavaScript expression to evaluate

        Returns:
            Result of the JavaScript expression
        """
        return self._driver.evaluate(expression, timeout=60.0)

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> Optional["ElementHandle"]:
        """
        Wait for an element matching the selector to appear in the DOM.

        Args:
            selector: CSS selector to wait for
            timeout: Maximum time to wait in milliseconds

        Returns:
            ElementHandle if found, None otherwise
        """
        # Use evaluate to check if element exists
        expression = f"""
        (function() {{
            return document.querySelector('{_escape_js_string(selector)}') !== null;
        }})()
        """
        exists = self._driver.evaluate(expression, timeout=60.0)
        if exists:
            # Return a simple element handle
            return ElementHandle(self, selector)
        else:
            return None

    async def set_viewport_size(self, width: int, height: int):
        """
        Set the viewport size.

        Args:
            width: Width in pixels
            height: Height in pixels
        """
        self._viewport_size = {"width": width, "height": height}


class ElementHandle:
    """Represents an element handle in the page."""

    def __init__(self, page: Page, selector: str):
        self._page = page
        self._selector = selector

    async def click(self):
        """Click the element."""
        await self._page.click(self._selector)

    async def fill(self, value: str):
        """Fill the element with a value."""
        # This is a simplified implementation - in a real implementation,
        # we'd need to check if the element is an input field
        await self._page.fill(self._selector, value)

    async def text_content(self) -> str:
        """Get the text content of the element."""
        return await self._page.text_content(self._selector)

    async def inner_html(self) -> str:
        """Get the inner HTML of the element."""
        return await self._page.inner_html(self._selector)


class BrowserContext:
    """Represents a browser context (session)."""

    def __init__(self, browser, context_id: str, options: Optional[Dict] = None):
        self._browser = browser
        self._driver = browser._driver
        self._context_id = context_id
        self._options = options or {}
        self._pages = []

    async def new_page(self) -> Page:
        """Create a new page in this context."""
        page_id = f"page_{len(self._pages)}"
        page = Page(self, page_id)
        self._pages.append(page)
        return page

    async def close(self):
        """Close the browser context."""
        # In PhantomJS, contexts are not separate processes, so we just clear pages
        self._pages.clear()


class Browser:
    """Represents a browser instance."""

    def __init__(self, driver: DriverPersistent, browser_id: str, options: Optional[Dict] = None):
        self._driver = driver
        self._browser_id = browser_id
        self._options = options or {}
        self._contexts = []
        self._is_closed = False

    async def new_context(self, options: Optional[Dict] = None) -> BrowserContext:
        """Create a new browser context."""
        context_id = f"context_{len(self._contexts)}"
        context = BrowserContext(self, context_id, options or self._options)
        self._contexts.append(context)
        return context

    async def new_page(self) -> Page:
        """Create a new page in the default context."""
        context = await self.new_context()
        return await context.new_page()

    async def close(self):
        """Close the browser."""
        for context in self._contexts:
            await context.close()
        self._contexts.clear()
        
        # If using persistent driver, close it properly
        if hasattr(self._driver, 'close'):
            self._driver.close()
        
        self._is_closed = True

    def is_connected(self) -> bool:
        """Check if the browser is connected."""
        return not self._is_closed


async def launch(options: Optional[Dict] = None) -> Browser:
    """
    Launch a new browser instance.

    Args:
        options: Browser launch options

    Returns:
        Browser instance
    """
    driver = DriverPersistent()
    # Start the persistent session
    driver.start_persistent_session()

    browser_id = "browser_1"  # Simple ID for now
    browser = Browser(driver, browser_id, options)
    return browser


async def connect(options: Optional[Dict] = None) -> Browser:
    """
    Connect to an existing browser instance.
    For PhantomJS, this is similar to launch since it doesn't maintain persistent processes.

    Args:
        options: Browser connection options

    Returns:
        Browser instance
    """
    return await launch(options)