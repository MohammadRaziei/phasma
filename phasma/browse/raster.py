"""
Turns a rasterized <img> region into a grid of terminal half-block cells.
This is the ONLY thing that gets rasterized — real page text never goes
through here (see grid.py).

Technique: each terminal cell shows two vertically-stacked source pixels via
the upper-half-block glyph '▀' — its foreground paints the top pixel, its
background paints the bottom pixel, doubling vertical resolution. A pixel
with negligible alpha produces neither fg nor bg, letting the terminal's own
background show through untouched.
"""
from __future__ import annotations

import base64
import io
import urllib.parse
import urllib.request
from typing import List, Optional, Tuple, Union

try:
    from PIL import Image
except ImportError:  # pragma: no cover - guarded by the `browse` extra
    Image = None

RGB = Tuple[int, int, int]
PixelGrid = List[List[Tuple[Optional[RGB], Optional[RGB]]]]

_FETCH_TIMEOUT = 5.0
_USER_AGENT = "Mozilla/5.0 (compatible; phasma-browse)"


def require_pillow() -> None:
    if Image is None:
        raise RuntimeError(
            "Pillow is required for image rendering in `phasma browse`. "
            "Install it with: pip install 'phasma[browse]'"
        )


def fetch_image_bytes(src: str) -> Optional[bytes]:
    """Fetch an <img>'s own source bytes directly - preserving its real
    alpha channel, unlike a page screenshot (which bakes transparency into
    whatever the page's background happens to be at that spot). Returns
    None on any failure (protected resource, bad URL, timeout, ...) so the
    caller can fall back to a page screenshot instead."""
    if not src:
        return None
    try:
        if src.startswith("data:"):
            _, _, payload = src.partition(",")
            if ";base64" in src.split(",", 1)[0]:
                return base64.b64decode(payload)
            return urllib.parse.unquote_to_bytes(payload)
        req = urllib.request.Request(src, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            return resp.read()
    except Exception:
        return None


def image_to_halfblock_grid(image_source: Union[str, bytes], cols: int, rows: int) -> PixelGrid:
    """Resize the image (a file path, or raw bytes from fetch_image_bytes)
    to (cols, rows*2) px and return a rows x cols grid of (fg, bg) RGB
    pairs, one per terminal cell. A pixel with alpha <= 10 contributes
    neither fg nor bg, so real transparency shows through as the
    terminal's own background rather than an opaque color."""
    require_pillow()
    if cols <= 0 or rows <= 0:
        return []
    source = io.BytesIO(image_source) if isinstance(image_source, (bytes, bytearray)) else image_source
    img = Image.open(source).convert("RGBA")
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
