"""
phasma.svg — SVG rendering without any extra dependencies.

Uses the bundled PhantomJS engine. One SvgRenderer instance = one persistent
PhantomJS process, reused across all conversions.

Usage
-----
    import asyncio
    from phasma.svg import SvgRenderer

    async def main():
        async with SvgRenderer() as r:
            png = await r.to_png("<svg ...>...</svg>")
            jpg = await r.to_jpeg(Path("diagram.svg"), scale=2.0)
            await r.to_pdf(Path("chart.svg"), output="chart.pdf")

    asyncio.run(main())

    # or manually:
    r = SvgRenderer()
    await r.start()
    data = await r.to_png(svg)
    await r.close()
"""

from __future__ import annotations

import asyncio
import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Union

import phasma.browser as _browser


# ── SVG helpers ───────────────────────────────────────────────────────────────

def _read_svg(source: Union[str, Path]) -> str:
    """Accept a Path object, a .svg file path string, or a raw SVG string."""
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    p = Path(source)
    if p.suffix.lower() == ".svg" and p.is_file():
        return p.read_text(encoding="utf-8")
    return source


def _parse_dimensions(svg_text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract width/height from the root <svg> tag.
    Falls back to viewBox when width/height are missing or non-numeric (e.g. "100%").
    """
    m = re.search(r"<svg[^>]*>", svg_text, re.DOTALL)
    if not m:
        return None, None

    tag = m.group(0)

    def _attr_int(name: str) -> Optional[int]:
        am = re.search(rf'{name}\s*=\s*["\']([^"\']+)["\']', tag)
        if not am:
            return None
        val = am.group(1).strip().rstrip("px").strip()
        try:
            v = int(float(val))
            return v if v > 0 else None
        except ValueError:
            return None  # "100%", "auto", etc.

    w = _attr_int("width")
    h = _attr_int("height")

    # fallback: viewBox="x y w h"
    if w is None or h is None:
        vb = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', tag)
        if vb:
            parts = vb.group(1).strip().split()
            if len(parts) == 4:
                try:
                    w = w or int(float(parts[2]))
                    h = h or int(float(parts[3]))
                except ValueError:
                    pass

    return w, h


def _make_responsive(svg_text: str) -> str:
    """
    Replace fixed width/height on the root <svg> with 100% so the element
    fills whatever viewport PhantomJS is given.  viewBox is preserved (or
    added from the original dimensions) so the content scales correctly.
    """
    m = re.search(r"<svg([^>]*)>", svg_text, re.DOTALL)
    if not m:
        return svg_text

    attrs = m.group(1)

    # extract original dims to build a viewBox if one is missing
    def _num(name: str) -> Optional[int]:
        am = re.search(rf'{name}\s*=\s*["\']([^"\']+)["\']', attrs)
        if not am:
            return None
        try:
            return int(float(am.group(1).strip().rstrip("px")))
        except ValueError:
            return None

    orig_w, orig_h = _num("width"), _num("height")

    new_attrs = attrs

    # add viewBox before stripping width/height
    if "viewBox" not in attrs and orig_w and orig_h:
        new_attrs += f' viewBox="0 0 {orig_w} {orig_h}"'

    # replace fixed dimensions with 100%
    new_attrs = re.sub(r'\s*width\s*=\s*["\'][^"\']*["\']',  ' width="100%"',  new_attrs, count=1)
    new_attrs = re.sub(r'\s*height\s*=\s*["\'][^"\']*["\']', ' height="100%"', new_attrs, count=1)

    # if there were no width/height attrs at all, add them
    if 'width="100%"' not in new_attrs:
        new_attrs += ' width="100%"'
    if 'height="100%"' not in new_attrs:
        new_attrs += ' height="100%"'

    return svg_text[:m.start()] + f"<svg{new_attrs}>" + svg_text[m.end():]


def _svg_to_html(svg_text: str, background: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ background: {background}; overflow: hidden; width: 100%; height: 100%; }}
  svg {{ display: block; width: 100%; height: 100%; }}
</style>
</head>
<body>{svg_text}</body>
</html>"""


# ── SvgRenderer ───────────────────────────────────────────────────────────────

class SvgRenderer:
    """
    Persistent SVG renderer backed by a single PhantomJS process.

    Use as an async context manager (recommended):

        async with SvgRenderer() as r:
            png = await r.to_png(svg_string)
            pdf = await r.to_pdf(Path("diagram.svg"), output="out.pdf")

    Or manage lifecycle manually:

        r = SvgRenderer()
        await r.start()
        data = await r.to_png(svg)
        await r.close()
    """

    def __init__(self) -> None:
        self._browser: Optional[_browser.Browser] = None
        self._page: Optional[_browser.Page] = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> "SvgRenderer":
        """Launch the PhantomJS process and prepare the page."""
        self._browser = await _browser.launch()
        self._page = await self._browser.new_page()
        return self

    async def close(self) -> None:
        """Shut down the PhantomJS process."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None

    async def __aenter__(self) -> "SvgRenderer":
        return await self.start()

    async def __aexit__(self, *_) -> None:
        await self.close()

    # ── internal render ───────────────────────────────────────────────────────

    async def _render(
        self,
        source: Union[str, Path],
        output: Optional[Union[str, Path]],
        fmt: str,
        scale: float,
        background: str,
        pdf_format: str,
        pdf_landscape: bool,
        pdf_margin: str,
    ) -> bytes:
        if self._page is None:
            raise RuntimeError("SvgRenderer is not started. Use 'async with' or call start() first.")

        svg_text = _read_svg(source)
        w, h = _parse_dimensions(svg_text)

        vp_w = max(1, round(w * scale)) if w else 1280
        vp_h = max(1, round(h * scale)) if h else 960

        svg_text = _make_responsive(svg_text)
        html = _svg_to_html(svg_text, background)
        await self._page.set_viewport_size(vp_w, vp_h)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as f:
            f.write(html)
            url = Path(f.name).as_uri()

        await self._page.goto(url, wait_ms=50)

        if output:
            out_path = Path(output)
        else:
            suffix = ".jpg" if fmt == "jpeg" else f".{fmt}"
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp.close()
            out_path = Path(tmp.name)

        if fmt == "pdf":
            if pdf_format is None:
                # fit mode: paper = SVG dimensions exactly
                pw = f"{vp_w}px"
                ph = f"{vp_h}px"
                return await self._page.pdf(
                    out_path, margin=pdf_margin,
                    width=pw, height=ph,
                )
            else:
                return await self._page.pdf(
                    out_path,
                    format=pdf_format,
                    landscape=pdf_landscape,
                    margin=pdf_margin,
                )
        else:
            if fmt == "jpeg" and out_path.suffix.lower() not in (".jpg", ".jpeg"):
                out_path = out_path.with_suffix(".jpg")
            return await self._page.screenshot(out_path)

    # ── public methods ────────────────────────────────────────────────────────

    async def to_png(
        self,
        source: Union[str, Path],
        output: Optional[Union[str, Path]] = None,
        *,
        scale: float = 1.0,
        background: str = "white",
    ) -> bytes:
        """
        Render SVG to PNG.

        Parameters
        ----------
        source:     SVG string, path string, or Path object.
        output:     Optional file path to write the result.
        scale:      Size multiplier (e.g. 2.0 for 2× resolution).
        background: CSS color for the page background.

        Returns the PNG bytes.
        """
        return await self._render(source, output, "png", scale, background, "A4", False, "0")

    async def to_jpeg(
        self,
        source: Union[str, Path],
        output: Optional[Union[str, Path]] = None,
        *,
        scale: float = 1.0,
        background: str = "white",
    ) -> bytes:
        """
        Render SVG to JPEG.

        Parameters
        ----------
        source:     SVG string, path string, or Path object.
        output:     Optional file path to write the result.
        scale:      Size multiplier.
        background: CSS color (use a solid color — JPEG has no transparency).

        Returns the JPEG bytes.
        """
        return await self._render(source, output, "jpeg", scale, background, "A4", False, "0")

    async def to_pdf(
        self,
        source: Union[str, Path],
        output: Optional[Union[str, Path]] = None,
        *,
        scale: float = 1.0,
        background: str = "white",
        pdf_format: Optional[str] = None,
        pdf_landscape: bool = False,
        pdf_margin: str = "0",
    ) -> bytes:
        """
        Render SVG to PDF.

        By default (pdf_format=None), the paper size matches the SVG dimensions
        exactly — no white borders, no cropping.

        Parameters
        ----------
        source:         SVG string, path string, or Path object.
        output:         Optional file path to write the result.
        scale:          Size multiplier applied to the SVG dimensions.
        background:     CSS color for the page background.
        pdf_format:     Standard paper format e.g. "A4", "Letter".
                        Pass None (default) to use the SVG's own dimensions.
        pdf_landscape:  Landscape orientation (only used with pdf_format).
        pdf_margin:     CSS margin string (e.g. "0", "1cm").
        """
        return await self._render(
            source, output, "pdf", scale, background,
            pdf_format, pdf_landscape, pdf_margin,
        )
    