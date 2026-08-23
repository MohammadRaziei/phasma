"""
Playwright-like async API for phasma.
All page operations are thin async wrappers around DriverPersistent._rpc(),
which does a single HTTP POST to the long-lived PhantomJS process.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .driver import DriverPersistent


# ── helpers ───────────────────────────────────────────────────────────────────

def _escape_js_string(s: Any) -> str:
    """Escape a value for safe embedding in a JS string literal."""
    if s is None:
        return "null"
    s = str(s)
    return (
        s.replace("\\", "\\\\")
         .replace("'", "\\'")
         .replace('"', '\\"')
         .replace("\n", "\\n")
         .replace("\r", "\\r")
    )


# ── exceptions ────────────────────────────────────────────────────────────────

class Error(Exception):
    """Base error class for phasma browser errors."""


class TimeoutError(Error):
    """Raised when an operation exceeds its timeout."""


# ── ElementHandle ─────────────────────────────────────────────────────────────

class ElementHandle:
    """Thin handle to a DOM element — delegates back to the Page."""

    def __init__(self, page: "Page", selector: str) -> None:
        self._page = page
        self._selector = selector

    async def click(self) -> None:
        await self._page.click(self._selector)

    async def fill(self, value: str) -> None:
        await self._page.fill(self._selector, value)

    async def text_content(self) -> str:
        return await self._page.text_content(self._selector)

    async def inner_html(self) -> str:
        return await self._page.inner_html(self._selector)


# ── Page ──────────────────────────────────────────────────────────────────────

class Page:
    """Represents a browser page.  All methods are async."""

    def __init__(self, driver: DriverPersistent) -> None:
        self._driver = driver
        self._url: Optional[str] = None
        self._viewport: Dict[str, int] = {"width": 1024, "height": 768}

    # navigation ---------------------------------------------------------------

    async def goto(
        self,
        url: str,
        *,
        wait_until: str = "load",
        timeout: int = 30_000,
        wait_ms: int = 0,
    ) -> Optional[str]:
        """Navigate to *url*.  Returns the page's outer HTML."""
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            lambda: self._driver.navigate(url, wait_ms=wait_ms, timeout=timeout / 1000.0),
        )
        self._url = url
        return content

    async def set_viewport_size(self, width: int, height: int) -> None:
        self._viewport = {"width": width, "height": height}
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.set_viewport(width, height),
        )

    # JS / DOM -----------------------------------------------------------------

    async def evaluate(self, expression: str) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.evaluate(expression),
        )

    async def text_content(self, selector: str) -> str:
        # Use a sentinel to distinguish "element not found" from "element has empty text".
        # PhantomJS serializes JS null as an empty string, so we can't use null directly.
        result = await self.evaluate(
            f"(function(){{"
            f"  var el = document.querySelector('{_escape_js_string(selector)}');"
            f"  return el ? ('__found__' + el.textContent) : '__notfound__';"
            f"}})()"
        )
        if result == "__notfound__" or result is None:
            raise Error(f"Element not found: {selector!r}")
        return result[len("__found__"):]

    async def inner_html(self, selector: str) -> str:
        result = await self.evaluate(
            f"(function(){{"
            f"  var el = document.querySelector('{_escape_js_string(selector)}');"
            f"  return el ? ('__found__' + el.innerHTML) : '__notfound__';"
            f"}})()"
        )
        if result == "__notfound__" or result is None:
            raise Error(f"Element not found: {selector!r}")
        return result[len("__found__"):]

    async def eval_on_selector(self, selector: str, expression: str) -> Any:
        # Check element existence separately so we can raise a proper error.
        exists = await self.evaluate(
            f"document.querySelector('{_escape_js_string(selector)}') !== null"
        )
        if not exists:
            raise Error(f"Element not found: {selector!r}")
        return await self.evaluate(
            f"(function(){{"
            f"  var el = document.querySelector('{_escape_js_string(selector)}');"
            f"  return (function(){{ return {expression}; }}).call(el);"
            f"}})()"
        )

    # interaction --------------------------------------------------------------

    async def click(self, selector: str) -> None:
        loop = asyncio.get_event_loop()
        found = await loop.run_in_executor(
            None,
            lambda: self._driver.click(selector),
        )
        if not found:
            raise Error(f"Element not found: {selector!r}")

    async def fill(self, selector: str, value: str) -> None:
        loop = asyncio.get_event_loop()
        found = await loop.run_in_executor(
            None,
            lambda: self._driver.fill(selector, value),
        )
        if not found:
            raise Error(f"Element not found: {selector!r}")

    async def wait_for_selector(
        self,
        selector: str,
        *,
        timeout: int = 30_000,
    ) -> Optional[ElementHandle]:
        deadline = asyncio.get_event_loop().time() + timeout / 1000.0
        while asyncio.get_event_loop().time() < deadline:
            # evaluate returns a bool — PhantomJS serializes true/false correctly
            exists = await self.evaluate(
                f"!!document.querySelector('{_escape_js_string(selector)}')"
            )
            if exists is True or exists == "true":
                return ElementHandle(self, selector)
            await asyncio.sleep(0.1)
        return None

    # terminal-browser primitives ------------------------------------------------

    async def layout(self) -> Dict:
        """Return the current viewport's layout: real text runs (never
        rasterized) plus the bounding boxes of <img> elements only."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.get_layout(),
        )

    async def scroll(self, dx: int = 0, dy: int = 0, *, absolute: bool = False) -> Dict:
        """Scroll by (dx, dy), or to (dx, dy) if absolute=True. Returns the new scroll position."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.scroll(dx, dy, absolute=absolute),
        )

    async def region_screenshot(self, path: Union[str, Path], left: int, top: int,
                                 width: int, height: int) -> bytes:
        """Render only a sub-rectangle of the viewport to PNG (used for <img> regions)."""
        path = Path(path)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.region_screenshot(path, left, top, width, height),
        )
        return path.read_bytes()

    async def mouse_event(self, type: str, x: int, y: int, button: str = "left") -> None:
        """Dispatch a mouse event at viewport coordinates. type: click|mousedown|mouseup|mousemove|doubleclick."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.mouse_event(type, x, y, button),
        )

    async def send_key(self, text: Optional[str] = None, special: Optional[str] = None) -> None:
        """Type *text* into the focused element, or send a *special* key
        (Backspace, Enter, Tab, Left, Right, Up, Down, Escape, Delete, Home, End)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.send_key(text=text, special=special),
        )

    async def active_element(self) -> Optional[Dict]:
        """Return {tag, editable, type} for document.activeElement, or None."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.active_element(),
        )

    async def active_field(self) -> Optional[Dict]:
        """Rect + current value + placeholder of the focused <input>/<textarea>,
        or None. Works via a function-reference RPC action, so unlike the
        generic string-based evaluate() it isn't blocked by a page's CSP."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.active_field(),
        )

    async def set_active_value(self, value: str) -> bool:
        """Set the focused element's value in one round trip, firing input/change."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.set_active_value(value),
        )

    async def blur_active(self) -> None:
        """Blur document.activeElement, if any."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.blur_active(),
        )

    # link hints -------------------------------------------------------------

    async def hints(self) -> list:
        """Tag every clickable/focusable element in the viewport and return
        a list of {id, x, y, w, h, tag} for each (vimium-style link hints)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.get_hints(),
        )

    async def hint_click(self, hint_id: str) -> None:
        """Click the element previously tagged with *hint_id* by hints()."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.hint_click(hint_id),
        )

    async def clear_hints(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.clear_hints(),
        )

    # media --------------------------------------------------------------------

    async def screenshot(
        self,
        path: Union[str, Path],
        *,
        full_page: bool = False,
        type: str = "png",
        quality: int = 100,
    ) -> bytes:
        path = Path(path)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.take_screenshot(path),
        )
        return path.read_bytes()

    async def pdf(
        self,
        path: Union[str, Path],
        *,
        format: Optional[str] = "A4",
        landscape: bool = False,
        margin: Union[str, Dict[str, str]] = "1cm",
        width: Optional[str] = None,
        height: Optional[str] = None,
    ) -> bytes:
        """Render the current page to a PDF.
        
        Use width/height (e.g. '400px', '297mm') for pixel-exact output,
        or format (e.g. 'A4', 'Letter') for standard paper sizes.
        """
        path = Path(path)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._driver.generate_pdf(
                path, format=format, landscape=landscape,
                margin=margin, width=width, height=height,
            ),
        )
        return path.read_bytes()


# ── BrowserContext ────────────────────────────────────────────────────────────

class BrowserContext:
    """Groups pages that share the same PhantomJS session."""

    def __init__(self, browser: "Browser") -> None:
        self._browser = browser
        self._pages: list[Page] = []

    async def new_page(self) -> Page:
        page = Page(self._browser._driver)
        self._pages.append(page)
        return page

    async def close(self) -> None:
        self._pages.clear()


# ── Browser ───────────────────────────────────────────────────────────────────

class Browser:
    """One Browser == one persistent PhantomJS process."""

    def __init__(self, driver: DriverPersistent) -> None:
        self._driver = driver
        self._contexts: list[BrowserContext] = []
        self._closed = False

    async def new_context(self, options: Optional[Dict] = None) -> BrowserContext:
        ctx = BrowserContext(self)
        self._contexts.append(ctx)
        return ctx

    async def new_page(self) -> Page:
        ctx = await self.new_context()
        return await ctx.new_page()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for ctx in self._contexts:
            await ctx.close()
        self._contexts.clear()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._driver.close)

    def is_connected(self) -> bool:
        return not self._closed


# ── top-level factory ─────────────────────────────────────────────────────────

async def launch(options: Optional[Dict] = None) -> Browser:
    """Launch a new PhantomJS browser session."""
    driver = DriverPersistent()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, driver.start_persistent_session)
    return Browser(driver)


async def connect(options: Optional[Dict] = None) -> Browser:
    """Alias for launch (PhantomJS has no remote attach support)."""
    return await launch(options)
