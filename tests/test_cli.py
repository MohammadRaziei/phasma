"""
Tests for the phasma CLI (python -m phasma).

All tests use subprocess so they test the real CLI entry point.
SVG and HTML fixtures are created inline — no external test data files needed.
"""

from __future__ import annotations

import subprocess
import sys
import struct
from pathlib import Path

import pytest


# ── helper ────────────────────────────────────────────────────────────────────

def run(*args, input: str = None) -> subprocess.CompletedProcess:
    """Run `python -m phasma <args>` and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "phasma", *args],
        capture_output=True,
        text=True,
        input=input,
    )


def run_bytes(*args, input: bytes = None) -> subprocess.CompletedProcess:
    """Run with binary stdout (for screenshot/pdf/svg output)."""
    return subprocess.run(
        [sys.executable, "-m", "phasma", *args],
        capture_output=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        input=input,
    )


SVG_SIMPLE = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40" fill="red"/></svg>'

HTML_SIMPLE = "<html><head><title>CLI Test</title></head><body><h1>hello</h1></body></html>"


# ── top-level ─────────────────────────────────────────────────────────────────

def test_version():
    r = run("--version")
    assert r.returncode == 0
    # should be a semver string like 0.6.0
    assert r.stdout.strip().count(".") >= 1


def test_short_version():
    r = run("-v")
    assert r.returncode == 0
    assert r.stdout.strip() == run("--version").stdout.strip()


def test_no_args_exits_nonzero():
    r = run()
    assert r.returncode != 0


def test_help():
    r = run("--help")
    assert r.returncode == 0
    assert "phasma" in r.stdout


# ── driver ────────────────────────────────────────────────────────────────────

def test_driver_version():
    r = run("driver", "--version")
    assert r.returncode == 0
    assert r.stdout.strip() == "2.1.1"


def test_driver_path():
    r = run("driver", "--path")
    assert r.returncode == 0
    path = Path(r.stdout.strip())
    assert path.exists()
    assert "phantomjs" in path.name.lower()


def test_driver_exec_version():
    r = run("driver", "exec", "--", "--version")
    assert r.returncode == 0
    assert "2.1.1" in r.stdout or "2.1.1" in r.stderr


def test_driver_download_noop():
    """Download when already present should succeed."""
    r = run("driver", "download")
    assert r.returncode == 0


# ── execjs ────────────────────────────────────────────────────────────────────

def test_execjs_expression():
    r = run("execjs", "1 + 1")
    assert r.returncode == 0
    assert r.stdout.strip() == "2"


def test_execjs_string():
    r = run("execjs", "'hello'")
    assert r.returncode == 0
    assert "hello" in r.stdout


def test_execjs_stdin():
    r = run("execjs", "-", input="2 * 21")
    assert r.returncode == 0
    assert r.stdout.strip() == "42"


# ── render-page ───────────────────────────────────────────────────────────────

def test_render_page_html_string():
    r = run("render-page", HTML_SIMPLE)
    assert r.returncode == 0
    assert "hello" in r.stdout.lower()


def test_render_page_output_file(tmp_path):
    out = tmp_path / "out.html"
    r = run("render-page", HTML_SIMPLE, "-o", str(out))
    assert r.returncode == 0
    assert out.exists()
    assert "hello" in out.read_text(encoding="utf-8").lower()


def test_render_page_from_file(tmp_path):
    f = tmp_path / "page.html"
    f.write_text(HTML_SIMPLE, encoding="utf-8")
    r = run("render-page", str(f))
    assert r.returncode == 0
    assert "hello" in r.stdout.lower()


def test_render_page_viewport(tmp_path):
    out = tmp_path / "out.html"
    r = run("render-page", HTML_SIMPLE, "-o", str(out), "--viewport", "1920x1080")
    assert r.returncode == 0
    assert out.exists()


# ── render-url ────────────────────────────────────────────────────────────────

def test_render_url(tmp_path):
    """Use a local file:// URL so no network is needed."""
    f = tmp_path / "page.html"
    f.write_text(HTML_SIMPLE, encoding="utf-8")
    r = run("render-url", f.as_uri())
    assert r.returncode == 0
    assert "hello" in r.stdout.lower()


def test_render_url_output_file(tmp_path):
    f = tmp_path / "page.html"
    f.write_text(HTML_SIMPLE, encoding="utf-8")
    out = tmp_path / "out.html"
    r = run("render-url", f.as_uri(), "-o", str(out))
    assert r.returncode == 0
    assert out.exists()


# ── screenshot ────────────────────────────────────────────────────────────────

def test_screenshot(tmp_path):
    src = tmp_path / "page.html"
    src.write_text(HTML_SIMPLE, encoding="utf-8")
    out = tmp_path / "shot.png"
    r = run("screenshot", src.as_uri(), str(out))
    assert r.returncode == 0
    assert out.exists()
    assert out.read_bytes()[:4] == b"\x89PNG"


def test_screenshot_viewport(tmp_path):
    src = tmp_path / "page.html"
    src.write_text(HTML_SIMPLE, encoding="utf-8")
    out = tmp_path / "shot.png"
    r = run("screenshot", src.as_uri(), str(out), "--viewport", "800x600")
    assert r.returncode == 0
    data = out.read_bytes()
    w = struct.unpack(">I", data[16:20])[0]
    h = struct.unpack(">I", data[20:24])[0]
    assert w == 800 and h == 600


# ── pdf ───────────────────────────────────────────────────────────────────────

def test_pdf(tmp_path):
    src = tmp_path / "page.html"
    src.write_text(HTML_SIMPLE, encoding="utf-8")
    out = tmp_path / "doc.pdf"
    r = run("pdf", src.as_uri(), str(out))
    assert r.returncode == 0
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_pdf_landscape(tmp_path):
    src = tmp_path / "page.html"
    src.write_text(HTML_SIMPLE, encoding="utf-8")
    out = tmp_path / "landscape.pdf"
    r = run("pdf", src.as_uri(), str(out), "--format", "A4", "--landscape")
    assert r.returncode == 0
    assert out.read_bytes()[:4] == b"%PDF"


# ── svg ───────────────────────────────────────────────────────────────────────

def test_svg_to_png_file(tmp_path):
    svg_file = tmp_path / "icon.svg"
    svg_file.write_text(SVG_SIMPLE, encoding="utf-8")
    out = tmp_path / "icon.png"
    r = run("svg", str(svg_file), "-o", str(out))
    assert r.returncode == 0
    assert out.read_bytes()[:4] == b"\x89PNG"


def test_svg_to_png_scale(tmp_path):
    svg_file = tmp_path / "icon.svg"
    svg_file.write_text(SVG_SIMPLE, encoding="utf-8")
    out = tmp_path / "icon_2x.png"
    r = run("svg", str(svg_file), "-o", str(out), "--scale", "2.0")
    assert r.returncode == 0
    data = out.read_bytes()
    w = struct.unpack(">I", data[16:20])[0]
    h = struct.unpack(">I", data[20:24])[0]
    assert w == 200 and h == 200


def test_svg_to_jpeg(tmp_path):
    svg_file = tmp_path / "icon.svg"
    svg_file.write_text(SVG_SIMPLE, encoding="utf-8")
    out = tmp_path / "icon.jpg"
    r = run("svg", str(svg_file), "-o", str(out), "--format", "jpeg")
    assert r.returncode == 0
    assert out.read_bytes()[:2] == b"\xff\xd8"


def test_svg_to_pdf_fit(tmp_path):
    svg_file = tmp_path / "icon.svg"
    svg_file.write_text(SVG_SIMPLE, encoding="utf-8")
    out = tmp_path / "icon.pdf"
    r = run("svg", str(svg_file), "-o", str(out), "--format", "pdf")
    assert r.returncode == 0
    assert out.read_bytes()[:4] == b"%PDF"


def test_svg_to_pdf_a4(tmp_path):
    svg_file = tmp_path / "icon.svg"
    svg_file.write_text(SVG_SIMPLE, encoding="utf-8")
    out = tmp_path / "icon_a4.pdf"
    r = run("svg", str(svg_file), "-o", str(out), "--format", "pdf", "--pdf-format", "A4")
    assert r.returncode == 0
    assert out.read_bytes()[:4] == b"%PDF"


def test_svg_stdin(tmp_path):
    out = tmp_path / "from_stdin.png"
    r = run("svg", "-", "-o", str(out), input=SVG_SIMPLE)
    assert r.returncode == 0
    assert out.read_bytes()[:4] == b"\x89PNG"


def test_svg_background(tmp_path):
    svg_file = tmp_path / "icon.svg"
    svg_file.write_text(SVG_SIMPLE, encoding="utf-8")
    out = tmp_path / "icon_dark.png"
    r = run("svg", str(svg_file), "-o", str(out), "--background", "#000000")
    assert r.returncode == 0
    assert out.read_bytes()[:4] == b"\x89PNG"
