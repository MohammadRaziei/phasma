# phasma terminal browser — status report

Goal: add an optional `phasma browse <url>` mode that turns phasma into a
browsh-like terminal browser, using PhantomJS's built-in engine instead of
Firefox. Text must stay real text in the terminal (real ANSI-colored
characters) — only `<img>` regions get rasterized to ASCII/ANSI block art.
Needs scroll, click, text selection, and input filling.

## Done

- Cloned the repo, downloaded the PhantomJS binary the same way the project
  does it (its own GitHub Releases URL in `driver/download.py`), no manual
  workaround.
- Added a `layout` RPC action to `driver/phantom_server.js`: walks the DOM,
  returns real text as text (per visual "run" — text + x/y/w/h + color/bg/
  bold/italic/underline, computed via per-character `Range.getClientRects()`),
  and separately the bounding boxes of `<img>` elements only. Everything is
  viewport-relative and pre-filtered so off-screen nodes are skipped cheaply.
- Added RPC actions: `scroll`, `mouse` (click/mousedown/mouseup/mousemove by
  coordinate), `key` (type text or send special keys: Backspace, Enter, Tab,
  arrows, Escape, Delete, Home, End), `region_screenshot` (renders only a
  sub-rectangle — used exclusively for `<img>` regions), `active_element`
  (detects whether an input/textarea is focused, for switching to "insert
  mode" in the TUI).
- Found and fixed a real PhantomJS engine bug: a `function` declared *inside*
  a `while` loop body hangs the process silently (no error, no output).
  Bisected it in ~8 steps. Fixed by inlining the logic instead of a nested
  function declaration.
- Tested all of the above against the real PhantomJS binary (not mocked):
  layout extraction (colors/bold/underline all correct), scroll, coordinate
  click, typing + backspace into an `<input>`, region screenshot.
- Added public wrapper methods on `DriverPersistent`: `get_layout()`,
  `scroll()`, `region_screenshot()`, `mouse_event()`, `send_key()`,
  `active_element()`. These are core phasma additions — no new dependency.

## Remaining

- Expose the same methods on the async `Page` class in `browser.py`.
- Build the `phasma/browse/` package:
  - convert `layout` JSON into a terminal character grid (text runs placed
    by cell, CSS color → ANSI truecolor)
  - rasterize `<img>` regions to ANSI half-block art (Pillow)
  - main TUI loop (blessed): scroll (arrows/mouse wheel), click (mouse),
    typing into focused inputs, visual-mode text selection + copy
- Add the `browse` extra to `pyproject.toml` (`blessed`, `Pillow`,
  `pyperclip` — gates only the TUI/rendering half; the DOM/layout RPCs stay
  dependency-free in core).
- Add `phasma browse <url>` subcommand to `__main__.py`.
- End-to-end test against a real website.
