# phasma browse

A [browsh](https://github.com/philc/browsh)-like terminal browser, powered
by PhantomJS instead of Firefox. Real page text is drawn as real terminal
characters — only `<img>` elements are ever turned into ASCII/ANSI block
art. Because PhantomJS renders headless natively (no GPU, no X server, no
`xvfb-run`), it runs on a bare server or container that browsh/Firefox
can't.

```
$ phasma browse https://pypi.org
```

## Install

```bash
pip install 'phasma[browse]'
```

This installs `blessed` (terminal control), `Pillow` (image rendering), and
`pyperclip` (clipboard yank). The core RPCs this feature depends on
(`layout`, `hints`, `scroll`, `mouse`, `key`, ...) ship with plain
`phasma` — no extra needed for those.

The first run downloads the PhantomJS binary automatically, the same way
every other `phasma` command does.

## Usage

```bash
phasma browse <url>              # scheme optional, defaults to https://
phasma browse <url> --char-size 9x19   # override the auto-detected cell size
```

`--char-size WxH` sets the assumed pixel size of one terminal character
cell. By default this is auto-detected from the terminal's real pixel
dimensions (`TIOCGWINSZ`); pass it explicitly if your terminal doesn't
report pixel size (common over some SSH/tmux setups) or if clicks are
landing in the wrong place. The status bar shows the size in use, with a
`?` suffix when it's the unverified 8x17 fallback rather than a detected
value.

## Keys

**Normal mode**

| Key(s) | Action |
|---|---|
| `j` / `k` / `↓` / `↑` | scroll down / up |
| `h` / `l` / `←` / `→` | scroll left / right |
| `Space` / `PgDn` | page down |
| `b` / `PgUp` | page up |
| `g` / `Home` | scroll to top |
| `G` | scroll to bottom |
| mouse click | click the element under the cursor |
| mouse wheel | scroll |
| `f` | **link hints** — label every clickable/focusable element; type the label to activate it (see below) |
| `v` | enter visual (selection) mode |
| `u` | type a new URL |
| `r` | reload |
| `q` | quit |

**Link hints** (`f`) — press `f`, a short label (`a`, `b`, ... `aa`, `ab`,
...) appears over every link, button, and form field in view. Type the
label to click that element via JS (`element.click()`), which sidesteps
pixel-coordinate guessing entirely. `Backspace` removes the last typed
character, `Esc` cancels. Clicking a text field this way drops straight
into insert mode, same as clicking it with the mouse.

**Insert mode** (after clicking/hinting into a text field or textarea)

| Key(s) | Action |
|---|---|
| any printable key | typed instantly, shown locally (no network round trip) |
| *(pause ~350ms)* | buffered text is sent to the page in one request, firing `input`/`change` |
| `Enter` | sends the buffered text immediately, then a real Enter keypress (so search-on-Enter, form submit, etc. still fire) |
| `Tab` | sends immediately, then Tab |
| `Backspace` | edits the local buffer |
| `Esc` | sends immediately, exits insert mode |

**Visual mode** (`v`)

| Key(s) | Action |
|---|---|
| movement keys, or click-drag | extend the selection |
| `y` | yank the selection to the system clipboard (needs `xclip`/`xsel`/`pbcopy` on the OS side for `pyperclip` to actually reach the clipboard) |
| `v` / `Esc` | cancel |

## How it works, briefly

- `layout()` walks the page's DOM once per redraw and returns real text as
  whole-word runs (position, color, bold/italic/underline) plus, sepa­rately,
  just the bounding boxes of `<img>` elements — never a screenshot of text.
- `phasma/browse/grid.py` places those words into a terminal character
  grid; `raster.py` turns each `<img>` (fetched directly, to preserve real
  transparency) into upper-half-block (`▀`) cells — 2 source pixels per
  cell.
- `compose.py` also takes one full-viewport screenshot per redraw and uses
  it as ground truth to fill in any cell's background (handles gradients
  and multi-section pages correctly, not just one flat guessed color) and
  to fix any text that would otherwise be unreadable against its own
  background — see **Known limitations** below for why that's needed.
- Typing, hint-clicking, and reading a focused field's value all go
  through dedicated function-reference RPC actions rather than a
  generic "run this JS string" call — the latter depends on `eval()`,
  which is blocked outright on any page whose CSP lacks `unsafe-eval`
  (most real production sites, GitHub and PyPI included).

## Known limitations

These come from PhantomJS's rendering engine itself (an old WebKit,
last updated around 2016) — not something a rendering tweak on our side
can fix:

- **No CSS custom properties.** `color: var(--x)` silently resolves to an
  invalid/default value instead of the site's real one. This is common
  enough on modern dark-themed sites (GitHub among them) that
  `phasma browse` actively detects and works around the resulting
  unreadable text (see `compose.py`'s contrast fix) — but the *exact*
  color a real browser would show may still differ from what
  PhantomJS reports.
- **Modern JS-heavy single-page apps may render blank.** Sites built with
  a framework that uses newer JS syntax than this engine parses (seen on
  crates.io, for example) can fail to boot their UI, leaving just the
  empty HTML shell.
- **Bot-detection challenge pages** (Cloudflare's "Just a moment..." and
  similar) will often block PhantomJS outright, the same way they block
  most non-mainstream browsers.
- Horizontal text reflow, CSS Grid, and other newer layout features may
  not compute exactly the way a current browser would.

None of the above are silent — `phasma browse` will still show *something*
(the real, if sometimes-wrong, rendering PhantomJS produces) rather than
crashing.

## Testing

```bash
pytest tests/test_browse.py
```

Includes pure-logic unit tests (color parsing, grid placement, contrast
fixing, hint-label generation, mouse-sequence parsing) that need no
browser, and integration tests that drive a real PhantomJS instance.
