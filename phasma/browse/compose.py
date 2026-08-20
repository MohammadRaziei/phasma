"""
Glues a live phasma Page to the grid/raster modules: fetches layout(), places
text runs directly, then rasterizes each <img> region (with caching, since
most images are static across redraws) and places those.
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Dict

from .grid import TerminalGrid
from .raster import image_to_halfblock_grid

_TMP_DIR = Path(tempfile.gettempdir()) / "phasma-browse"
_TMP_DIR.mkdir(exist_ok=True)


class ImageCache:
    """Caches rasterized <img> screenshots by (src, on-screen size) so a
    redraw triggered by e.g. typing in an unrelated field doesn't re-render
    every image on the page again."""

    def __init__(self) -> None:
        self._cache: Dict[str, object] = {}

    async def get_pixel_grid(self, page, src: str, left: int, top: int,
                              width: int, height: int, cols: int, rows: int):
        key = f"{src}|{cols}x{rows}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        digest = hashlib.sha1(key.encode("utf-8", "ignore")).hexdigest()[:16]
        path = _TMP_DIR / f"{digest}.png"
        try:
            await page.region_screenshot(path, left, top, width, height)
            grid = image_to_halfblock_grid(str(path), cols, rows)
        except Exception:
            grid = []
        self._cache[key] = grid
        return grid

    def clear(self) -> None:
        self._cache.clear()


async def build_grid(page, cols: int, rows: int, char_w: int, char_h: int,
                      image_cache: ImageCache) -> TerminalGrid:
    """Fetch the current viewport's layout and build a ready-to-render grid."""
    layout = await page.layout()
    grid = TerminalGrid(cols=cols, rows=rows, char_w=char_w, char_h=char_h)

    # Text first (real characters, drawn as-is).
    grid.place_text_runs(layout.get("texts", []))

    # Form-control values next (never DOM text nodes - see grid.py).
    grid.place_fields(layout.get("fields", []))

    # Images last, so an image never gets hidden behind a stray background
    # cell but can still legitimately sit behind overlapping text.
    for img in layout.get("images", []):
        x, y, w, h = img["x"], img["y"], img["w"], img["h"]
        col0 = int(x // char_w)
        row0 = int(y // char_h)
        img_cols = max(1, round(w / char_w))
        img_rows = max(1, round(h / char_h))
        pixel_grid = await image_cache.get_pixel_grid(
            page, img.get("src", ""), int(x), int(y), int(w) or 1, int(h) or 1,
            img_cols, img_rows,
        )
        if pixel_grid:
            grid.place_image_grid(col0, row0, pixel_grid)

    grid.page_width = layout.get("pageWidth", 0)
    grid.page_height = layout.get("pageHeight", 0)
    grid.scroll_x = layout.get("scrollX", 0)
    grid.scroll_y = layout.get("scrollY", 0)
    grid.title = layout.get("title", "")
    return grid
