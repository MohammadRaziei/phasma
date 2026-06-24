"""
Tests for phasma.svg.SvgRenderer — SVG to PNG/JPEG/PDF rendering.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
import pytest_asyncio

from phasma.svg import SvgRenderer


# ── sample SVGs ───────────────────────────────────────────────────────────────

SVG_SIMPLE = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <rect width="200" height="200" fill="blue"/>
  <circle cx="100" cy="100" r="60" fill="yellow"/>
  <text x="100" y="108" text-anchor="middle" font-size="18" fill="black">phasma</text>
</svg>"""

SVG_NO_DIMS = """<svg xmlns="http://www.w3.org/2000/svg">
  <rect width="100" height="100" fill="red"/>
</svg>"""

SVG_COMPLEX = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:rgb(255,0,0)"/>
      <stop offset="100%" style="stop-color:rgb(0,0,255)"/>
    </linearGradient>
  </defs>
  <rect width="400" height="300" fill="url(#grad)"/>
  <polygon points="200,20 380,280 20,280" fill="white" opacity="0.7"/>
  <text x="200" y="170" text-anchor="middle" font-size="24" font-weight="bold">SVG</text>
</svg>"""


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def renderer():
    """One SvgRenderer (= one PhantomJS process) shared across all tests."""
    async with SvgRenderer() as r:
        yield r


# ── helpers ───────────────────────────────────────────────────────────────────

def _png_dims(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    w = struct.unpack(">I", data[16:20])[0]
    h = struct.unpack(">I", data[20:24])[0]
    return w, h


# ── lifecycle ─────────────────────────────────────────────────────────────────

async def test_context_manager():
    async with SvgRenderer() as r:
        data = await r.to_png(SVG_SIMPLE)
        assert data[:4] == b"\x89PNG"


async def test_manual_start_close():
    r = SvgRenderer()
    await r.start()
    data = await r.to_png(SVG_SIMPLE)
    assert data[:4] == b"\x89PNG"
    await r.close()


async def test_not_started_raises():
    r = SvgRenderer()
    with pytest.raises(RuntimeError, match="not started"):
        await r.to_png(SVG_SIMPLE)


async def test_double_close_is_safe():
    r = SvgRenderer()
    await r.start()
    await r.close()
    await r.close()  # should not raise


# ── PNG ───────────────────────────────────────────────────────────────────────

async def test_to_png_returns_bytes(renderer):
    data = await renderer.to_png(SVG_SIMPLE)
    assert isinstance(data, bytes) and len(data) > 0


async def test_to_png_magic(renderer):
    assert (await renderer.to_png(SVG_SIMPLE))[:4] == b"\x89PNG"


async def test_to_png_correct_dimensions(renderer):
    w, h = _png_dims(await renderer.to_png(SVG_SIMPLE))
    assert w == 200 and h == 200


async def test_to_png_scale(renderer):
    w, h = _png_dims(await renderer.to_png(SVG_SIMPLE, scale=2.0))
    assert w == 400 and h == 400


async def test_to_png_writes_file(renderer, tmp_path):
    out = tmp_path / "out.png"
    data = await renderer.to_png(SVG_SIMPLE, output=out)
    assert out.exists() and data == out.read_bytes()


async def test_to_png_from_path_object(renderer, tmp_path):
    f = tmp_path / "test.svg"
    f.write_text(SVG_SIMPLE, encoding="utf-8")
    assert (await renderer.to_png(f))[:4] == b"\x89PNG"


async def test_to_png_from_file_string(renderer, tmp_path):
    f = tmp_path / "test.svg"
    f.write_text(SVG_SIMPLE, encoding="utf-8")
    assert (await renderer.to_png(str(f)))[:4] == b"\x89PNG"


async def test_to_png_no_dims_fallback(renderer):
    assert (await renderer.to_png(SVG_NO_DIMS))[:4] == b"\x89PNG"


async def test_to_png_complex(renderer):
    w, h = _png_dims(await renderer.to_png(SVG_COMPLEX))
    assert w == 400 and h == 300


async def test_to_png_batch_reuses_process(renderer):
    """Multiple renders on the same renderer should all succeed."""
    results = [await renderer.to_png(SVG_SIMPLE) for _ in range(5)]
    assert all(d[:4] == b"\x89PNG" for d in results)


# ── JPEG ──────────────────────────────────────────────────────────────────────

async def test_to_jpeg_magic(renderer):
    assert (await renderer.to_jpeg(SVG_SIMPLE))[:2] == b"\xff\xd8"


async def test_to_jpeg_writes_file(renderer, tmp_path):
    out = tmp_path / "out.jpg"
    data = await renderer.to_jpeg(SVG_SIMPLE, output=out)
    assert out.exists() and data[:2] == b"\xff\xd8"


async def test_to_jpeg_scale(renderer):
    data = await renderer.to_jpeg(SVG_SIMPLE, scale=0.5)
    assert data[:2] == b"\xff\xd8"


# ── PDF ───────────────────────────────────────────────────────────────────────

async def test_to_pdf_magic(renderer):
    assert (await renderer.to_pdf(SVG_SIMPLE))[:4] == b"%PDF"


async def test_to_pdf_writes_file(renderer, tmp_path):
    out = tmp_path / "out.pdf"
    data = await renderer.to_pdf(SVG_SIMPLE, output=out)
    assert out.exists() and data[:4] == b"%PDF"


async def test_to_pdf_landscape(renderer, tmp_path):
    data = await renderer.to_pdf(SVG_SIMPLE, pdf_landscape=True)
    assert data[:4] == b"%PDF"


async def test_to_pdf_custom_format(renderer):
    data = await renderer.to_pdf(SVG_SIMPLE, pdf_format="Letter")
    assert data[:4] == b"%PDF"


# ── phasma namespace ──────────────────────────────────────────────────────────

async def test_importable_from_phasma():
    import phasma
    assert hasattr(phasma, "SvgRenderer")


async def test_phasma_svg_renderer():
    import phasma
    async with phasma.SvgRenderer() as r:
        data = await r.to_png(SVG_SIMPLE)
        assert data[:4] == b"\x89PNG"
