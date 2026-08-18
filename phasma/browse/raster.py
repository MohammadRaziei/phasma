"""
Turns a rasterized <img> region (a PNG captured by Page.region_screenshot)
into a grid of terminal half-block cells. This is the ONLY thing that gets
rasterized — real page text never goes through here (see grid.py).

Technique: each terminal cell shows two vertically-stacked source pixels via
the upper-half-block glyph '▀' — its foreground paints the top pixel, its
background paints the bottom pixel, doubling vertical resolution.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

try:
    from PIL import Image
except ImportError:  # pragma: no cover - guarded by the `browse` extra
    Image = None

RGB = Tuple[int, int, int]
PixelGrid = List[List[Tuple[Optional[RGB], Optional[RGB]]]]


def require_pillow() -> None:
    if Image is None:
        raise RuntimeError(
            "Pillow is required for image rendering in `phasma browse`. "
            "Install it with: pip install 'phasma[browse]'"
        )


def image_to_halfblock_grid(image_path: str, cols: int, rows: int) -> PixelGrid:
    """Resize the image at *image_path* to (cols, rows*2) px and return a
    rows x cols grid of (fg, bg) RGB pairs, one per terminal cell."""
    require_pillow()
    if cols <= 0 or rows <= 0:
        return []
    img = Image.open(image_path).convert("RGBA")
    img = img.resize((max(1, cols), max(1, rows * 2)), Image.LANCZOS)
    px = img.load()
    grid: PixelGrid = []
    for r in range(rows):
        row_out = []
        for c in range(cols):
            top = px[c, r * 2]
            bot = px[c, r * 2 + 1]
            fg = (top[0], top[1], top[2]) if top[3] > 10 else None
            bg = (bot[0], bot[1], bot[2]) if bot[3] > 10 else None
            row_out.append((fg, bg))
        grid.append(row_out)
    return grid
