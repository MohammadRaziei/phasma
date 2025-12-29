# Phasma – Modern PhantomJS Browser Automation for Python

<div align="center">
<img src="https://github.com/MohammadRaziei/phasma/raw/master/docs/images/phasma.jpg" width="30%" style="min-width: 200px;" alt="Phasma Logo" />
</div>

**Phasma** is a modern Python library that provides a Playwright-like API for PhantomJS browser automation. It combines the power of PhantomJS with a familiar, intuitive interface similar to Playwright, making it ideal for web scraping, automated testing, screenshot capture, and PDF generation.

## Key Features

### 🚀 Playwright-like API
- **Familiar Interface**: Uses the same patterns as Playwright (`launch`, `Browser`, `Page`, `ElementHandle`)
- **Async Support**: Full async/await support for efficient concurrent operations
- **Modern Design**: Clean, intuitive API that follows current best practices

### 🌐 Browser Automation
- **Page Navigation**: Navigate to URLs with `page.goto()`
- **Element Interaction**: Click, fill, and interact with page elements
- **JavaScript Execution**: Run JavaScript in the page context
- **Content Extraction**: Extract text, HTML, and other content from pages

### 📸 Media Generation
- **Screenshots**: Capture page screenshots in PNG, JPG, and other formats
- **PDF Generation**: Generate PDFs with customizable formatting options
- **High Quality**: Full control over viewport size, quality, and formatting

### 🛠️ Developer Experience
- **Automatic Driver Management**: PhantomJS driver downloaded and managed automatically
- **Cross-Platform**: Works seamlessly on Windows, Linux, and macOS
- **Zero Configuration**: No setup required - just install and use
- **CLI Interface**: Command-line tools for quick operations

### 📋 Technical Specifications
- **Python 3.4+**: Compatible with modern Python versions
- **Lightweight**: Minimal dependencies and fast installation
- **Reliable**: Comprehensive test suite and error handling
- **Secure**: SSL control and environment isolation options

## Installation

Install the latest version from PyPI:

```bash
pip install phasma
```

### System Requirements
- **Python**: 3.4 or higher
- **OS**: Windows, Linux, or macOS (32-bit and 64-bit supported)
- **Memory**: Minimal memory footprint
- **Storage**: ~50MB for PhantomJS driver (downloaded automatically)

The package includes the PhantomJS driver for all supported platforms. No separate download is required - the driver is automatically downloaded and managed when needed.

### From Source
For development or latest features:

```bash
git clone https://github.com/MohammadRaziei/phasma.git
cd phasma
pip install -e .
```

## Quick Start

Getting started with Phasma is simple. The library provides a Playwright-like API that's familiar to modern web automation developers.

### Basic Browser Automation

```python
import asyncio
from phasma import launch

async def main():
    # Launch a browser instance (PhantomJS driver auto-downloaded)
    browser = await launch()

    try:
        # Create a new page
        page = await browser.new_page()

        # Navigate to a website
        await page.goto("https://example.com")

        # Extract content from the page
        title = await page.text_content("h1")
        print(f"Main heading: {title}")

        # Execute JavaScript in the page context
        page_title = await page.evaluate("document.title")
        print(f"Page title: {page_title}")

        # Take a screenshot
        await page.screenshot(path="example.png")

        # Generate a PDF
        await page.pdf(path="example.pdf")

    finally:
        # Always close the browser to free resources
        await browser.close()

# Run the async function
asyncio.run(main())
```

### Advanced Usage Example

```python
import asyncio
from phasma import launch

async def advanced_example():
    browser = await launch()

    try:
        page = await browser.new_page()

        # Set custom viewport size
        await page.set_viewport_size(1920, 1080)

        # Navigate and wait for content
        await page.goto("https://example.com")

        # Wait for specific elements
        await page.wait_for_selector("h1", timeout=5000)

        # Interact with elements
        heading = await page.text_content("h1")
        print(f"Found heading: {heading}")

        # Take a high-quality screenshot
        await page.screenshot(
            path="full_page.png",
            type="png",
            quality=100
        )

        # Generate a customized PDF
        await page.pdf(
            path="document.pdf",
            format="A4",
            landscape=False,
            margin="1cm"
        )

    finally:
        await browser.close()

asyncio.run(advanced_example())
```

### Command Line Interface

Phasma also provides a powerful command-line interface for quick operations:

```bash
# Show PhantomJS driver information
python -m phasma driver --version    # Display driver version
python -m phasma driver --path       # Show driver executable path

# Download and manage the driver
python -m phasma driver download                    # Download driver
python -m phasma driver download --force           # Force re-download

# Execute PhantomJS directly with custom arguments
python -m phasma driver exec script.js
python -m phasma driver exec --cwd /path/to/dir script.js
python -m phasma driver exec --ssl --timeout 10 script.js
python -m phasma driver exec --no-ssl --capture-output script.js

# Render HTML content
python -m phasma render-page /path/to/file.html
python -m phasma render-page "<html><body>Hello</body></html>"
python -m phasma render-page file.html --output output.html --viewport 1920x1080 --wait 1000

# Render URLs
python -m phasma render-url https://example.com
python -m phasma render-url https://example.com --output page.html --wait 2000

# Execute JavaScript
python -m phasma execjs "console.log('Hello from PhantomJS');"
python -m phasma execjs "document.title" --arg value1 --arg value2
```

## API Reference

### Core Functions

#### `launch(options=None)`
Launches a new browser instance with automatic driver management.

- **Parameters**: `options` (dict, optional) - Browser launch options
- **Returns**: `Browser` object
- **Example**: `browser = await launch()`

#### `connect(options=None)`
Connects to an existing browser instance (PhantomJS implementation similar to launch).

- **Parameters**: `options` (dict, optional) - Connection options
- **Returns**: `Browser` object

#### `download_driver(os_name=None, arch=None, force=False)`
Downloads the PhantomJS driver for the specified platform.

- **Parameters**:
  - `os_name` (str, optional) - Operating system ('windows', 'linux', 'darwin')
  - `arch` (str, optional) - Architecture ('32bit', '64bit')
  - `force` (bool) - Force re-download if driver exists
- **Returns**: `bool` - Success status

### Browser Classes

#### `Browser`
Represents a browser instance with full lifecycle management.

- **Methods**:
  - `new_page()` → `Page`: Create a new page
  - `new_context()` → `BrowserContext`: Create a new context
  - `close()`: Close the browser
  - `is_connected()` → `bool`: Check connection status

#### `BrowserContext`
Manages a browser context/session.

- **Methods**:
  - `new_page()` → `Page`: Create a new page in this context
  - `close()`: Close the context

#### `Page`
Represents a single web page with comprehensive automation capabilities.

- **Navigation**:
  - `goto(url, wait_until="load", timeout=30000)` → `str`: Navigate to URL
  - `set_viewport_size(width, height)`: Set viewport dimensions

- **Content Extraction**:
  - `text_content(selector)` → `str`: Get element text content
  - `inner_html(selector)` → `str`: Get element inner HTML
  - `evaluate(expression)` → `Any`: Execute JavaScript expression

- **Element Interaction**:
  - `click(selector)`: Click an element
  - `fill(selector, value)`: Fill input field
  - `wait_for_selector(selector, timeout=30000)` → `ElementHandle`: Wait for element

- **Media Generation**:
  - `screenshot(path, type="png", quality=100)` → `bytes`: Take screenshot
  - `pdf(path, format="A4", landscape=False, margin="1cm")` → `bytes`: Generate PDF

#### `ElementHandle`
Represents a specific DOM element with interaction methods.

- **Methods**:
  - `click()`: Click the element
  - `fill(value)`: Fill the element (if input)
  - `text_content()` → `str`: Get text content
  - `inner_html()` → `str`: Get inner HTML

### Error Handling

- `Error`: Base error class for all Phasma errors
- `TimeoutError`: Raised when operations exceed timeout limits

## Advanced Usage

### Rendering Dynamic JavaScript Content

Phasma can render pages that modify their DOM with JavaScript:

```python
import asyncio
from phasma import launch

async def render_dynamic_content():
    browser = await launch()
    try:
        page = await browser.new_page()

        # Create HTML with JavaScript
        html_with_js = '''
        <html>
        <body>
            <div id="container">Initial</div>
            <script>
                document.getElementById('container').innerHTML = '<h2>Generated by JS</h2>';
            </script>
        </body>
        </html>
        '''

        # For HTML strings, you'd need to serve them via a local file or server
        # Here's how you'd work with a URL that has dynamic content
        await page.goto("https://example.com")  # Replace with your URL

        # Wait for dynamic content to load
        await page.wait_for_selector("#container", timeout=5000)

        # Get the updated content
        content = await page.inner_html("#container")
        print(content)

    finally:
        await browser.close()

# Run the async function
import asyncio
asyncio.run(render_dynamic_content())
```

### Custom Viewport and Screenshots

```python
import asyncio
from phasma import launch

async def custom_viewport_example():
    browser = await launch()
    try:
        page = await browser.new_page()

        # Set custom viewport size
        await page.set_viewport_size(1920, 1080)

        # Navigate to a page
        await page.goto("https://example.com")

        # Take a screenshot
        await page.screenshot(path="screenshot.png")

        # Generate a PDF
        await page.pdf(path="page.pdf", format="A4", landscape=True)

    finally:
        await browser.close()

# Run the async function
asyncio.run(custom_viewport_example())
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
