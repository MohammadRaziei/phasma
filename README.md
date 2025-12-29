# Phasma – Modern PhantomJS Browser Automation for Python

<div align="center">
<img src="https://github.com/MohammadRaziei/phasma/raw/master/docs/images/phasma.jpg" width="30%" style="min-width: 200px;" alt="Phasma Logo" />
</div>

**Phasma** is a modern Python library that provides a Playwright-like API for PhantomJS browser automation. Unlike other tools, Phasma requires **no external dependencies** - no need to install browsers, Node.js, npm, or browser drivers like Chrome or Firefox. It includes a bundled PhantomJS engine and provides a familiar Playwright-like interface, making it ideal for executing JavaScript that manipulates the DOM, web scraping, automated testing, screenshot capture, and PDF generation.

## Key Features

### 🚀 Playwright-like API
- **Familiar Interface**: Uses the same patterns as Playwright (`launch`, `Browser`, `Page`, `ElementHandle`)
- **Async Support**: Full async/await support for efficient concurrent operations
- **Modern Design**: Clean, intuitive API that follows current best practices

### 🌐 Browser Automation & Media Generation
- **Page Navigation**: Navigate to URLs with `page.goto()`, extract content with `text_content()`, `inner_html()`
- **Element Interaction**: Click, fill, and interact with page elements
- **JavaScript Execution**: Run JavaScript in the page context with `evaluate()`
- **Media Generation**: Capture screenshots and generate PDFs with customizable options

### 🛠️ Zero Setup Required
- **No External Dependencies**: No need to install browsers, Node.js, npm, or browser drivers
- **Bundled PhantomJS**: Complete PhantomJS engine included (~20MB) - works across all platforms
- **Self-Contained**: OS-independent with embedded binaries, no additional setup needed
- **CLI Interface**: Command-line tools for quick operations

## Installation

Install the latest version from PyPI:

```bash
pip install phasma
```

### System Requirements
- **Python**: 3.4 or higher
- **OS**: Windows, Linux, or macOS (32-bit and 64-bit supported)
- **Storage**: ~20MB for bundled PhantomJS engine (included in package)

Phasma is completely self-contained with no external dependencies - no need to install browsers, Node.js, npm, or browser drivers.

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

- `launch(options=None)` → `Browser`: Launch a new browser instance
- `connect(options=None)` → `Browser`: Connect to existing browser instance
- `download_driver(os_name=None, arch=None, force=False)` → `bool`: Download PhantomJS driver

### Browser Classes

- `Browser`: Full lifecycle management
  - `new_page()` → `Page`, `new_context()` → `BrowserContext`, `close()`, `is_connected()` → `bool`

- `BrowserContext`: Session management
  - `new_page()` → `Page`, `close()`

- `Page`: Web page automation
  - **Navigation**: `goto(url, timeout=30000)`, `set_viewport_size(width, height)`
  - **Content**: `text_content(selector)`, `inner_html(selector)`, `evaluate(expression)`
  - **Interaction**: `click(selector)`, `fill(selector, value)`, `wait_for_selector(selector, timeout=30000)`
  - **Media**: `screenshot(path)`, `pdf(path)`

- `ElementHandle`: DOM element interaction
  - `click()`, `fill(value)`, `text_content()`, `inner_html()`

### Error Handling

- `Error`: Base error class
- `TimeoutError`: Raised on timeout

## Advanced Usage

### Web Scraping with Phasma

Phasma excels at extracting data from websites, especially those with JavaScript-generated content:

```python
import asyncio
from phasma import launch

async def scrape_website():
    browser = await launch()
    try:
        page = await browser.new_page()

        # Navigate to target website
        await page.goto("https://example.com")

        # Extract multiple elements
        title = await page.text_content("h1")
        description = await page.text_content("p")

        # Execute complex JavaScript to extract structured data
        data = await page.evaluate("""
            ({
                title: document.title,
                headings: Array.from(document.querySelectorAll('h2')).map(h => h.textContent),
                links: Array.from(document.querySelectorAll('a')).map(a => ({
                    text: a.textContent,
                    href: a.href
                }))
            })
        """)

        print(f"Title: {title}")
        print(f"Description: {description[:100]}...")
        print(f"Found {len(data['headings'])} headings")
        print(f"Found {len(data['links'])} links")

    finally:
        await browser.close()

asyncio.run(scrape_website())
```

### Automated Testing

Use Phasma for automated UI testing and validation:

```python
import asyncio
from phasma import launch

async def automated_test():
    browser = await launch()
    try:
        page = await browser.new_page()

        # Navigate to test page
        await page.goto("https://example.com")

        # Verify page elements exist
        assert await page.text_content("h1") == "Example Domain"

        # Test interactions (if applicable)
        # await page.click("#some-button")
        # await page.wait_for_selector(".result-element")

        print("All tests passed!")

    finally:
        await browser.close()

asyncio.run(automated_test())
```

### Batch Processing

Process multiple URLs efficiently with async operations:

```python
import asyncio
from phasma import launch

async def process_urls(urls):
    browser = await launch()
    try:
        tasks = []
        for url in urls:
            tasks.append(capture_page(browser, url))

        results = await asyncio.gather(*tasks)
        return results
    finally:
        await browser.close()

async def capture_page(browser, url):
    page = await browser.new_page()
    try:
        await page.goto(url, timeout=10000)

        # Extract content
        title = await page.text_content("title")

        # Take screenshot
        filename = f"screenshots/{url.replace('https://', '').replace('/', '_')}.png"
        await page.screenshot(path=filename)

        return {"url": url, "title": title, "screenshot": filename}
    finally:
        await page.close()  # Close individual page, not entire browser

# Example usage
urls = [
    "https://example.com",
    "https://httpbin.org",
    "https://jsonplaceholder.typicode.com"
]

# asyncio.run(process_urls(urls))  # Uncomment to run
```

### Custom Configuration

Configure browser behavior with custom settings:

```python
import asyncio
from phasma import launch

async def custom_configuration():
    browser = await launch()
    try:
        page = await browser.new_page()

        # Set custom viewport
        await page.set_viewport_size(1280, 720)

        # Navigate with custom timeout
        await page.goto("https://example.com", timeout=15000)

        # Take high-quality screenshot
        await page.screenshot(
            path="high_quality.png",
            type="png",
            quality=100
        )

        # Generate customized PDF
        await page.pdf(
            path="custom_document.pdf",
            format="A4",
            landscape=True,
            margin={"top": "2cm", "bottom": "2cm", "left": "1.5cm", "right": "1.5cm"}
        )

    finally:
        await browser.close()

asyncio.run(custom_configuration())
```

## Testing

Phasma includes a comprehensive test suite to ensure reliability:

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_browser_api.py

# Run tests with coverage
pytest tests/ --cov=phasma
```

The test suite covers:
- Browser automation functionality
- Page navigation and content extraction
- Screenshot and PDF generation
- Element interaction methods
- Error handling and edge cases
- CLI functionality

## Performance Tips

- **Resource Management**: Always close browsers/pages to free resources:
  ```python
  try:
      browser = await launch()
      page = await browser.new_page()
      # ... do work
  finally:
      await page.close()  # or await browser.close()
  ```

- **Reuse Browser Instances**: For multiple operations, reuse the same browser instance
- **Use Async Operations**: Leverage `asyncio.gather()` for concurrent operations
- **Use `wait_for_selector()`**: Instead of fixed delays, wait for elements to appear
- **Set Appropriate Viewport Sizes**: Smaller viewports may render faster

## Use Cases

### JavaScript & DOM Execution
- **Execute JavaScript with DOM access**: Run JavaScript code that can interact with and manipulate the DOM
- **Dynamic Content Rendering**: Capture pages after JavaScript has modified the DOM
- **Client-side Script Testing**: Test JavaScript applications that modify the DOM

### Web Scraping
- Extract structured data from JavaScript-heavy websites
- Capture content that requires DOM manipulation to appear

### Document Generation
- Convert web pages to PDFs and screenshots
- Generate reports from web-based dashboards

### Automated Testing
- UI testing for JavaScript applications
- Visual regression testing

## Troubleshooting

- **Timeout Errors**: Increase timeout values or check network connectivity
- **SSL Issues**: Use `--no-ssl` flag in CLI or configure SSL settings
- **Driver Issues**: Check driver path with `python -m phasma driver --path`

## Contributing

We welcome contributions to improve Phasma!

### Development Setup

```bash
# Clone the repository
git clone https://github.com/MohammadRaziei/phasma.git
cd phasma

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Pull Request Guidelines

1. Fork the repository and create a feature branch
2. Add tests for new functionality
3. Ensure all tests pass (`pytest tests/`)
4. Update documentation as needed
5. Submit a pull request with a clear description

### Code Standards

- Follow PEP 8 style guidelines
- Write comprehensive docstrings
- Include type hints where appropriate
- Add tests for all functionality

## License & Versioning

Phasma is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

Versioning follows Semantic Versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward-compatible)
- PATCH: Bug fixes (backward-compatible)

## Acknowledgments

- **PhantomJS Team**: For creating the powerful headless browser engine
- **Playwright Team**: For inspiration with the excellent API design

---

**Phasma** – Modern PhantomJS automation with a Playwright-like API for Python developers.
