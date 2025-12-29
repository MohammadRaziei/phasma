# Phasma – Modern PhantomJS Driver for Python

<div align="center">
<img src="https://github.com/MohammadRaziei/phasma/raw/master/docs/images/phasma.jpg" width="30%" style="min-width: 200px;" alt="Phasma Logo" />
</div>

**Phasma** is a Python library that provides a clean, high‑level interface to PhantomJS, enabling headless browser automation, web page rendering, and JavaScript execution. It simplifies the process of downloading, managing, and interacting with PhantomJS, making it ideal for web scraping, screenshot capture, and automated testing.

## Features

- **Bundled Driver**: PhantomJS driver is included in the package (Windows, macOS, Linux). No separate download needed.
- **Page Rendering**: Render HTML files, strings, and remote URLs with JavaScript support.
- **JavaScript Execution**: Run arbitrary JavaScript code in a PhantomJS context.
- **Direct PhantomJS Execution**: Execute PhantomJS with full control over arguments, environment, and working directory.
- **SSL Control**: Disable SSL verification by setting `OPENSSL_CONF` environment variable.
- **CLI Interface**: Command‑line tools for quick operations.
- **Cross‑Platform**: Works on Windows, Linux, and macOS.
- **Lightweight**: Minimal dependencies, focused on simplicity and reliability.

## Installation

Install from PyPI:

```bash
pip install phasma
```

The package includes the PhantomJS driver for Windows, macOS, and Linux (both 32‑bit and 64‑bit). No separate download is required.

Or install from source:

```bash
git clone https://github.com/MohammadRaziei/phantomjs-driver.git
cd phantomjs-driver
pip install -e .
```

## Quick Start

### Using the Playwright-like API

Phasma provides a modern, async interface similar to Playwright:

```python
import asyncio
from phasma import launch

async def main():
    # Download and launch a browser instance (PhantomJS)
    # The driver will be downloaded automatically if not present
    browser = await launch()

    try:
        # Create a new page
        page = await browser.new_page()

        # Navigate to a URL
        await page.goto("https://example.com")

        # Get text content of elements
        title = await page.text_content("h1")
        print(f"Main title: {title}")

        # Execute JavaScript
        page_title = await page.evaluate("document.title")
        print(f"Page title: {page_title}")

        # Take screenshots
        await page.screenshot(path="screenshot.png")

        # Generate PDFs
        await page.pdf(path="page.pdf")

    finally:
        # Close the browser
        await browser.close()

# Run the async function
asyncio.run(main())
```

### Using the Command Line

```bash
# Show driver version
python -m phasma driver --version

# Show driver executable path
python -m phasma driver --path

# Download the driver (use --force to re-download)
python -m phasma driver download
python -m phasma driver download --force

# Execute PhantomJS directly with arguments
python -m phasma driver exec script.js
python -m phasma driver exec --cwd /path/to/working/dir script.js
python -m phasma driver exec --ssl --timeout 10 script.js
python -m phasma driver exec --no-ssl --capture-output script.js

# Render an HTML file
python -m phasma render-page tests/data/test_page.html

# Render a URL
python -m phasma render-url https://example.com --wait 2000

# Execute JavaScript
python -m phasma execjs "console.log('Hello');"
```

## API Reference

### `download_driver(os_name=None, arch=None, force=False)`
Downloads the PhantomJS driver for the given OS and architecture. If no arguments are provided, it auto‑detects the current platform. Set `force=True` to re‑download even if the driver already exists.

### `Driver.exec(args, *, capture_output=False, timeout=30, check=False, ssl=False, env=None, cwd=None, **kwargs)`
Executes PhantomJS with the given arguments. Returns a `subprocess.CompletedProcess` instance.

- `args`: Command line arguments as a string or sequence of strings.
- `capture_output`: If `True`, capture stdout and stderr.
- `timeout`: Timeout in seconds.
- `check`: If `True`, raise `CalledProcessError` on non‑zero exit code.
- `ssl`: If `False` (default), set `OPENSSL_CONF` environment variable to empty string (disables SSL verification).
- `env`: Optional environment variables dictionary for subprocess.
- `cwd`: Optional working directory for subprocess.

### `render_page(page, output=None, viewport_size="1024x768", wait_time=100, **kwargs)`
Renders an HTML page (file path or HTML string) and returns the rendered HTML. Optionally saves the output to a file.

### `render_url(url, output=None, viewport_size="1024x768", wait_time=0, **kwargs)`
Renders a remote URL and returns the rendered HTML. Optionally saves the output to a file.

### `execjs(script, args=None, **kwargs)`
Executes JavaScript code in a PhantomJS context and returns the stdout.

## Advanced Usage

### Rendering Dynamic JavaScript Content

Phasma can render pages that modify their DOM with JavaScript:

```python
from phasma import render_page

html_with_js = """
<html>
<body>
    <div id="container">Initial</div>
    <script>
        document.getElementById('container').innerHTML = '<h2>Generated by JS</h2>';
    </script>
</body>
</html>
"""

rendered = render_page(html_with_js, wait_time=500)
assert "<h2>Generated by JS</h2>" in rendered
```

### Custom Viewport and Wait Time

```python
# Render with a custom viewport and longer wait
rendered = render_page(
    "page.html",
    viewport_size="1920x1080",
    wait_time=2000,
    output="screenshot.html"
)
```

## Testing

Run the test suite with pytest:

```bash
pytest tests/
```

All core functionality is covered by unit tests, including page rendering, URL fetching, and JavaScript execution.


## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and add tests.
4. Ensure all tests pass.
5. Submit a pull request.

## License

Phasma is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PhantomJS team for the amazing headless browser.
- The Python community for excellent tooling and support.

---

**Phasma** – Making PhantomJS easy for Python developers.
