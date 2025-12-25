"""
Phasma - PhantomJS driver for Python.
Command-line interface.
"""
import sys
import os
import argparse
from pathlib import Path

# Add src directory to sys.path to allow absolute imports

from phasma.phasma import download_driver, render_page, render_url, execjs
from phasma.driver import Driver

def main():
    parser = argparse.ArgumentParser(description="Phasma: PhantomJS driver for Python")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # driver command
    driver_parser = subparsers.add_parser("driver", help="Manage PhantomJS driver")
    driver_subparsers = driver_parser.add_subparsers(dest="driver_action", help="Driver action")

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
    rp_parser = subparsers.add_parser("render-page", help="Render an HTML page")
    rp_parser.add_argument("input", help="HTML file path or HTML string")
    rp_parser.add_argument("--output", "-o", help="Output file path")
    rp_parser.add_argument("--viewport", default="1024x768", help="Viewport size (widthxheight)")
    rp_parser.add_argument("--wait", type=int, default=100, help="Wait time in milliseconds")

    # render-url
    ru_parser = subparsers.add_parser("render-url", help="Render a URL")
    ru_parser.add_argument("url", help="URL to render")
    ru_parser.add_argument("--output", "-o", help="Output file path")
    ru_parser.add_argument("--viewport", default="1024x768", help="Viewport size (widthxheight)")
    ru_parser.add_argument("--wait", type=int, default=0, help="Wait time in milliseconds")

    # execjs
    js_parser = subparsers.add_parser("execjs", help="Execute JavaScript code")
    js_parser.add_argument("script", help="JavaScript code (use '-' to read from stdin)")
    js_parser.add_argument("--arg", action="append", help="Additional arguments to pass")

    args = parser.parse_args()

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
        # Determine if input is a file
        input_path = Path(args.input)
        if input_path.is_file():
            page = input_path
        else:
            page = args.input
        rendered = render_page(page, output=args.output, viewport_size=args.viewport, wait_time=args.wait)
        if not args.output:
            print(rendered)
        else:
            print(f"Rendered content saved to {args.output}")

    elif args.command == "render-url":
        rendered = render_url(args.url, output=args.output, viewport_size=args.viewport, wait_time=args.wait)
        if not args.output:
            print(rendered)
        else:
            print(f"Rendered content saved to {args.output}")

    elif args.command == "execjs":
        if args.script == "-":
            script = sys.stdin.read()
        else:
            script = args.script
        output = execjs(script, args=args.arg)
        print(output)

    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
