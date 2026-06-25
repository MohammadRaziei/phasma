"""
Phasma CLI — python -m phasma <command>

Commands:
  driver              Manage the PhantomJS binary
  render-page         Render an HTML file or string
  render-url          Render a URL
  execjs              Execute JavaScript
  screenshot          Take a screenshot
  pdf                 Generate a PDF
  svg                 Convert SVG to PNG, JPEG, or PDF
"""

import argparse
import asyncio
import sys
from pathlib import Path

import phasma
from phasma.driver import Driver
from phasma.svg import SvgRenderer


# ── helpers ───────────────────────────────────────────────────────────────────

def _err(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def _ok(msg: str) -> None:
    print(msg)


# ── svg handler ───────────────────────────────────────────────────────────────

async def _svg(args) -> None:
    source = args.input
    output = args.output
    scale  = args.scale
    bg     = args.background
    fmt    = args.format.lower()

    async with SvgRenderer() as r:
        if fmt == "png":
            data = await r.to_png(source, output, scale=scale, background=bg)
        elif fmt in ("jpeg", "jpg"):
            data = await r.to_jpeg(source, output, scale=scale, background=bg)
        elif fmt == "pdf":
            pdf_format = args.pdf_format  # None = fit to SVG size
            data = await r.to_pdf(
                source, output,
                scale=scale,
                background=bg,
                pdf_format=pdf_format,
                pdf_landscape=args.landscape,
                pdf_margin=args.margin,
            )
        else:
            _err(f"unknown format: {fmt!r}. Use png, jpeg, or pdf.")

    if output:
        _ok(f"saved to {output}  ({len(data):,} bytes)")
    else:
        sys.stdout.buffer.write(data)


# ── build parser ──────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m phasma",
        description="Phasma: Playwright-like async API for PhantomJS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python -m phasma driver --version
  python -m phasma driver download --force
  python -m phasma driver exec script.js

  python -m phasma render-page file.html -o out.html --viewport 1920x1080
  python -m phasma render-url https://example.com -o page.html --wait 2000

  python -m phasma execjs "document.title"
  python -m phasma execjs -                          # read from stdin

  python -m phasma screenshot https://example.com shot.png --viewport 1280x720
  python -m phasma pdf https://example.com doc.pdf --format A4 --landscape

  python -m phasma svg diagram.svg -o diagram.png
  python -m phasma svg diagram.svg -o diagram.png --scale 2.0
  python -m phasma svg diagram.svg -o diagram.pdf --format pdf
  python -m phasma svg diagram.svg -o diagram.pdf --format pdf --pdf-format A4
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # ── driver ────────────────────────────────────────────────────────────────
    dp = sub.add_parser("driver", help="Manage the PhantomJS binary")
    dp.add_argument("--version", action="store_true", help="Show PhantomJS version")
    dp.add_argument("--path",    action="store_true", help="Show binary path")
    dsub = dp.add_subparsers(dest="driver_action")

    dl = dsub.add_parser("download", help="Download the PhantomJS binary")
    dl.add_argument("--os",    help="Target OS (windows, linux, darwin)")
    dl.add_argument("--arch",  help="Target arch (32bit, 64bit)")
    dl.add_argument("--force", action="store_true", help="Re-download even if present")

    ex = dsub.add_parser("exec", help="Run PhantomJS with given arguments")
    ex.add_argument("args",    nargs="*", help="Arguments passed to PhantomJS")
    ex.add_argument("--timeout",        type=float, help="Timeout in seconds")
    ex.add_argument("--cwd",            help="Working directory")
    ex.add_argument("--ssl",            action="store_true", default=False)
    ex.add_argument("--capture-output", action="store_true")

    # ── render-page ───────────────────────────────────────────────────────────
    rp = sub.add_parser("render-page", help="Render an HTML file or HTML string")
    rp.add_argument("input",       help="HTML file path or raw HTML string")
    rp.add_argument("-o", "--output", help="Output file (default: stdout)")
    rp.add_argument("--viewport",  default="1024x768", help="WIDTHxHEIGHT (default: 1024x768)")
    rp.add_argument("--wait",      type=int, default=100, help="Settle delay in ms (default: 100)")

    # ── render-url ────────────────────────────────────────────────────────────
    ru = sub.add_parser("render-url", help="Render a URL")
    ru.add_argument("url",            help="URL to render")
    ru.add_argument("-o", "--output", help="Output file (default: stdout)")
    ru.add_argument("--viewport",  default="1024x768")
    ru.add_argument("--wait",      type=int, default=0)

    # ── execjs ────────────────────────────────────────────────────────────────
    js = sub.add_parser("execjs", help="Execute JavaScript in PhantomJS")
    js.add_argument("script", help="JS expression, or '-' to read from stdin")

    # ── screenshot ────────────────────────────────────────────────────────────
    sc = sub.add_parser("screenshot", help="Take a screenshot of a URL")
    sc.add_argument("url",      help="URL")
    sc.add_argument("output",   help="Output file path (.png or .jpg)")
    sc.add_argument("--viewport", default="1024x768")
    sc.add_argument("--wait",   type=int, default=100)

    # ── pdf ───────────────────────────────────────────────────────────────────
    pf = sub.add_parser("pdf", help="Generate a PDF from a URL")
    pf.add_argument("url",      help="URL")
    pf.add_argument("output",   help="Output file path (.pdf)")
    pf.add_argument("--format", default="A4", help="Paper format (default: A4)")
    pf.add_argument("--landscape", action="store_true")
    pf.add_argument("--margin", default="1cm")
    pf.add_argument("--viewport", default="1024x768")
    pf.add_argument("--wait",   type=int, default=100)

    # ── svg ───────────────────────────────────────────────────────────────────
    sv = sub.add_parser("svg", help="Convert SVG to PNG, JPEG, or PDF")
    sv.add_argument("input",            help="SVG file path or raw SVG string")
    sv.add_argument("-o", "--output",   help="Output file path (default: stdout)")
    sv.add_argument("--format",         default="png",
                    choices=["png", "jpeg", "jpg", "pdf"],
                    help="Output format (default: png)")
    sv.add_argument("--scale",          type=float, default=1.0,
                    help="Scale factor, e.g. 2.0 for 2× resolution (default: 1.0)")
    sv.add_argument("--background",     default="white",
                    help="CSS background color (default: white)")
    sv.add_argument("--pdf-format",     default=None, metavar="FORMAT",
                    help="PDF paper format e.g. A4, Letter. "
                         "Omit to fit paper to SVG dimensions (default: fit)")
    sv.add_argument("--landscape",      action="store_true",
                    help="Landscape orientation (PDF only)")
    sv.add_argument("--margin",         default="0",
                    help="PDF margin e.g. '1cm', '10px' (default: 0)")

    return parser


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # ── driver ────────────────────────────────────────────────────────────────
    if args.command == "driver":
        if args.driver_action == "download":
            ok = Driver.download(os_name=args.os, arch=args.arch, force=args.force)
            if ok:
                _ok("driver downloaded successfully.")
            else:
                _err("driver download failed.")

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
                _err(str(e))
            if args.capture_output:
                if result.stdout:
                    sys.stdout.buffer.write(result.stdout)
                if result.stderr:
                    sys.stderr.buffer.write(result.stderr)
            sys.exit(result.returncode)

        elif args.version:
            _ok(Driver().version)

        elif args.path:
            _ok(str(Driver().bin_path))

        else:
            # show help for `python -m phasma driver` with no subcommand
            parser.parse_args(["driver", "--help"])

    # ── render-page ───────────────────────────────────────────────────────────
    elif args.command == "render-page":
        result = phasma.sync_render_page_content(
            args.input, args.output, viewport=args.viewport, wait=args.wait
        )
        if result:
            sys.stdout.write(result)

    # ── render-url ────────────────────────────────────────────────────────────
    elif args.command == "render-url":
        result = phasma.sync_render_url_content(
            args.url, args.output, viewport=args.viewport, wait=args.wait
        )
        if result:
            sys.stdout.write(result)

    # ── execjs ────────────────────────────────────────────────────────────────
    elif args.command == "execjs":
        script = sys.stdin.read() if args.script == "-" else args.script
        result = phasma.sync_execute_js_script(script)
        if result is not None:
            sys.stdout.write(str(result))

    # ── screenshot ────────────────────────────────────────────────────────────
    elif args.command == "screenshot":
        phasma.sync_take_screenshot(
            args.url, args.output, viewport=args.viewport, wait=args.wait
        )
        _ok(f"saved to {args.output}")

    # ── pdf ───────────────────────────────────────────────────────────────────
    elif args.command == "pdf":
        phasma.sync_generate_pdf(
            args.url, args.output,
            format=args.format,
            landscape=args.landscape,
            margin=args.margin,
            viewport=args.viewport,
            wait=args.wait,
        )
        _ok(f"saved to {args.output}")

    # ── svg ───────────────────────────────────────────────────────────────────
    elif args.command == "svg":
        asyncio.run(_svg(args))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
    