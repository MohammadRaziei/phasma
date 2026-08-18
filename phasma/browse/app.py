"""
The interactive terminal-browser loop: `phasma browse <url>`.

Text is drawn as real characters (see grid.py); only <img> regions are
rasterized (see raster.py). Supports scrolling (vertical and horizontal),
mouse clicks (including focusing & typing into inputs), and click-drag
text selection + yank.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Optional, Tuple

import phasma

from .compose import ImageCache, build_grid

try:
    import blessed
except ImportError:  # pragma: no cover - guarded by the `browse` extra
    blessed = None

try:
    import pyperclip
except ImportError:  # pragma: no cover - optional even within the `browse` extra
    pyperclip = None

DEFAULT_CHAR_W = 8
DEFAULT_CHAR_H = 17

_MOUSE_ON = "\x1b[?1000h\x1b[?1006h"
_MOUSE_OFF = "\x1b[?1000l\x1b[?1006l"

_SPECIAL_KEY_NAMES = {
    "KEY_BACKSPACE": "Backspace",
    "KEY_DELETE": "Delete",
    "KEY_ENTER": "Enter",
    "KEY_TAB": "Tab",
    "KEY_LEFT": "Left",
    "KEY_RIGHT": "Right",
    "KEY_UP": "Up",
    "KEY_DOWN": "Down",
    "KEY_ESCAPE": "Escape",
    "KEY_HOME": "Home",
    "KEY_END": "End",
}


def _normalize_url(url: str) -> str:
    if "://" not in url:
        return "https://" + url
    return url


class BrowseApp:
    def __init__(self, term: "blessed.Terminal", char_w: int = DEFAULT_CHAR_W,
                 char_h: int = DEFAULT_CHAR_H) -> None:
        self.term = term
        self.char_w = char_w
        self.char_h = char_h
        self.browser = None
        self.page = None
        self.url: Optional[str] = None
        self.mode = "normal"  # normal | insert | visual
        self.status = ""
        self.image_cache = ImageCache()
        self.grid = None
        self.selecting = False
        self.selection_start: Optional[Tuple[int, int]] = None
        self.selection_end: Optional[Tuple[int, int]] = None

    @property
    def content_rows(self) -> int:
        return max(1, self.term.height - 1)

    @property
    def cols(self) -> int:
        return max(1, self.term.width)

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self, url: str) -> None:
        self.browser = await phasma.launch()
        self.page = await self.browser.new_page()
        await self.navigate(url)

    async def stop(self) -> None:
        if self.browser:
            await self.browser.close()

    async def navigate(self, url: str) -> None:
        url = _normalize_url(url)
        self.url = url
        self.status = f"Loading {url} ..."
        self._draw_status_only()
        await self.page.set_viewport_size(self.cols * self.char_w, self.content_rows * self.char_h)
        try:
            await self.page.goto(url)
            self.status = url
        except Exception as exc:  # noqa: BLE001 - surfaced to the status bar, not fatal
            self.status = f"Failed to load {url}: {exc}"
        self.image_cache.clear()

    async def resize_viewport(self) -> None:
        await self.page.set_viewport_size(self.cols * self.char_w, self.content_rows * self.char_h)

    async def refresh_grid(self) -> None:
        self.grid = await build_grid(
            self.page, cols=self.cols, rows=self.content_rows,
            char_w=self.char_w, char_h=self.char_h, image_cache=self.image_cache,
        )

    # ── drawing ──────────────────────────────────────────────────────────────

    def draw(self) -> None:
        term = self.term
        out = [term.home]
        if self.grid:
            out.append(self._render_with_selection())
        out.append("\n")
        out.append(term.reverse(self._status_bar()[: self.cols].ljust(self.cols)))
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def _render_with_selection(self) -> str:
        if not (self.mode == "visual" and self.selection_start and self.selection_end):
            return self.grid.render_ansi()
        # cheap approach: render normally, then overlay a reverse-video
        # band for the selected rows/cols using cursor positioning.
        base = self.grid.render_ansi()
        term = self.term
        (r1, c1), (r2, c2) = sorted([self.selection_start, self.selection_end])
        overlay = [base]
        for r in range(r1, min(r2, self.grid.rows - 1) + 1):
            start = c1 if r == r1 else 0
            end = c2 if r == r2 else self.grid.cols - 1
            text = "".join(cell.ch for cell in self.grid.cells[r][start:end + 1])
            overlay.append(term.move_xy(start, r) + term.reverse(text))
        return "".join(overlay)

    def _draw_status_only(self) -> None:
        term = self.term
        sys.stdout.write(
            term.move_xy(0, self.content_rows)
            + term.reverse(self._status_bar()[: self.cols].ljust(self.cols))
        )
        sys.stdout.flush()

    def _status_bar(self) -> str:
        tag = {"normal": "", "insert": "-- INSERT --  ", "visual": "-- VISUAL (y=yank) --  "}[self.mode]
        return f" {tag}{self.status}   [q]uit [u]rl [r]eload [v]isual  h/l:scroll< > "

    # ── actions ──────────────────────────────────────────────────────────────

    async def click_at(self, col: int, row: int) -> None:
        px_x, px_y = col * self.char_w, row * self.char_h
        await self.page.mouse_event("click", px_x, px_y)
        active = await self.page.active_element()
        self.mode = "insert" if (active and active.get("editable")) else "normal"

    async def scroll(self, dx: int = 0, dy: int = 0, *, absolute: bool = False) -> None:
        await self.page.scroll(dx=dx, dy=dy, absolute=absolute)

    async def type_char(self, ch: str) -> None:
        await self.page.send_key(text=ch)

    async def special_key(self, name: str) -> None:
        await self.page.send_key(special=name)

    async def exit_insert(self) -> None:
        await self.page.evaluate(
            "document.activeElement && document.activeElement.blur && document.activeElement.blur();"
        )
        self.mode = "normal"

    def yank_selection(self) -> None:
        if not (self.selection_start and self.selection_end and self.grid):
            return
        (r1, c1), (r2, c2) = sorted([self.selection_start, self.selection_end])
        lines = []
        for r in range(r1, min(r2, self.grid.rows - 1) + 1):
            start = c1 if r == r1 else 0
            end = c2 if r == r2 else self.grid.cols - 1
            lines.append("".join(cell.ch for cell in self.grid.cells[r][start:end + 1]).rstrip())
        text = "\n".join(lines)
        if pyperclip is not None:
            try:
                pyperclip.copy(text)
                self.status = "Copied selection to clipboard"
                return
            except Exception:  # noqa: BLE001 - clipboard tools (xclip/xsel/pbcopy) may be missing
                pass
        preview = text if len(text) <= 60 else text[:57] + "..."
        self.status = f"Selected (install xclip/xsel to copy): {preview}"

    @staticmethod
    def parse_mouse(seq: str) -> Optional[dict]:
        """Parse an SGR mouse sequence body, e.g. '<0;12;5M'."""
        if not seq or seq[0] != "<":
            return None
        body, final = seq[1:-1], seq[-1]
        try:
            btn_s, x_s, y_s = body.split(";")
            return {"btn": int(btn_s), "col": int(x_s) - 1, "row": int(y_s) - 1, "pressed": final == "M"}
        except ValueError:
            return None


# ── key handling ────────────────────────────────────────────────────────────

async def _handle_normal_movement(app: BrowseApp, key) -> bool:
    s = str(key)
    v_step = app.char_h * 2
    h_step = app.char_w * 4
    page_step = app.content_rows * app.char_h

    if key.name == "KEY_DOWN" or s == "j":
        await app.scroll(dy=v_step)
        return True
    if key.name == "KEY_UP" or s == "k":
        await app.scroll(dy=-v_step)
        return True
    if key.name == "KEY_RIGHT" or s == "l":
        await app.scroll(dx=h_step)
        return True
    if key.name == "KEY_LEFT" or s == "h":
        await app.scroll(dx=-h_step)
        return True
    if s == " " or key.name == "KEY_PGDOWN":
        await app.scroll(dy=page_step)
        return True
    if s == "b" or key.name == "KEY_PGUP":
        await app.scroll(dy=-page_step)
        return True
    if s == "g" or key.name == "KEY_HOME":
        await app.scroll(dx=0, dy=0, absolute=True)
        return True
    if s == "G" and app.grid:
        await app.scroll(dy=app.grid.page_height, absolute=True)
        return True
    return False


async def _prompt_url(app: BrowseApp, loop: asyncio.AbstractEventLoop) -> Optional[str]:
    term = app.term
    buf = app.url or ""
    while True:
        sys.stdout.write(
            term.move_xy(0, app.content_rows) + term.reverse((" URL: " + buf)[: app.cols].ljust(app.cols))
        )
        sys.stdout.flush()
        key = await loop.run_in_executor(None, term.inkey)
        if key.name == "KEY_ENTER":
            return buf.strip() or None
        if key.name == "KEY_ESCAPE":
            return None
        if key.name == "KEY_BACKSPACE":
            buf = buf[:-1]
        elif str(key).isprintable():
            buf += str(key)


async def _handle_key(app: BrowseApp, key, loop: asyncio.AbstractEventLoop):
    """Returns True if a redraw+refresh is needed, "quit" to exit, False otherwise."""
    seq = str(key)

    if seq.startswith("\x1b[<"):
        ev = app.parse_mouse(seq[2:])
        if not ev:
            return False
        if ev["btn"] in (64, 65) and ev["pressed"]:
            await app.scroll(dy=-40 if ev["btn"] == 64 else 40)
            return True
        if ev["btn"] in (66, 67) and ev["pressed"]:  # shift+wheel: horizontal in most terminals
            await app.scroll(dx=-40 if ev["btn"] == 66 else 40)
            return True
        if ev["btn"] in (0, 1, 2):
            if app.mode == "visual":
                if ev["pressed"] and app.selection_start is None:
                    app.selection_start = (ev["row"], ev["col"])
                app.selection_end = (ev["row"], ev["col"])
                return True
            if ev["pressed"]:
                await app.click_at(ev["col"], ev["row"])
                return True
        return False

    if app.mode == "insert":
        if key.name == "KEY_ESCAPE":
            await app.exit_insert()
            return True
        if key.name == "KEY_BACKSPACE":
            await app.special_key("Backspace")
            return True
        if key.name == "KEY_ENTER":
            await app.special_key("Enter")
            return True
        if key.name == "KEY_TAB":
            await app.special_key("Tab")
            return True
        if key.name in _SPECIAL_KEY_NAMES:
            await app.special_key(_SPECIAL_KEY_NAMES[key.name])
            return True
        if seq and seq.isprintable():
            await app.type_char(seq)
            return True
        return False

    if app.mode == "visual":
        if seq == "v" or key.name == "KEY_ESCAPE":
            app.mode, app.selection_start, app.selection_end = "normal", None, None
            return True
        if seq == "y":
            app.yank_selection()
            app.mode = "normal"
            return True
        return await _handle_normal_movement(app, key)

    # normal mode
    if seq == "q":
        return "quit"
    if seq == "u":
        new_url = await _prompt_url(app, loop)
        if new_url:
            await app.navigate(new_url)
            return True
        return False
    if seq == "r":
        await app.navigate(app.url)
        return True
    if seq == "v":
        app.mode, app.selection_start, app.selection_end = "visual", None, None
        return True

    return await _handle_normal_movement(app, key)


# ── entry point ──────────────────────────────────────────────────────────────

async def run(url: str, char_w: int = DEFAULT_CHAR_W, char_h: int = DEFAULT_CHAR_H) -> None:
    if blessed is None:
        raise RuntimeError(
            "The `browse` extra is required for `phasma browse`. "
            "Install it with: pip install 'phasma[browse]'"
        )
    term = blessed.Terminal()
    app = BrowseApp(term, char_w=char_w, char_h=char_h)
    loop = asyncio.get_event_loop()

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        sys.stdout.write(_MOUSE_ON)
        sys.stdout.flush()
        try:
            await app.start(url)
            await app.refresh_grid()
            app.draw()

            last_size = (term.width, term.height)
            while True:
                key = await loop.run_in_executor(None, term.inkey, 0.3)

                if (term.width, term.height) != last_size:
                    last_size = (term.width, term.height)
                    await app.resize_viewport()
                    await app.refresh_grid()
                    app.draw()
                    continue

                if not key:
                    continue

                result = await _handle_key(app, key, loop)
                if result == "quit":
                    break
                if result:
                    await app.refresh_grid()
                app.draw()
        finally:
            sys.stdout.write(_MOUSE_OFF)
            sys.stdout.flush()
            await app.stop()


def main(url: str, char_w: int = DEFAULT_CHAR_W, char_h: int = DEFAULT_CHAR_H) -> None:
    """Synchronous entry point used by the `phasma browse` CLI subcommand."""
    asyncio.run(run(url, char_w=char_w, char_h=char_h))
