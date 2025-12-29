"""
Phasma - PhantomJS driver for Python.
Command-line interface with Playwright-like API support.
"""
import sys
import os
import argparse
import asyncio
from pathlib import Path
import tempfile
import asyncio


import phasma
from phasma.driver import Driver


def main():
    parser = argparse.ArgumentParser(
        description="Phasma: Modern PhantomJS automation with Playwright-like API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Driver management
  python -m phasma driver --version
  python -m phasma driver --path
  python -m phasma driver download --force

  # Execute PhantomJS directly
  python -m phasma driver exec --version
  python -m phasma driver exec script.js --ssl --timeout 30

  # Render HTML content
  python -m phasma render-page file.html --output result.html --viewport 1920x1080
  python -m phasma render-page "<html><body>Hello</body></html>" --wait 500

  # Render URLs
  python -m phasma render-url https://example.com --wait 2000
  python -m phasma render-url https://example.com --output page.html

  # Execute JavaScript
  python -m phasma execjs "console.log('Hello from PhantomJS');"
  python -m phasma execjs "document.title" --arg value1

  # Screenshot and PDF generation (using new API)
  python -m phasma screenshot https://example.com screenshot.png
  python -m phasma pdf https://example.com document.pdf
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # driver command
    driver_parser = subparsers.add_parser("driver", help="Manage PhantomJS driver")
    driver_subparsers = driver_parser.add_subparsers(dest="driver_action", help="Driver management actions")

    # driver download
    dl_parser = driver_subparsers.add_parser("download", help="Download PhantomJS driver")
    dl_parser.add_argument("--os", help="Operating system (windows, linux, darwin)")
    dl_parser.add_argument("--arch", help="Architecture (32bit, 64bit)")
    dl_parser.add_argument("--force", action="store_true", help="Force download even if already exists")

    # driver exec
    exec_parser = driver_subparsers.add_parser("exec", help="Execute PhantomJS with arguments")
    exec_parser.add_argument("args", nargs="*", help="Arguments to pass to PhantomJS (e.g., '--version', 'script.js')")
    exec_parser.add_argument("--capture-output", action="store_true", help="Capture stdout and stderr")
    exec_parser.add_argument("--timeout", type=float, help="Timeout in seconds")
    exec_parser.add_argument("--cwd", help="Working directory for PhantomJS process")
    exec_parser.add_argument("--ssl", action="store_true", default=False, help="Enable SSL (default: False)")
    exec_parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="Disable SSL (set OPENSSL_CONF='')")

    # driver --version and --path as optional arguments of driver command itself
    driver_parser.add_argument("--version", action="store_true", help="Show driver version")
    driver_parser.add_argument("--path", action="store_true", help="Show driver executable path")

    # render-page
    rp_parser = subparsers.add_parser("render-page", help="Render an HTML page with JavaScript support")
    rp_parser.add_argument("input", help="HTML file path or HTML string to render")
    rp_parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    rp_parser.add_argument("--viewport", default="1024x768", help="Viewport size as WIDTHxHEIGHT (default: 1024x768)")
    rp_parser.add_argument("--wait", type=int, default=100, help="Wait time in milliseconds after page load (default: 100)")

    # render-url
    ru_parser = subparsers.add_parser("render-url", help="Render a URL with JavaScript support")
    ru_parser.add_argument("url", help="URL to render")
    ru_parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    ru_parser.add_argument("--viewport", default="1024x768", help="Viewport size as WIDTHxHEIGHT (default: 1024x768)")
    ru_parser.add_argument("--wait", type=int, default=0, help="Wait time in milliseconds after page load (default: 0)")

    # execjs
    js_parser = subparsers.add_parser("execjs", help="Execute JavaScript code in PhantomJS context")
    js_parser.add_argument("script", help="JavaScript code to execute (use '-' to read from stdin)")
    js_parser.add_argument("--arg", action="append", help="Additional arguments to pass to the script")

    # screenshot command (new API)
    screenshot_parser = subparsers.add_parser("screenshot", help="Take a screenshot of a webpage")
    screenshot_parser.add_argument("url", help="URL to take screenshot of")
    screenshot_parser.add_argument("output", help="Output file path for the screenshot")
    screenshot_parser.add_argument("--viewport", default="1024x768", help="Viewport size as WIDTHxHEIGHT (default: 1024x768)")
    screenshot_parser.add_argument("--wait", type=int, default=100, help="Wait time in milliseconds after page load (default: 100)")

    # pdf command (new API)
    pdf_parser = subparsers.add_parser("pdf", help="Generate a PDF from a webpage")
    pdf_parser.add_argument("url", help="URL to generate PDF from")
    pdf_parser.add_argument("output", help="Output file path for the PDF")
    pdf_parser.add_argument("--format", default="A4", help="PDF format (A3, A4, A5, Letter, Legal, etc.)")
    pdf_parser.add_argument("--landscape", action="store_true", help="Use landscape orientation")
    pdf_parser.add_argument("--margin", default="1cm", help="Page margin (default: 1cm)")
    pdf_parser.add_argument("--viewport", default="1024x768", help="Viewport size as WIDTHxHEIGHT (default: 1024x768)")
    pdf_parser.add_argument("--wait", type=int, default=100, help="Wait time in milliseconds after page load (default: 100)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "driver":
        if args.driver_action == "download":
            success = Driver.download(os_name=args.os, arch=args.arch, force=args.force)
            if success:
                print("Driver downloaded successfully.")
                sys.exit(0)
            else:
                print("Driver download failed.")
                sys.exit(1)
        elif args.driver_action == "exec":
            driver = Driver()
            try:
                result = driver.exec(
                    args.args,
                    capture_output=args.capture_output,
                    timeout=args.timeout,
                    ssl=args.ssl,
                    cwd=args.cwd,
                )
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

            if args.capture_output:
                if result.stdout:
                    sys.stdout.buffer.write(result.stdout)
                if result.stderr:
                    sys.stderr.buffer.write(result.stderr)
            sys.exit(result.returncode)
        elif args.version:
            driver = Driver()
            version = driver.version
            print(f"PhantomJS driver version: {version}")
        elif args.path:
            driver = Driver()
            path = driver.bin_path
            print(path)
        else:
            driver_parser.print_help()
            sys.exit(1)

    elif args.command == "render-page":
        # Use the new Playwright-like API for rendering HTML pages
        async def render_page_content():
            browser = await phasma.browser.launch()
            try:
                page = await browser.new_page()

                # Set viewport size
                width, height = map(int, args.viewport.split('x'))
                await page.set_viewport_size(width, height)

                # Read HTML content
                input_path = Path(args.input)
                if input_path.is_file():
                    html_content = input_path.read_text(encoding='utf-8')
                else:
                    html_content = args.input

                # Create a temporary HTML file with the content and navigate to it
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(html_content)
                    temp_html_path = temp_file.name

                try:
                    # Navigate to the temporary HTML file
                    await page.goto(f"file://{temp_html_path}")

                    # Wait for the specified time
                    await asyncio.sleep(args.wait / 1000.0)  # Convert milliseconds to seconds

                    # Get the rendered content
                    rendered = await page.evaluate("document.documentElement.outerHTML")
                    if not args.output:
                        print(rendered)
                    else:
                        Path(args.output).write_text(rendered, encoding='utf-8')
                        print(f"Rendered content saved to {args.output}")

                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_html_path):
                        os.unlink(temp_html_path)

            finally:
                await browser.close()

        asyncio.run(render_page_content())

    elif args.command == "render-url":
        # Use the new Playwright-like API for rendering URLs
        async def render_url_content():
            browser = await phasma.browser.launch()
            try:
                page = await browser.new_page()

                # Set viewport size
                width, height = map(int, args.viewport.split('x'))
                await page.set_viewport_size(width, height)

                # Navigate to URL
                await page.goto(args.url)
                # Wait for the specified time
                await asyncio.sleep(args.wait / 1000.0)  # Convert milliseconds to seconds

                # Get the rendered content
                rendered = await page.evaluate("document.documentElement.outerHTML")
                if not args.output:
                    print(rendered)
                else:
                    Path(args.output).write_text(rendered, encoding='utf-8')
                    print(f"Rendered content saved to {args.output}")

            finally:
                await browser.close()

        asyncio.run(render_url_content())

    elif args.command == "execjs":
        # Use the new Playwright-like API for executing JavaScript
        async def exec_js():
            browser = await phasma.browser.launch()
            try:
                page = await browser.new_page()

                # Navigate to a blank page first
                await page.goto("about:blank")

                # Execute the JavaScript code
                if args.script == "-":
                    script = sys.stdin.read()
                else:
                    script = args.script

                # Evaluate the script in the page context
                result = await page.evaluate(script)
                print(result)

            finally:
                await browser.close()

        asyncio.run(exec_js())

    elif args.command == "screenshot":
        # Use the new Playwright-like API for screenshot
        async def take_screenshot():
            browser = await phasma.browser.launch()
            try:
                page = await browser.new_page()

                # Set viewport size
                width, height = map(int, args.viewport.split('x'))
                await page.set_viewport_size(width, height)

                # Navigate to URL
                await page.goto(args.url)
                # Wait for the specified time
                import asyncio
                await asyncio.sleep(args.wait / 1000.0)  # Convert milliseconds to seconds

                # Take screenshot
                await page.screenshot(path=args.output)
                print(f"Screenshot saved to {args.output}")

            finally:
                await browser.close()

        asyncio.run(take_screenshot())

    elif args.command == "pdf":
        # Use the new Playwright-like API for PDF generation
        async def generate_pdf():
            browser = await phasma.browser.launch()
            try:
                page = await browser.new_page()

                # Set viewport size
                width, height = map(int, args.viewport.split('x'))
                await page.set_viewport_size(width, height)

                # Navigate to URL
                await page.goto(args.url)
                # Wait for the specified time
                await asyncio.sleep(args.wait / 1000.0)  # Convert milliseconds to seconds

                # Generate PDF with specified options
                await page.pdf(
                    path=args.output,
                    format=args.format,
                    landscape=args.landscape,
                    margin=args.margin
                )
                print(f"PDF saved to {args.output}")

            finally:
                await browser.close()

        asyncio.run(generate_pdf())

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
