"""
Main phasma module containing utility functions for rendering and processing web content.
"""
import asyncio
import tempfile
from pathlib import Path

import phasma.browser


async def render_page_content(input_content, output_path=None, viewport="1024x768", wait=100):
    """
    Render HTML content using PhantomJS.
    
    Args:
        input_content: Either a file path or HTML string to render
        output_path: Optional output file path (if None, returns content as string)
        viewport: Viewport size as WIDTHxHEIGHT (default: 1024x768)
        wait: Wait time in milliseconds after page load (default: 100)
    
    Returns:
        Rendered content as string if no output_path provided, otherwise None
    """
    browser = await phasma.browser.launch()
    try:
        page = await browser.new_page()

        # Set viewport size
        width, height = map(int, viewport.split("x"))
        await page.set_viewport_size(width, height)

        # Read HTML content - check if input_content is a valid file path
        # Only treat as file if it looks like a file path and exists
        is_potential_file_path = (
            len(input_content) < 1000  # Reasonable length for a file path
            and (input_content.startswith('.') or '/' in input_content or '\\' in input_content)
            and not input_content.strip().startswith('<')  # Doesn't look like HTML
        )

        if is_potential_file_path:
            try:
                input_path = Path(input_content)
                if input_path.is_file():
                    html_content = input_path.read_text(encoding="utf-8")
                else:
                    html_content = input_content  # Not an existing file, treat as HTML
            except OSError:
                # If Path construction fails, treat as HTML content
                html_content = input_content
        else:
            # Treat as HTML content string
            html_content = input_content

        # Create a temporary HTML file with the content and navigate to it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(html_content)
            temp_html_path = temp_file.name

        try:
            # Navigate to the temporary HTML file
            temp_html_url = Path(temp_html_path).as_uri()
            await page.goto(temp_html_url)

            # Wait for the specified time
            await asyncio.sleep(wait / 1000.0)  # Convert milliseconds to seconds

            # Get the rendered content
            rendered = await page.evaluate("document.documentElement.outerHTML")
            if not output_path:
                return rendered
            else:
                Path(output_path).write_text(rendered, encoding="utf-8")

        finally:
            # Clean up the temporary file
            if Path(temp_html_path).exists():
                Path(temp_html_path).unlink()

    finally:
        await browser.close()


async def render_url_content(url, output_path=None, viewport="1024x768", wait=0):
    """
    Render a URL using PhantomJS.
    
    Args:
        url: URL to render
        output_path: Optional output file path (if None, returns content as string)
        viewport: Viewport size as WIDTHxHEIGHT (default: 1024x768)
        wait: Wait time in milliseconds after page load (default: 0)
    
    Returns:
        Rendered content as string if no output_path provided, otherwise None
    """
    browser = await phasma.browser.launch()
    try:
        page = await browser.new_page()

        # Set viewport size
        width, height = map(int, viewport.split("x"))
        await page.set_viewport_size(width, height)

        # Navigate to URL
        await page.goto(url)
        # Wait for the specified time
        await asyncio.sleep(wait / 1000.0)  # Convert milliseconds to seconds

        # Get the rendered content
        rendered = await page.evaluate("document.documentElement.outerHTML")
        if not output_path:
            return rendered
        else:
            Path(output_path).write_text(rendered, encoding="utf-8")

    finally:
        await browser.close()


async def execute_js_script(script, url="about:blank"):
    """
    Execute JavaScript code in a PhantomJS context.

    Args:
        script: JavaScript code to execute (without 'return' keyword)
        url: URL to load before executing script (default: about:blank)

    Returns:
        Result of the JavaScript execution
    """
    browser = await phasma.browser.launch()
    try:
        page = await browser.new_page()

        # Navigate to the specified URL
        await page.goto(url)

        # Execute the JavaScript code
        result = await page.evaluate(script)
        return result

    finally:
        await browser.close()


async def take_screenshot(url, output_path, viewport="1024x768", wait=100):
    """
    Take a screenshot of a webpage.
    
    Args:
        url: URL to take screenshot of
        output_path: Output file path for the screenshot
        viewport: Viewport size as WIDTHxHEIGHT (default: 1024x768)
        wait: Wait time in milliseconds after page load (default: 100)
    """
    browser = await phasma.browser.launch()
    try:
        page = await browser.new_page()

        # Set viewport size
        width, height = map(int, viewport.split("x"))
        await page.set_viewport_size(width, height)

        # Navigate to URL
        await page.goto(url)
        # Wait for the specified time
        await asyncio.sleep(wait / 1000.0)  # Convert milliseconds to seconds

        # Take screenshot
        await page.screenshot(path=output_path)

    finally:
        await browser.close()


async def generate_pdf(url, output_path, format="A4", landscape=False, margin="1cm", viewport="1024x768", wait=100):
    """
    Generate a PDF from a webpage.
    
    Args:
        url: URL to generate PDF from
        output_path: Output file path for the PDF
        format: PDF format (A3, A4, A5, Letter, Legal, etc.)
        landscape: Whether to use landscape orientation
        margin: Page margin (default: 1cm)
        viewport: Viewport size as WIDTHxHEIGHT (default: 1024x768)
        wait: Wait time in milliseconds after page load (default: 100)
    """
    browser = await phasma.browser.launch()
    try:
        page = await browser.new_page()

        # Set viewport size
        width, height = map(int, viewport.split("x"))
        await page.set_viewport_size(width, height)

        # Navigate to URL
        await page.goto(url)
        # Wait for the specified time
        await asyncio.sleep(wait / 1000.0)  # Convert milliseconds to seconds

        # Generate PDF with specified options
        await page.pdf(
            path=output_path,
            format=format,
            landscape=landscape,
            margin=margin
        )

    finally:
        await browser.close()


def sync_render_page_content(input_content, output_path=None, viewport="1024x768", wait=100):
    """Synchronous wrapper for render_page_content."""
    return asyncio.run(render_page_content(input_content, output_path, viewport, wait))


def sync_render_url_content(url, output_path=None, viewport="1024x768", wait=0):
    """Synchronous wrapper for render_url_content."""
    return asyncio.run(render_url_content(url, output_path, viewport, wait))


def sync_execute_js_script(script, url="about:blank"):
    """Synchronous wrapper for execute_js_script."""
    return asyncio.run(execute_js_script(script, url))


def sync_take_screenshot(url, output_path, viewport="1024x768", wait=100):
    """Synchronous wrapper for take_screenshot."""
    asyncio.run(take_screenshot(url, output_path, viewport, wait))


def sync_generate_pdf(url, output_path, format="A4", landscape=False, margin="1cm", viewport="1024x768", wait=100):
    """Synchronous wrapper for generate_pdf."""
    asyncio.run(generate_pdf(url, output_path, format, landscape, margin, viewport, wait))
