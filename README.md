# Phasma – Modern PhantomJS Browser Automation for Python

<div align="center">
<img src="https://github.com/MohammadRaziei/phasma/raw/master/docs/images/phasma.jpg" width="30%" style="min-width: 200px;" alt="Phasma Logo" />
</div>

**Phasma** is a modern Python library that provides a Playwright-like API for PhantomJS browser automation. Unlike other tools, Phasma requires **no external dependencies** - no need to install browsers, Node.js, npm, or browser drivers like Chrome or Firefox. It includes a bundled PhantomJS engine and provides a familiar Playwright-like interface, making it ideal for web scraping, automated testing, screenshot capture, and PDF generation.

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
- **No External Dependencies**: No need to install browsers, Node.js, npm, or browser drivers
- **Bundled PhantomJS**: Complete PhantomJS engine included in the package
- **Automatic Driver Management**: Driver downloaded and managed automatically
- **Cross-Platform**: Works seamlessly on Windows, Linux, and macOS
- **Zero Configuration**: No setup required - just install and use
- **CLI Interface**: Command-line tools for quick operations

### 📋 Technical Specifications
- **Python 3.4+**: Compatible with modern Python versions
- **No External Dependencies**: No need for browsers, Node.js, npm, or browser drivers
- **Self-Contained**: Bundled PhantomJS engine included
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
- **No External Dependencies**: No need to install browsers, Node.js, npm, or browser drivers
- **Memory**: Minimal memory footprint
- **Storage**: ~50MB for bundled PhantomJS engine (downloaded automatically)

Phasma is completely self-contained - it includes the PhantomJS engine and requires no external dependencies. No need to install Chrome, Firefox, Node.js, npm, or any browser drivers. The bundled PhantomJS engine is automatically downloaded and managed when needed.

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

## Performance Considerations

### Best Practices

1. **Resource Management**: Always close browsers and pages to free resources:
   ```python
   try:
       browser = await launch()
       page = await browser.new_page()
       # ... do work
   finally:
       await page.close()  # or await browser.close()
   ```

2. **Reuse Browser Instances**: For multiple operations, reuse the same browser:
   ```python
   browser = await launch()
   try:
       for url in urls:
           page = await browser.new_page()
           await page.goto(url)
           # ... process page
           await page.close()  # Close just the page
   finally:
       await browser.close()  # Close browser when done
   ```

3. **Set Appropriate Timeouts**: Configure timeouts based on your needs:
   ```python
   await page.goto(url, timeout=30000)  # 30 seconds
   ```

4. **Use Async Operations**: Leverage async/await for concurrent operations:
   ```python
   tasks = [process_page(url) for url in urls]
   results = await asyncio.gather(*tasks)
   ```

### Performance Tips

- Use `page.wait_for_selector()` instead of fixed delays
- Set appropriate viewport sizes for your use case
- Consider using smaller viewport sizes for faster rendering
- Close pages individually when processing multiple URLs with one browser

## Use Cases

### Web Scraping
- Extract structured data from JavaScript-heavy websites
- Capture dynamic content that requires JavaScript execution
- Handle complex forms and interactions

### Automated Testing
- UI testing for web applications
- Visual regression testing with screenshots
- Functional testing of JavaScript applications

### Document Generation
- Convert web pages to PDFs for archiving
- Generate reports from web-based dashboards
- Create print-ready documents from HTML content

### Screenshot Services
- Capture website previews
- Generate social media thumbnails
- Visual validation of web pages

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase timeout values or check network connectivity
2. **SSL Issues**: Use `--no-ssl` flag in CLI or configure SSL settings
3. **Driver Download**: Ensure internet connectivity for initial driver download

### Debugging Tips

- Enable verbose logging for detailed information
- Check PhantomJS driver path with `python -m phasma driver --path`
- Verify PhantomJS version compatibility

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

## License

Phasma is distributed under the MIT License. See the [LICENSE](LICENSE) file for complete license text.

## Versioning

Phasma follows Semantic Versioning (SemVer):
- MAJOR versions for incompatible API changes
- MINOR versions for functionality added in a backward-compatible manner
- PATCH versions for backward-compatible bug fixes

## Acknowledgments

- **PhantomJS Team**: For creating the powerful headless browser engine
- **Playwright Team**: For inspiration with the excellent API design
- **Python Community**: For the robust ecosystem and tooling
- **Open Source Contributors**: For continuous improvements and feedback

---

**Phasma** – Modern PhantomJS automation with a Playwright-like API for Python developers.
