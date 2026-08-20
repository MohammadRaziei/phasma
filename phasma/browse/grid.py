"""
Builds a terminal character grid out of a phasma Page.layout() result.

Design: text stays text. A layout "run" (a contiguous stretch of characters
on one visual line, as extracted by the `layout` RPC) is placed character by
character into terminal cells — never rasterized. Only pre-rasterized image
blocks (produced by raster.py from an <img> region) are written as colored
half-block glyphs. See raster.py for the image half.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

RGB = Tuple[int, int, int]

_RGB_RE = re.compile(
    r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)"
)


def parse_css_color(value: Optional[str]) -> Optional[RGB]:
    """Parse a computed-style color string ('rgb(...)' / 'rgba(...)').
    Returns None for transparent / fully-invisible colors (nothing to draw)."""
    if not value:
        return None
    m = _RGB_RE.match(value.strip())
    if not m:
        return None
    r, g, b = (int(float(m.group(i))) for i in (1, 2, 3))
    a = float(m.group(4)) if m.group(4) is not None else 1.0
    if a <= 0.0:
        return None
    clamp = lambda v: max(0, min(255, v))
    return (clamp(r), clamp(g), clamp(b))


@dataclass
class Cell:
    ch: str = " "
    fg: Optional[RGB] = None
    bg: Optional[RGB] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass
class TerminalGrid:
    cols: int
    rows: int
    char_w: int
    char_h: int
    cells: List[List[Cell]] = field(init=False)

    def __post_init__(self) -> None:
        self.cells = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]

    def set(self, row: int, col: int, cell: Cell) -> None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.cells[row][col] = cell

    def place_text_runs(self, texts: List[Dict]) -> None:
        """Place real text characters into cells. Never rasterizes text.

        Tracks the previous run's end column per row: when a run is flagged
        `gapBefore` (there was real whitespace before it in the source) but
        its measured x-position would make it visually touch the previous
        run, one column of separation is enforced. This compensates for a
        WebKit layout quirk where whitespace sitting exactly at an inline
        element boundary can collapse to zero width in the actual render,
        not just in isolated measurement.
        """
        last_end_col: Dict[int, int] = {}
        for run in texts:
            row = int(run["y"] // self.char_h)
            if row < 0 or row >= self.rows:
                continue
            start_col = int(round(run["x"] / self.char_w))
            if run.get("gapBefore") and row in last_end_col:
                # Guarantee at least one blank column of separation, not
                # merely "no overlap" — proportional-to-monospace rounding
                # can otherwise snap two adjacent words to touching columns
                # even though the source had real whitespace between them.
                start_col = max(start_col, last_end_col[row] + 2)
            fg = parse_css_color(run.get("color"))
            bg = parse_css_color(run.get("bg"))
            bold = bool(run.get("bold"))
            italic = bool(run.get("italic"))
            underline = bool(run.get("underline"))
            text = run.get("text", "")
            end_col = start_col
            for i, ch in enumerate(text):
                col = start_col + i
                end_col = col
                if col < 0 or col >= self.cols:
                    continue
                if ch == " " and bg is None:
                    # nothing to draw for a plain space - don't clobber
                    # anything already placed there (e.g. an image behind it)
                    continue
                if ch == "\t" or ord(ch) < 0x20:
                    continue
                self.set(row, col, Cell(ch, fg, bg, bold, italic, underline))
            last_end_col[row] = end_col

    def place_fields(self, fields: List[Dict]) -> None:
        """Draw <input>/<textarea> boxes: a background tint across the
        field's rect plus its current value (or a dimmed placeholder when
        empty). Needed because form-control content is native widget state,
        never a DOM text node — invisible to place_text_runs()."""
        PLACEHOLDER_FG = (120, 120, 120)
        DEFAULT_FIELD_BG = (40, 40, 40)
        DEFAULT_FIELD_FG = (230, 230, 230)
        CURSOR_BG = (255, 255, 255)
        CURSOR_FG = (0, 0, 0)

        for f in fields:
            x, y, w, h = f["x"], f["y"], f["w"], f["h"]
            row0 = int(y // self.char_h)
            col0 = int(x // self.char_w)
            cols = max(1, int(w // self.char_w))
            rows = max(1, int(h // self.char_h))
            bg = parse_css_color(f.get("bg")) or DEFAULT_FIELD_BG

            for r in range(rows):
                for c in range(cols):
                    self.set(row0 + r, col0 + c, Cell(" ", None, bg))

            value = f.get("value") or ""
            is_placeholder = not value
            text = f.get("placeholder", "") if is_placeholder else value
            fg = PLACEHOLDER_FG if is_placeholder else (parse_css_color(f.get("color")) or DEFAULT_FIELD_FG)

            inner_col0 = col0 + 1  # small left padding, matches typical native input padding
            inner_cols = max(1, cols - 2)
            lines = text.split("\n")[:rows] if text else []
            for li, line in enumerate(lines):
                for ci, ch in enumerate(line[:inner_cols]):
                    self.set(row0 + li, inner_col0 + ci, Cell(ch, fg, bg))

            if f.get("focused"):
                last_line = lines[-1] if lines else ""
                cursor_row = row0 + max(0, len(lines) - 1)
                cursor_col = inner_col0 + min(len(last_line), inner_cols)
                if cursor_row < row0 + rows:
                    self.set(cursor_row, cursor_col, Cell(" ", CURSOR_FG, CURSOR_BG))

    def place_image_grid(self, col0: int, row0: int,
                          pixels: List[List[Tuple[Optional[RGB], Optional[RGB]]]]) -> None:
        """pixels: rows x cols grid of (fg, bg) RGB pairs from raster.py,
        drawn as upper-half-block glyphs (2 vertical source pixels/cell)."""
        for r, row_pixels in enumerate(pixels):
            for c, (fg, bg) in enumerate(row_pixels):
                if fg is None and bg is None:
                    continue
                self.set(row0 + r, col0 + c, Cell("\u2580", fg, bg, False, False, False))

    def render_ansi(self) -> str:
        """Render the grid as an ANSI truecolor string, one line per row,
        minimizing escape codes by only emitting SGR on style changes."""
        RESET = "\x1b[0m"
        out_lines = []
        for row in self.cells:
            parts: List[str] = []
            last_style = None
            for cell in row:
                style = (cell.fg, cell.bg, cell.bold, cell.italic, cell.underline)
                if style != last_style:
                    codes = []
                    if cell.fg:
                        codes.append(f"38;2;{cell.fg[0]};{cell.fg[1]};{cell.fg[2]}")
                    if cell.bg:
                        codes.append(f"48;2;{cell.bg[0]};{cell.bg[1]};{cell.bg[2]}")
                    if cell.bold:
                        codes.append("1")
                    if cell.italic:
                        codes.append("3")
                    if cell.underline:
                        codes.append("4")
                    parts.append(RESET)
                    if codes:
                        parts.append("\x1b[" + ";".join(codes) + "m")
                    last_style = style
                parts.append(cell.ch)
            parts.append(RESET)
            out_lines.append("".join(parts))
        return "\n".join(out_lines)
