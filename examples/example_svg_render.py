"""
example_svg_render.py
─────────────────────
Shows how to use phasma.svg.SvgRenderer to convert SVG to PNG, JPEG, and PDF
with different scales, backgrounds, and paper formats.

Run:
    python examples/example_svg_render.py
"""

import asyncio
from pathlib import Path

from phasma.svg import SvgRenderer


# ── sample SVGs ───────────────────────────────────────────────────────────────

SVG_CHART = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="100%" style="stop-color:#16213e"/>
    </linearGradient>
  </defs>
  <rect width="400" height="300" fill="url(#bg)" rx="12"/>

  <!-- bars -->
  <rect x="40"  y="200" width="50" height="70"  fill="#e94560" rx="4"/>
  <rect x="110" y="150" width="50" height="120" fill="#0f3460" rx="4"/>
  <rect x="180" y="100" width="50" height="170" fill="#533483" rx="4"/>
  <rect x="250" y="130" width="50" height="140" fill="#e94560" rx="4"/>
  <rect x="320" y="80"  width="50" height="190" fill="#0f3460" rx="4"/>

  <!-- labels -->
  <text x="65"  y="290" text-anchor="middle" font-size="11" fill="#aaa">Jan</text>
  <text x="135" y="290" text-anchor="middle" font-size="11" fill="#aaa">Feb</text>
  <text x="205" y="290" text-anchor="middle" font-size="11" fill="#aaa">Mar</text>
  <text x="275" y="290" text-anchor="middle" font-size="11" fill="#aaa">Apr</text>
  <text x="345" y="290" text-anchor="middle" font-size="11" fill="#aaa">May</text>

  <text x="200" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="white">Monthly Sales</text>
</svg>"""

SVG_ICON = """<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <circle cx="32" cy="32" r="30" fill="#3498db" stroke="white" stroke-width="2"/>
  <polygon points="26,20 26,44 46,32" fill="white"/>
</svg>"""

SVG_LOGO = """<svg xmlns="http://www.w3.org/2000/svg" width="300" height="100">
  <rect width="300" height="100" fill="#2c3e50" rx="10"/>
  <circle cx="50" cy="50" r="28" fill="#e74c3c"/>
  <circle cx="50" cy="50" r="18" fill="#2c3e50"/>
  <text x="90" y="42" font-size="22" font-weight="bold" fill="white" font-family="sans-serif">phasma</text>
  <text x="90" y="65" font-size="12" fill="#95a5a6" font-family="sans-serif">headless browser · pip install only</text>
</svg>"""


async def main():
    out = Path("svg_output")
    out.mkdir(exist_ok=True)

    # also save SVGs to disk so we can demonstrate file-based input
    (out / "chart.svg").write_text(SVG_CHART, encoding="utf-8")
    (out / "icon.svg").write_text(SVG_ICON,  encoding="utf-8")
    (out / "logo.svg").write_text(SVG_LOGO,  encoding="utf-8")

    # one SvgRenderer = one PhantomJS process reused for all conversions
    async with SvgRenderer() as r:

        # ── 1. basic conversions ──────────────────────────────────────────────
        print("── basic conversions ──")

        png  = await r.to_png(SVG_CHART,  out / "chart.png")
        jpg  = await r.to_jpeg(SVG_CHART, out / "chart.jpg")
        pdf  = await r.to_pdf(SVG_CHART,  out / "chart.pdf")

        print(f"  PNG   {len(png):>8,} bytes  →  chart.png")
        print(f"  JPEG  {len(jpg):>8,} bytes  →  chart.jpg")
        print(f"  PDF   {len(pdf):>8,} bytes  →  chart.pdf")

        # ── 2. scale — same SVG, different resolutions ────────────────────────
        print("\n── scale (chart PNG at different resolutions) ──")

        scales = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
        for scale in scales:
            path = out / f"chart_scale_{scale}x.png"
            data = await r.to_png(SVG_CHART, path, scale=scale)
            # original SVG is 400×300 — compute expected output size
            ew, eh = round(400 * scale), round(300 * scale)
            print(f"  scale={scale}x  expected {ew}×{eh}px  →  {path.name}  ({len(data):,} bytes)")

        # ── 3. icon at multiple sizes (typical asset pipeline) ────────────────
        print("\n── icon export at common sizes ──")

        icon_sizes = [
            ("favicon",   0.25),   # 16×16
            ("small",     0.5),    # 32×32
            ("standard",  1.0),    # 64×64
            ("medium",    2.0),    # 128×128
            ("large",     4.0),    # 256×256
            ("xlarge",    8.0),    # 512×512
        ]

        for label, scale in icon_sizes:
            path = out / f"icon_{label}.png"
            data = await r.to_png(out / "icon.svg", path, scale=scale)
            px = round(64 * scale)
            print(f"  {label:<10} {px}×{px}px  →  {path.name}  ({len(data):,} bytes)")

        # ── 4. background options ─────────────────────────────────────────────
        print("\n── background variants ──")

        backgrounds = [
            ("white",       "white"),
            ("transparent", "transparent"),
            ("dark",        "#1a1a2e"),
            ("light_gray",  "#f5f5f5"),
        ]

        for label, bg in backgrounds:
            path = out / f"logo_bg_{label}.png"
            data = await r.to_png(SVG_LOGO, path, background=bg)
            print(f"  background={bg:<12}  →  {path.name}  ({len(data):,} bytes)")

        # ── 5. JPEG quality tradeoff (scale affects effective resolution) ─────
        print("\n── JPEG at different scales ──")

        for scale in [0.5, 1.0, 2.0]:
            path = out / f"chart_jpeg_scale_{scale}x.jpg"
            data = await r.to_jpeg(SVG_CHART, path, scale=scale, background="white")
            print(f"  scale={scale}x  →  {path.name}  ({len(data):,} bytes)")

        # ── 6. PDF paper formats and orientation ──────────────────────────────
        print("\n── PDF formats ──")

        pdf_variants = [
            ("A4 portrait",  "A4",     False, "0"),
            ("A4 landscape", "A4",     True,  "0"),
            ("Letter",       "Letter", False, "0"),
            ("A3",           "A3",     False, "0"),
            ("with margin",  "A4",     False, "1cm"),
        ]

        for label, fmt, landscape, margin in pdf_variants:
            filename = f"chart_{label.replace(' ', '_')}.pdf"
            path = out / filename
            data = await r.to_pdf(
                SVG_CHART, path,
                pdf_format=fmt,
                pdf_landscape=landscape,
                pdf_margin=margin,
            )
            print(f"  {label:<16}  →  {filename}  ({len(data):,} bytes)")

        # ── 7. input from file path (string and Path object) ──────────────────
        print("\n── input from file ──")

        data = await r.to_png(str(out / "logo.svg"), out / "logo_from_str_path.png")
        print(f"  from str path  →  logo_from_str_path.png  ({len(data):,} bytes)")

        data = await r.to_png(out / "logo.svg", out / "logo_from_path_obj.png")
        print(f"  from Path obj  →  logo_from_path_obj.png  ({len(data):,} bytes)")

        # ── 8. raw bytes without saving to disk ───────────────────────────────
        print("\n── in-memory (no output file) ──")

        png_bytes = await r.to_png(SVG_ICON, scale=4.0)
        jpg_bytes = await r.to_jpeg(SVG_ICON, scale=4.0, background="white")
        pdf_bytes = await r.to_pdf(SVG_CHART)

        print(f"  PNG bytes  : {len(png_bytes):,}")
        print(f"  JPEG bytes : {len(jpg_bytes):,}")
        print(f"  PDF bytes  : {len(pdf_bytes):,}")

    print(f"\n✓ all outputs saved to ./{out}/")
    print(f"  {len(list(out.glob('*')))} files generated")


if __name__ == "__main__":
    asyncio.run(main())
