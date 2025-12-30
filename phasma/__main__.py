"""
Phasma - PhantomJS driver for Python.
Command-line interface with Playwright-like API support.
"""
import argparse
import logging
import sys

import phasma
from phasma.driver import Driver

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


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
                logger.info("Driver downloaded successfully.")
                sys.exit(0)
            else:
                logger.error("Driver download failed.")
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
                logger.error(f"Error: {e}")
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
            logger.info(f"PhantomJS driver version: {version}")
        elif args.path:
            driver = Driver()
            path = driver.bin_path
            logger.info(str(path))
        else:
            driver_parser.print_help()
            sys.exit(1)

    elif args.command == "render-page":
        # Use the function from phasma module
        result = phasma.sync_render_page_content(
            input_content=args.input,
            output_path=args.output,
            viewport=args.viewport,
            wait=args.wait
        )
        if result:
            sys.stdout.write(result)  # Use sys.stdout.write for output content to stdout

    elif args.command == "render-url":
        # Use the function from phasma module
        result = phasma.sync_render_url_content(
            url=args.url,
            output_path=args.output,
            viewport=args.viewport,
            wait=args.wait
        )
        if result:
            sys.stdout.write(result)  # Use sys.stdout.write for output content to stdout

    elif args.command == "execjs":
        # Use the function from phasma module
        if args.script == "-":
            script = sys.stdin.read()
        else:
            script = args.script
        result = phasma.sync_execute_js_script(script)
        sys.stdout.write(result)  # Use sys.stdout.write for output content to stdout

    elif args.command == "screenshot":
        # Use the function from phasma module
        phasma.sync_take_screenshot(
            url=args.url,
            output_path=args.output,
            viewport=args.viewport,
            wait=args.wait
        )
        logger.info(f"Screenshot saved to {args.output}")

    elif args.command == "pdf":
        # Use the function from phasma module
        phasma.sync_generate_pdf(
            url=args.url,
            output_path=args.output,
            format=args.format,
            landscape=args.landscape,
            margin=args.margin,
            viewport=args.viewport,
            wait=args.wait
        )
        logger.info(f"PDF saved to {args.output}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
