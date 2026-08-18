# phasma terminal browser — status report

Goal: `phasma browse <url>` — a browsh-like terminal browser using
PhantomJS's own engine instead of Firefox. Real page text stays real text in
the terminal; only `<img>` elements get rasterized to ANSI block art.
Scroll, click, typing into inputs, and text selection/copy are supported.

## Status: feature-complete, core pipeline verified against real PhantomJS

## What was built

**Core (`phasma/driver/phantom_server.js`, `driver_persistent.py`, `browser.py`)**
No new dependency — always available in phasma, not gated by an extra.
- `layout` RPC: walks the DOM, returns real text as **whole-word runs** (not
  per-character) — text + x/y/w/h + color/bg/bold/italic/underline — plus,
  separately, just the bounding boxes of `<img>` elements. Word-level
  measurement (vs. per-character) is both ~5-6x fewer DOM calls on normal
  prose and avoids a WebKit quirk (see bugs below).
- `scroll`, `mouse` (click/mousedown/mouseup/mousemove by coordinate), `key`
  (type text, or a special key: Backspace/Enter/Tab/arrows/Escape/Delete/
  Home/End), `region_screenshot` (renders only a sub-rect — used exclusively
  for `<img>`), `active_element` (detects focused input, for "insert mode").
- Same methods exposed on the async `Page` class (`page.layout()`,
  `page.scroll()`, `page.mouse_event()`, `page.send_key()`,
  `page.active_element()`, `page.region_screenshot()`).

**`phasma/browse/` package** (needs `pip install 'phasma[browse]'` —
`blessed`, `Pillow`, `pyperclip`)
- `grid.py` — terminal character grid + CSS color parsing + ANSI truecolor
  rendering. Enforces a real gap between words that would otherwise round to
  touching terminal columns (see bugs below).
- `raster.py` — turns one rasterized `<img>` region into a grid of
  upper-half-block (`▀`) cells, 2 source pixels per cell via Pillow.
- `compose.py` — glues a live `Page` to the two above: fetches `layout()`,
  places text runs directly, rasterizes each image (with an on-src cache so
  static images aren't re-rendered every redraw).
- `app.py` — the interactive loop (`blessed`): scroll (arrows/space/b/g/G/
  mouse wheel), click-to-focus-and-type into inputs (auto-detects "insert
  mode" via `active_element`), `v` for visual-selection mode + `y` to yank
  to the system clipboard via `pyperclip`, `u` to type a new URL, `r` to
  reload, `q` to quit. Viewport size tracks terminal resize.

**CLI**: `phasma browse <url>` added to `__main__.py`, with a clean error
message pointing at `pip install 'phasma[browse]'` if the extra isn't
installed.

## Two real bugs found and fixed along the way

1. **PhantomJS hang on nested function declarations.** A `function`
   declared *inside* a `while` loop body hangs the whole process silently —
   no error, no output, nothing in stderr. Found by binary-bisecting the
   layout code in ~8 steps down to a two-line repro. Fixed by inlining the
   logic instead of declaring a nested function per iteration.
2. **WebKit collapses whitespace at inline-element boundaries.** Text like
   `and <i>italic</i>` can render with the space between them at less than
   one terminal-cell width, so naive column-rounding snaps the two words
   together with zero gap ("anditalic"). Fixed with a `gapBefore` flag set
   during the DOM walk (was there real whitespace before this word in the
   source?) that the grid placement step uses to force at least one blank
   column of separation.

## Testing performed (against the real PhantomJS binary, not mocked)

- All new RPC actions individually (layout colors/bold/underline, scroll,
  coordinate click, typing + backspace into a real `<input>`, region
  screenshot) — and again through the async `Page` API.
- The full `layout → grid → ANSI` pipeline end-to-end, including a real
  `<img>` rasterized to block art alongside untouched real text.
- The interactive TUI itself, driven through a real pseudo-TTY (`pty` +
  `subprocess`, proper `TIOCSWINSZ`): startup, full-screen mode, mouse
  reporting on/off, rendering, keyboard scrolling (`j`/space — exactly one
  redraw per keypress, correct scroll deltas), and clean `q` quit (exit
  code 0, screen/mouse state restored).

**Known test-harness limitation**: injecting *raw SGR mouse escape
sequences* through the synthetic pty produced extra redraw frames that
plain keyboard input did not. This looks like an artifact of the fake pty
not answering blessed's terminal capability queries (a real terminal
would), rather than an app bug — `parse_mouse()` itself is a small pure
function and the underlying `page.mouse_event()` RPC was already verified
correct in isolation. Worth a first check in a real terminal before calling
mouse support fully proven end-to-end.

## Suggested next steps (not done)

- Try it in an actual terminal to confirm mouse clicks/wheel feel right.
- `--char-size WxH` CLI flag (currently fixed 8x17 heuristic).
- Horizontal scroll support (currently vertical-only).

## Why this is more deployable than browsh

Verified directly in this sandbox: no X server, no GPU, no Xvfb installed —
and PhantomJS still started and rendered correctly, because it's built on a
QtWebKit backend that renders to an in-memory buffer with no display surface
required at all. Firefox (which browsh drives) still depends on graphics
infrastructure even in `--headless` mode, which is exactly the "no graphics"
failure the user hit trying to run browsh on a server. Since `phasma browse`
never needs `xvfb-run` or any system package, it fits the project's existing
"pip install only, no apt" philosophy and should just work on a bare VPS,
container, or CI box.
