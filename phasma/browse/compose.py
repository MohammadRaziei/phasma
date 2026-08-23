"""
Glues a live phasma Page to the grid/raster modules: fetches layout(), places
text runs directly, then rasterizes each <img> region (with caching, since
most images are static across redraws) and places those.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Optional, Tuple

from .grid import TerminalGrid, parse_css_color
from .raster import fetch_image_bytes, image_to_halfblock_grid, require_pillow

try:
    from PIL import Image
except ImportError:  # pragma: no cover - guarded by the `browse` extra
    Image = None

RGB = Tuple[int, int, int]


class ImageCache:
    """Caches rasterized <img> pixel grids by (src, on-screen size) so a
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

        loop = asyncio.get_event_loop()
        grid = []
        try:
            # Prefer fetching the image's own bytes: this preserves real
            # transparency. A page screenshot of the region would instead
            # capture the already-composited (opaque) result, baking in
            # whatever the page's background happens to be behind it.
            data = await loop.run_in_executor(None, fetch_image_bytes, src)
            if data:
                grid = await loop.run_in_executor(None, image_to_halfblock_grid, data, cols, rows)
        except Exception:
            grid = []

        if not grid:
            # Fallback for images the direct fetch can't reach (auth-gated,
            # CORS, blob:/canvas-drawn content): screenshot the rendered
            # region instead. This loses true transparency but still shows
            # something rather than nothing.
            try:
                import hashlib
                import tempfile
                from pathlib import Path
                tmp_dir = Path(tempfile.gettempdir()) / "phasma-browse"
                tmp_dir.mkdir(exist_ok=True)
                digest = hashlib.sha1(key.encode("utf-8", "ignore")).hexdigest()[:16]
                path = tmp_dir / f"{digest}.png"
                await page.region_screenshot(path, left, top, width, height)
                grid = await loop.run_in_executor(None, image_to_halfblock_grid, str(path), cols, rows)
            except Exception:
                grid = []

        self._cache[key] = grid
        return grid

    def clear(self) -> None:
        self._cache.clear()


def _luminance(rgb: RGB) -> float:
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


_LOW_CONTRAST_THRESHOLD = 40.0  # out of a 0-255 luminance range


async def _capture_background_reference(page, grid: TerminalGrid):
    """One full-viewport screenshot, used as ground truth for every blank
    cell's background and for fixing any text that still doesn't contrast
    with its own background after CSS-based placement. Because this is a
    real screenshot rather than one sampled point (or one guessed page-wide
    color), it naturally handles non-solid backgrounds too - gradients,
    background images, several differently-colored sections on the same
    page - not just a single flat color assumed for the whole viewport.
    Costs exactly one RPC round trip regardless of page size or how many
    cells need it."""
    try:
        require_pillow()
    except RuntimeError:
        return None
    try:
        import hashlib
        import tempfile
        from pathlib import Path

        from PIL import Image

        tmp_dir = Path(tempfile.gettempdir()) / "phasma-browse"
        tmp_dir.mkdir(exist_ok=True)
        w_px = grid.cols * grid.char_w
        h_px = grid.rows * grid.char_h
        digest = hashlib.sha1(f"bgref-{w_px}x{h_px}".encode()).hexdigest()[:16]
        path = tmp_dir / f"{digest}.png"
        await page.region_screenshot(path, 0, 0, w_px, h_px)
        return Image.open(path).convert("RGB")
    except Exception:
        return None


def _pixel_at(ref_img, grid: TerminalGrid, row: int, col: int) -> Optional[RGB]:
    """Average a small block near the cell's top-left corner rather than
    reading one single pixel there. A single raw pixel picks up whatever
    local noise the real render happens to have right at that exact spot -
    anti-aliasing at a nearby edge, subpixel font hinting, faint gradient
    dithering - and renders as visible speckle/blotchiness instead of the
    smooth, uniform block a terminal cell should show. Averaging a few
    pixels smooths that out while still mostly avoiding a text cell's own
    glyph ink, which concentrates away from the very corner."""
    if ref_img is None:
        return None
    size = max(2, min(grid.char_w, grid.char_h) // 2)
    x0 = min(ref_img.width - 1, max(0, col * grid.char_w + 1))
    y0 = min(ref_img.height - 1, max(0, row * grid.char_h + 1))
    x1 = min(ref_img.width, x0 + size)
    y1 = min(ref_img.height, y0 + size)
    try:
        if x1 <= x0 or y1 <= y0:
            return ref_img.getpixel((x0, y0))
        region = ref_img.crop((x0, y0, x1, y1))
        return region.resize((1, 1), Image.BOX).getpixel((0, 0))
    except Exception:
        return None


def _fill_backgrounds_from_reference(ref_img, grid: TerminalGrid) -> None:
    """Every cell without an explicit CSS-derived background - blank or
    text alike - gets the real per-cell pixel color from the reference
    screenshot. This does two things at once: it's what makes gradients/
    background-images/local card sections render correctly instead of one
    guessed color for the whole page, and it gives every cell a real,
    per-cell-accurate background for the contrast check below to compare
    against - a cell whose text already reads fine against its true local
    background (e.g. dark text on a small white icon badge inside an
    otherwise dark page) must still end up with that white recorded as its
    own `bg`, or the renderer's fallback to the page's global background
    would silently make it unreadable again at render time even though
    this pass judged it fine."""
    if ref_img is None:
        return
    for r, row in enumerate(grid.cells):
        for c, cell in enumerate(row):
            if cell.bg is None:
                px = _pixel_at(ref_img, grid, r, c)
                if px is not None:
                    cell.bg = px


def _fix_low_contrast_text(grid: TerminalGrid) -> None:
    """Run after _fill_backgrounds_from_reference, so every cell already
    has a real, per-cell-accurate background to check against - no
    sampling needed here, just the contrast decision.

    A text cell's fg can still fail to contrast with that real background
    in one specific way: PhantomJS's rendering engine (ancient WebKit)
    doesn't support CSS custom properties (`var(--x)`) at all, so any
    color defined that way silently resolves to an invalid/default value
    instead of the site's real one - which can make an element's
    *foreground* itself genuinely wrong (GitHub's dark theme is a real
    example: text computes to black regardless of what's behind it).
    Sampling fixed the background; this fixes the one thing sampling
    can't - trading exact color fidelity for the property that matters
    most: being legible at all."""
    for row in grid.cells:
        for cell in row:
            if cell.ch == " " or cell.fg is None or cell.bg is None:
                continue
            if abs(_luminance(cell.fg) - _luminance(cell.bg)) < _LOW_CONTRAST_THRESHOLD:
                cell.fg = (255, 255, 255) if _luminance(cell.bg) < 128 else (0, 0, 0)


async def build_grid(page, cols: int, rows: int, char_w: int, char_h: int,
                      image_cache: ImageCache) -> TerminalGrid:
    """Fetch the current viewport's layout and build a ready-to-render grid."""
    layout = await page.layout()
    grid = TerminalGrid(cols=cols, rows=rows, char_w=char_w, char_h=char_h,
                         page_bg=parse_css_color(layout.get("pageBackground")))

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

    ref_img = await _capture_background_reference(page, grid)
    _fill_backgrounds_from_reference(ref_img, grid)
    _fix_low_contrast_text(grid)
    if grid.page_bg is None and ref_img is not None:
        grid.page_bg = _pixel_at(ref_img, grid, 0, 0)

    grid.page_width = layout.get("pageWidth", 0)
    grid.page_height = layout.get("pageHeight", 0)
    grid.scroll_x = layout.get("scrollX", 0)
    grid.scroll_y = layout.get("scrollY", 0)
    grid.title = layout.get("title", "")
    return grid
