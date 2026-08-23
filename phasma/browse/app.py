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
from .rawinput import read_key

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


def detect_char_size(fd: int) -> Optional[Tuple[int, int]]:
    """Ask the tty for its real pixel dimensions (TIOCGWINSZ) and derive the
    actual on-screen size of one character cell from them. This matters a
    lot: if the assumed cell size is wrong, every click lands on the wrong
    DOM coordinates even though the click mechanism itself works fine -
    which looks exactly like "clicking doesn't work". Not all terminals
    fill in the pixel fields (many report 0), in which case this returns
    None and the caller should fall back to a fixed default."""
    import fcntl
    import struct
    import termios

    try:
        packed = fcntl.ioctl(fd, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0))
        rows, cols, xpixel, ypixel = struct.unpack("HHHH", packed)
    except OSError:
        return None
    if not (rows and cols and xpixel and ypixel):
        return None
    char_w = max(1, xpixel // cols)
    char_h = max(1, ypixel // rows)
    return char_w, char_h

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


_HINT_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def _generate_hint_labels(n: int) -> list:
    """Short, easy-to-type labels for n targets: single letters first, then
    2-letter combinations once the alphabet is exhausted (vimium-style)."""
    if n <= 0:
        return []
    if n <= len(_HINT_ALPHABET):
        return list(_HINT_ALPHABET[:n])
    import itertools
    length = 2
    while len(_HINT_ALPHABET) ** length < n:
        length += 1
    return ["".join(c) for c in itertools.islice(itertools.product(_HINT_ALPHABET, repeat=length), n)]


def _normalize_url(url: str) -> str:
    if "://" not in url:
        return "https://" + url
    return url


class BrowseApp:
    DEBOUNCE_SECONDS = 0.35

    def __init__(self, term: "blessed.Terminal", char_w: int = DEFAULT_CHAR_W,
                 char_h: int = DEFAULT_CHAR_H) -> None:
        self.term = term
        self.char_w = char_w
        self.char_h = char_h
        self.browser = None
        self.page = None
        self.url: Optional[str] = None
        self.mode = "normal"  # normal | insert | visual | hint
        self.status = ""
        self.image_cache = ImageCache()
        self.grid = None
        self.selecting = False
        self.selection_start: Optional[Tuple[int, int]] = None
        self.selection_end: Optional[Tuple[int, int]] = None
        self.char_size_detected = False
        self.hint_targets: list = []  # [{id, x, y, w, h, tag, label}, ...]
        self.hint_input = ""
        self.pending_field: Optional[dict] = None  # rect/value snapshot of the focused field
        self.pending_value: Optional[str] = None    # locally-buffered, not-yet-sent value
        self.pending_task: Optional[asyncio.Task] = None

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
            if self.mode == "hint":
                out.append(self._render_with_hints())
            else:
                out.append(self._render_with_selection())
        out.append("\n")
        out.append(term.reverse(self._status_bar()[: self.cols].ljust(self.cols)))
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def _render_with_hints(self) -> str:
        base = self.grid.render_ansi()
        term = self.term
        overlay = [base]
        for h in self.hint_targets:
            label = h["label"]
            if self.hint_input and not label.startswith(self.hint_input):
                continue  # narrowed out - don't clutter the screen with non-matches
            row = int(h["y"] // self.char_h)
            col = int(h["x"] // self.char_w)
            if not (0 <= row < self.grid.rows and 0 <= col < self.grid.cols):
                continue
            text = label.upper()[: max(1, self.grid.cols - col)]
            overlay.append(term.move_xy(col, row) + term.black_on_yellow(text))
        return "".join(overlay)

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
        tag = {
            "normal": "", "insert": "-- INSERT --  ", "visual": "-- VISUAL (y=yank) --  ",
            "hint": f"-- HINT ({self.hint_input}) --  ",
        }[self.mode]
        size_note = f"{self.char_w}x{self.char_h}{'' if self.char_size_detected else '?'}"
        return f" {tag}{self.status}   [q]uit [u]rl [r]eload [v]isual [f]ollow  [{size_note}]"

    # ── link hints ───────────────────────────────────────────────────────────

    async def enter_hint_mode(self) -> None:
        raw = await self.page.hints()
        labels = _generate_hint_labels(len(raw))
        for target, label in zip(raw, labels):
            target["label"] = label
        self.hint_targets = raw
        self.hint_input = ""
        self.mode = "hint" if raw else "normal"
        if not raw:
            self.status = "No clickable elements in view"

    def hint_matches(self) -> list:
        return [h for h in self.hint_targets if h["label"].startswith(self.hint_input)]

    async def activate_hint(self, label: str) -> None:
        match = next((h for h in self.hint_targets if h["label"] == label), None)
        self.exit_hint_mode()
        if match is None:
            return
        await self.page.hint_click(match["id"])
        active = await self.page.active_element()
        if active and active.get("editable"):
            self.mode = "insert"
            self.pending_field = await self._fetch_active_field()
            self.pending_value = self.pending_field.get("value", "") if self.pending_field else None

    def exit_hint_mode(self) -> None:
        self.mode = "normal"
        self.hint_targets = []
        self.hint_input = ""

    # ── actions ──────────────────────────────────────────────────────────────

    async def click_at(self, col: int, row: int) -> None:
        # Switching targets while mid-edit must not silently drop what was typed.
        if self.mode == "insert" and self.pending_value is not None:
            self.cancel_pending_flush()
            await self.flush_pending_value()

        px_x, px_y = col * self.char_w, row * self.char_h
        await self.page.mouse_event("click", px_x, px_y)
        active = await self.page.active_element()
        if active and active.get("editable"):
            self.mode = "insert"
            self.pending_field = await self._fetch_active_field()
            self.pending_value = self.pending_field.get("value", "") if self.pending_field else None
        else:
            self.mode = "normal"
            self.pending_field = None
            self.pending_value = None

    async def scroll(self, dx: int = 0, dy: int = 0, *, absolute: bool = False) -> None:
        await self.page.scroll(dx=dx, dy=dy, absolute=absolute)

    async def _fetch_active_field(self) -> Optional[dict]:
        """The rect + current value + placeholder of document.activeElement,
        if it's an editable field. Uses the dedicated active_field RPC
        (function-reference based - works even on CSP-strict sites, unlike
        the generic string-based evaluate())."""
        return await self.page.active_field()

    def _patch_local_field_display(self) -> None:
        """Redraw just the focused field's cells from the local buffer -
        instant, no RPC. The real page isn't touched until a debounced
        flush fires or the field loses focus (see DEBOUNCE_SECONDS)."""
        if not (self.grid and self.pending_field is not None):
            return
        value = self.pending_value or ""
        if self.pending_field.get("isPassword"):
            value = "\u2022" * len(value)
        self.grid.place_fields([{**self.pending_field, "value": value, "focused": True}])

    def cancel_pending_flush(self) -> None:
        if self.pending_task is not None and not self.pending_task.done():
            self.pending_task.cancel()
        self.pending_task = None

    async def flush_pending_value(self) -> None:
        """Push the locally-buffered value to the real page in one RPC
        (instead of one round-trip per keystroke), firing input/change so
        page JS (search-as-you-type, validation, ...) still sees it. Uses
        the dedicated set_active_value RPC - the generic string-based
        evaluate() calls eval() internally and is silently blocked by any
        page whose CSP lacks 'unsafe-eval' (most real production sites)."""
        if self.pending_value is None:
            return
        try:
            await self.page.set_active_value(self.pending_value)
        except Exception:  # noqa: BLE001 - best-effort; a stale/gone element shouldn't crash the app
            pass

    async def _debounced_flush(self) -> None:
        try:
            await asyncio.sleep(self.DEBOUNCE_SECONDS)
        except asyncio.CancelledError:
            return
        await self.flush_pending_value()
        await self.refresh_grid()
        self.draw()

    def schedule_flush(self) -> None:
        self.cancel_pending_flush()
        self.pending_task = asyncio.ensure_future(self._debounced_flush())

    async def local_type_char(self, ch: str) -> None:
        """Echo a character instantly with no network round-trip; the real
        page is updated after DEBOUNCE_SECONDS of no typing, or immediately
        on Enter/Escape/Tab/click-elsewhere."""
        if self.pending_value is None:
            await self.page.send_key(text=ch)  # no field info available - fall back to direct send
            return
        self.pending_value += ch
        self._patch_local_field_display()
        self.schedule_flush()

    async def local_backspace(self) -> None:
        if self.pending_value is None:
            await self.page.send_key(special="Backspace")
            return
        self.pending_value = self.pending_value[:-1]
        self._patch_local_field_display()
        self.schedule_flush()

    async def type_char(self, ch: str) -> None:
        await self.page.send_key(text=ch)

    async def special_key(self, name: str) -> None:
        await self.page.send_key(special=name)

    async def exit_insert(self) -> None:
        self.cancel_pending_flush()
        await self.flush_pending_value()
        await self.page.blur_active()
        self.mode = "normal"
        self.pending_field = None
        self.pending_value = None

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
    fd = sys.stdin.fileno()
    buf = app.url or ""
    while True:
        sys.stdout.write(
            term.move_xy(0, app.content_rows) + term.reverse((" URL: " + buf)[: app.cols].ljust(app.cols))
        )
        sys.stdout.flush()
        key = await loop.run_in_executor(None, read_key, fd, None)
        if key is None:
            continue
        if key.name == "KEY_ENTER":
            return buf.strip() or None
        if key.name == "KEY_ESCAPE":
            return None
        if key.name == "KEY_BACKSPACE":
            buf = buf[:-1]
        elif str(key).isprintable():
            buf += str(key)


async def _handle_key(app: BrowseApp, key, loop: asyncio.AbstractEventLoop):
    """Returns "quit" to exit, True if a full refresh+redraw is needed,
    "local" if only a redraw is needed (state already patched locally, no
    RPC - see local_type_char/local_backspace), or False for no change."""
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
            if app.mode == "hint":
                app.exit_hint_mode()
            if app.mode == "visual":
                if ev["pressed"] and app.selection_start is None:
                    app.selection_start = (ev["row"], ev["col"])
                app.selection_end = (ev["row"], ev["col"])
                return True
            if ev["pressed"]:
                await app.click_at(ev["col"], ev["row"])
                return True
        return False

    if app.mode == "hint":
        if key.name == "KEY_ESCAPE":
            app.exit_hint_mode()
            return True
        if key.name == "KEY_BACKSPACE":
            app.hint_input = app.hint_input[:-1]
            return "local"
        if seq and seq.isalpha():
            candidate = app.hint_input + seq.lower()
            matches = [h for h in app.hint_targets if h["label"].startswith(candidate)]
            if not matches:
                return False  # not a valid next character - ignore, keep current input
            app.hint_input = candidate
            if len(matches) == 1 and matches[0]["label"] == app.hint_input:
                await app.activate_hint(app.hint_input)
                return True
            return "local"
        return False

    if app.mode == "insert":
        if key.name == "KEY_ESCAPE":
            await app.exit_insert()
            return True
        if key.name == "KEY_BACKSPACE":
            await app.local_backspace()
            return "local"
        if key.name == "KEY_ENTER":
            app.cancel_pending_flush()
            await app.flush_pending_value()
            await app.special_key("Enter")  # let page JS (submit/search-on-Enter) react too
            return True
        if key.name == "KEY_TAB":
            app.cancel_pending_flush()
            await app.flush_pending_value()
            await app.special_key("Tab")
            return True
        if key.name in _SPECIAL_KEY_NAMES:
            app.cancel_pending_flush()
            await app.flush_pending_value()
            await app.special_key(_SPECIAL_KEY_NAMES[key.name])
            return True
        if seq and seq.isprintable():
            await app.local_type_char(seq)
            return "local"
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
    if seq == "f":
        await app.enter_hint_mode()
        return True

    return await _handle_normal_movement(app, key)


# ── entry point ──────────────────────────────────────────────────────────────

async def run(url: str, char_w: Optional[int] = None, char_h: Optional[int] = None) -> None:
    if blessed is None:
        raise RuntimeError(
            "The `browse` extra is required for `phasma browse`. "
            "Install it with: pip install 'phasma[browse]'"
        )
    term = blessed.Terminal()
    fd = sys.stdin.fileno()

    detected = detect_char_size(fd) if (char_w is None or char_h is None) else None
    resolved_w = char_w if char_w is not None else (detected[0] if detected else DEFAULT_CHAR_W)
    resolved_h = char_h if char_h is not None else (detected[1] if detected else DEFAULT_CHAR_H)

    app = BrowseApp(term, char_w=resolved_w, char_h=resolved_h)
    app.char_size_detected = detected is not None
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
                key = await loop.run_in_executor(None, read_key, fd, 0.3)

                if (term.width, term.height) != last_size:
                    last_size = (term.width, term.height)
                    await app.resize_viewport()
                    await app.refresh_grid()
                    app.draw()
                    continue

                if key is None:
                    continue

                result = await _handle_key(app, key, loop)
                if result == "quit":
                    break
                if result == "local":
                    pass  # already patched app.grid directly - just redraw
                elif result:
                    await app.refresh_grid()
                app.draw()
        finally:
            sys.stdout.write(_MOUSE_OFF)
            sys.stdout.flush()
            if app.mode == "insert":
                app.cancel_pending_flush()
                try:
                    await app.flush_pending_value()
                except Exception:  # noqa: BLE001 - best-effort on the way out
                    pass
            await app.stop()


def main(url: str, char_w: Optional[int] = None, char_h: Optional[int] = None) -> None:
    """Synchronous entry point used by the `phasma browse` CLI subcommand.
    char_w/char_h of None means: auto-detect from the terminal's real pixel
    size (falls back to an 8x17 guess if the terminal doesn't report one)."""
    asyncio.run(run(url, char_w=char_w, char_h=char_h))
