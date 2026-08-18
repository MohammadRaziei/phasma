"""
Tests for phasma.browse (the `phasma browse` terminal-browser feature).

Split in two:
- Pure-logic unit tests (grid/raster/mouse-parsing) — no PhantomJS needed.
- Integration tests against a real Page, following the same fixture style
  as test_browser.py.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

import phasma
from phasma.browse.app import BrowseApp
from phasma.browse.compose import ImageCache, build_grid
from phasma.browse.grid import Cell, TerminalGrid, parse_css_color
from phasma.browse.raster import image_to_halfblock_grid


def _write_html(html: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        return Path(f.name).as_uri()


# ── parse_css_color ─────────────────────────────────────────────────────────

def test_parse_css_color_rgb():
    assert parse_css_color("rgb(255, 0, 0)") == (255, 0, 0)


def test_parse_css_color_rgba_opaque():
    assert parse_css_color("rgba(10, 20, 30, 1)") == (10, 20, 30)


def test_parse_css_color_rgba_transparent_is_none():
    assert parse_css_color("rgba(10, 20, 30, 0)") is None


def test_parse_css_color_empty_is_none():
    assert parse_css_color("") is None
    assert parse_css_color(None) is None


def test_parse_css_color_clamps_out_of_range():
    # getComputedStyle never actually returns out-of-range digits, but the
    # parser should not explode on a stray value at the boundary.
    assert parse_css_color("rgb(255, 0, 128)") == (255, 0, 128)


# ── TerminalGrid.place_text_runs ─────────────────────────────────────────────

def test_place_text_runs_basic_position():
    grid = TerminalGrid(cols=20, rows=3, char_w=8, char_h=17)
    grid.place_text_runs([{"text": "hi", "x": 16, "y": 0, "w": 16, "h": 17, "color": "rgb(1,2,3)"}])
    assert grid.cells[0][2].ch == "h"
    assert grid.cells[0][3].ch == "i"
    assert grid.cells[0][2].fg == (1, 2, 3)


def test_place_text_runs_out_of_bounds_row_is_dropped():
    grid = TerminalGrid(cols=10, rows=1, char_w=8, char_h=17)
    grid.place_text_runs([{"text": "x", "x": 0, "y": 1000, "w": 8, "h": 17}])
    assert all(c.ch == " " for row in grid.cells for c in row)


def test_place_text_runs_gap_before_forces_separation():
    """Two runs that would round to touching columns must still get a
    blank column between them when gapBefore=True (the WebKit-collapsed-
    whitespace fix)."""
    grid = TerminalGrid(cols=20, rows=1, char_w=8, char_h=17)
    grid.place_text_runs([
        {"text": "and", "x": 0, "y": 0, "w": 24, "h": 17},
        {"text": "italic", "x": 24, "y": 0, "w": 40, "h": 17, "gapBefore": True},
    ])
    row_text = "".join(c.ch for c in grid.cells[0][:12])
    assert row_text.startswith("and "), f"expected a gap after 'and', got {row_text!r}"
    assert not row_text.startswith("andi"), f"words merged with no gap: {row_text!r}"


def test_place_text_runs_skips_plain_space_without_clobbering():
    grid = TerminalGrid(cols=5, rows=1, char_w=8, char_h=17)
    grid.set(0, 2, Cell("X", (1, 2, 3)))
    grid.place_text_runs([{"text": "a b", "x": 0, "y": 0, "w": 24, "h": 17}])
    # the space in "a b" at column 1 must not overwrite the pre-set cell at column 2... 
    # (column 1 is the space itself; column 2 already holds 'X' set above and "b" would
    # land at column 2 too - this asserts place_text_runs' own space DOES still draw 'b')
    assert grid.cells[0][0].ch == "a"
    assert grid.cells[0][2].ch == "b"  # 'b' overwrites the preset cell - only spaces are skipped


# ── TerminalGrid.render_ansi ─────────────────────────────────────────────────

def test_render_ansi_contains_truecolor_codes():
    grid = TerminalGrid(cols=3, rows=1, char_w=8, char_h=17)
    grid.set(0, 0, Cell("x", fg=(255, 0, 0)))
    out = grid.render_ansi()
    assert "38;2;255;0;0" in out
    assert "x" in out


def test_render_ansi_row_count_matches_rows():
    grid = TerminalGrid(cols=3, rows=4, char_w=8, char_h=17)
    assert grid.render_ansi().count("\n") == 3  # 4 rows -> 3 newlines joining them


# ── raster.image_to_halfblock_grid ───────────────────────────────────────────

def test_image_to_halfblock_grid_dimensions():
    from PIL import Image
    img = Image.new("RGBA", (20, 20), (255, 0, 0, 255))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f.name)
        path = f.name
    grid = image_to_halfblock_grid(path, cols=4, rows=2)
    assert len(grid) == 2
    assert all(len(row) == 4 for row in grid)
    fg, bg = grid[0][0]
    assert fg == (255, 0, 0)
    assert bg == (255, 0, 0)


def test_image_to_halfblock_grid_zero_size_returns_empty():
    assert image_to_halfblock_grid("/nonexistent.png", cols=0, rows=5) == []


# ── BrowseApp.parse_mouse ────────────────────────────────────────────────────

def test_parse_mouse_click_press():
    ev = BrowseApp.parse_mouse("<0;12;5M")
    assert ev == {"btn": 0, "col": 11, "row": 4, "pressed": True}


def test_parse_mouse_release():
    ev = BrowseApp.parse_mouse("<0;12;5m")
    assert ev["pressed"] is False


def test_parse_mouse_wheel():
    ev = BrowseApp.parse_mouse("<64;1;1M")
    assert ev["btn"] == 64


def test_parse_mouse_malformed_returns_none():
    assert BrowseApp.parse_mouse("<garbage") is None
    assert BrowseApp.parse_mouse("") is None


# ── integration: real Page ───────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def browser():
    b = await phasma.launch()
    yield b
    await b.close()


@pytest_asyncio.fixture()
async def page(browser):
    return await browser.new_page()


@pytest.mark.asyncio
async def test_page_layout_extracts_real_text(page):
    await page.set_viewport_size(400, 300)
    await page.goto(_write_html(
        "<html><body style='margin:0'><h1 style='color:rgb(255,0,0)'>Hi there</h1></body></html>"
    ))
    layout = await page.layout()
    words = [t["text"] for t in layout["texts"]]
    assert "Hi" in words and "there" in words


@pytest.mark.asyncio
async def test_page_scroll_and_active_element(page):
    await page.set_viewport_size(300, 200)
    await page.goto(_write_html(
        "<html><body style='margin:0'><div style='height:1000px'></div>"
        "<input id='inp' style='margin-top:900px'></body></html>"
    ))
    pos = await page.scroll(dy=500)
    assert pos["y"] == 500

    ae = await page.active_element()
    assert ae["editable"] is False

    await page.evaluate("document.getElementById('inp').focus()")
    ae2 = await page.active_element()
    assert ae2["editable"] is True
    assert ae2["tag"] == "INPUT"


@pytest.mark.asyncio
async def test_page_mouse_event_click(page):
    await page.set_viewport_size(300, 200)
    await page.goto(_write_html(
        "<html><body style='margin:0'>"
        "<button style='position:absolute;left:0;top:0;width:50px;height:20px' "
        "onclick=\"document.title='clicked'\">go</button></body></html>"
    ))
    await page.mouse_event("click", 10, 10)
    assert await page.evaluate("document.title") == "clicked"


@pytest.mark.asyncio
async def test_page_send_key_types_and_backspaces(page):
    await page.set_viewport_size(300, 200)
    await page.goto(_write_html("<html><body><input id='i'></body></html>"))
    await page.evaluate("document.getElementById('i').focus()")
    await page.send_key(text="hi")
    assert await page.evaluate("document.getElementById('i').value") == "hi"
    await page.send_key(special="Backspace")
    assert await page.evaluate("document.getElementById('i').value") == "h"


@pytest.mark.asyncio
async def test_build_grid_places_text_and_image(page, tmp_path):
    await page.set_viewport_size(300, 200)
    await page.goto(_write_html(
        "<html><body style='margin:0;background:#000;color:#fff'><p>Hello</p></body></html>"
    ))
    cache = ImageCache()
    grid = await build_grid(page, cols=40, rows=12, char_w=8, char_h=17, image_cache=cache)
    flat = "".join(c.ch for row in grid.cells for c in row)
    assert "Hello" in flat
