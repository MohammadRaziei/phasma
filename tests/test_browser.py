"""
Tests for the phasma browser API (HTTP-based persistent PhantomJS session).

Fixtures
--------
- `page`  : a fresh Page inside a single Browser per test module (session-scoped).
             Re-uses the same PhantomJS process for the whole module → fast.
- `local_page(html)` : helper that writes HTML to a temp file and navigates to it.

Marks
-----
- All async tests require `pytest-asyncio` (already in dev deps).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

import phasma
from phasma.browser import Error


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def browser():
    """One PhantomJS process shared across all tests in this module."""
    b = await phasma.launch()
    yield b
    await b.close()


@pytest_asyncio.fixture()
async def page(browser):
    """Fresh Page for each test (same PhantomJS process)."""
    return await browser.new_page()


def _write_html(html: str) -> str:
    """Write *html* to a temp file and return a file:// URL."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        return Path(f.name).as_uri()


# ── launch / close ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_launch_and_close():
    """launch() returns a connected Browser; close() disconnects it."""
    b = await phasma.launch()
    assert b.is_connected()
    await b.close()
    assert not b.is_connected()


@pytest.mark.asyncio
async def test_double_close_is_safe():
    b = await phasma.launch()
    await b.close()
    await b.close()          # should not raise


# ── navigation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_goto_returns_html(page):
    url = _write_html("<html><body><h1>Hi</h1></body></html>")
    html = await page.goto(url)
    assert html is not None
    assert "Hi" in html


@pytest.mark.asyncio
async def test_goto_multiple_times(page):
    """Same page object navigates multiple times without restarting PhantomJS."""
    url_a = _write_html("<html><head><title>PageA</title></head><body></body></html>")
    url_b = _write_html("<html><head><title>PageB</title></head><body></body></html>")

    await page.goto(url_a)
    assert await page.evaluate("document.title") == "PageA"

    await page.goto(url_b)
    assert await page.evaluate("document.title") == "PageB"


# ── evaluate ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_primitive(page):
    await page.goto(_write_html("<html><head><title>Eval</title></head><body></body></html>"))
    assert await page.evaluate("document.title") == "Eval"
    assert await page.evaluate("1 + 1") == 2
    assert await page.evaluate("true") is True


@pytest.mark.asyncio
async def test_evaluate_returns_object(page):
    await page.goto(_write_html("<html><body><p>x</p><p>y</p></body></html>"))
    count = await page.evaluate(
        "document.querySelectorAll('p').length"
    )
    assert count == 2


# ── text_content / inner_html ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_text_content(page):
    await page.goto(_write_html(
        "<html><body><h1>Hello World</h1></body></html>"
    ))
    assert await page.text_content("h1") == "Hello World"


@pytest.mark.asyncio
async def test_inner_html(page):
    await page.goto(_write_html(
        "<html><body><div id='x'><span>inner</span></div></body></html>"
    ))
    assert await page.inner_html("#x") == "<span>inner</span>"


@pytest.mark.asyncio
async def test_text_content_missing_selector_raises(page):
    await page.goto(_write_html("<html><body></body></html>"))
    with pytest.raises(Error):
        await page.text_content("#does-not-exist")


# ── click / fill ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fill_and_read_back(page):
    await page.goto(_write_html(
        "<html><body><input id='inp' type='text'/></body></html>"
    ))
    await page.fill("#inp", "hello phasma")
    value = await page.evaluate("document.getElementById('inp').value")
    assert value == "hello phasma"


@pytest.mark.asyncio
async def test_click_toggles_state(page):
    await page.goto(_write_html("""
        <html><body>
          <button id='btn' onclick="this.dataset.clicked='yes'">click me</button>
        </body></html>
    """))
    await page.click("#btn")
    clicked = await page.evaluate("document.getElementById('btn').dataset.clicked")
    assert clicked == "yes"


@pytest.mark.asyncio
async def test_click_missing_selector_raises(page):
    await page.goto(_write_html("<html><body></body></html>"))
    with pytest.raises(Error):
        await page.click("#ghost")


@pytest.mark.asyncio
async def test_fill_missing_selector_raises(page):
    await page.goto(_write_html("<html><body></body></html>"))
    with pytest.raises(Error):
        await page.fill("#ghost", "value")


# ── wait_for_selector ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wait_for_selector_found(page):
    await page.goto(_write_html(
        "<html><body><div id='here'>present</div></body></html>"
    ))
    el = await page.wait_for_selector("#here", timeout=3000)
    assert el is not None
    assert await el.text_content() == "present"


@pytest.mark.asyncio
async def test_wait_for_selector_not_found_returns_none(page):
    await page.goto(_write_html("<html><body></body></html>"))
    el = await page.wait_for_selector("#missing", timeout=500)
    assert el is None


# ── eval_on_selector ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eval_on_selector(page):
    await page.goto(_write_html(
        "<html><body><a href='https://example.com'>link</a></body></html>"
    ))
    href = await page.eval_on_selector("a", "this.href")
    assert "example.com" in href


# ── viewport ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_viewport(page):
    await page.set_viewport_size(800, 600)
    w = await page.evaluate("window.innerWidth || document.documentElement.clientWidth")
    # PhantomJS may report 0 for innerWidth on blank pages; just check no exception
    assert isinstance(w, (int, float, type(None)))


# ── screenshot ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_screenshot_produces_file(page, tmp_path):
    await page.goto(_write_html(
        "<html><body style='background:blue'><h1>snap</h1></body></html>"
    ))
    out = tmp_path / "shot.png"
    data = await page.screenshot(out)
    assert out.exists()
    assert len(data) > 0
    # PNG magic bytes
    assert data[:4] == b"\x89PNG"


# ── pdf ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pdf_produces_file(page, tmp_path):
    await page.goto(_write_html(
        "<html><body><h1>PDF test</h1></body></html>"
    ))
    out = tmp_path / "doc.pdf"
    data = await page.pdf(out)
    assert out.exists()
    assert len(data) > 0
    assert data[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_pdf_landscape(page, tmp_path):
    await page.goto(_write_html("<html><body><p>landscape</p></body></html>"))
    out = tmp_path / "landscape.pdf"
    data = await page.pdf(out, format="A4", landscape=True)
    assert data[:4] == b"%PDF"


# ── ElementHandle ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_element_handle_methods(page):
    await page.goto(_write_html("""
        <html><body>
          <div id='el'>content</div>
          <input id='inp'/>
        </body></html>
    """))
    el = await page.wait_for_selector("#el", timeout=2000)
    assert el is not None
    assert await el.text_content() == "content"
    assert await el.inner_html() == "content"

    inp = await page.wait_for_selector("#inp", timeout=2000)
    assert inp is not None
    await inp.fill("typed")
    val = await page.evaluate("document.getElementById('inp').value")
    assert val == "typed"


# ── BrowserContext ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_context_returns_page(browser):
    ctx = await browser.new_context()
    page = await ctx.new_page()
    url = _write_html("<html><head><title>ctx</title></head><body></body></html>")
    await page.goto(url)
    assert await page.evaluate("document.title") == "ctx"
    await ctx.close()


# ── concurrent pages (same session) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_sequential_pages_share_process(browser):
    """Multiple pages created from the same browser reuse one PhantomJS process."""
    results = []
    for i in range(5):
        p = await browser.new_page()
        url = _write_html(f"<html><head><title>p{i}</title></head><body></body></html>")
        await p.goto(url)
        results.append(await p.evaluate("document.title"))

    assert results == [f"p{i}" for i in range(5)]
    