"""
example_render_page.py
─────────────────────
Shows how to use phasma to render a web page:
  - navigate and extract content
  - take a screenshot at different viewport sizes
  - generate a PDF
  - render a local HTML file

Run:
    python examples/example_render_page.py
"""

import asyncio
from pathlib import Path

import phasma


# ── helper ────────────────────────────────────────────────────────────────────

SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>phasma render demo</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
    h1   { color: #2c3e50; }
    p    { line-height: 1.6; color: #555; }
    .box { background: #3498db; color: white; padding: 20px; border-radius: 8px; margin-top: 20px; }
  </style>
</head>
<body>
  <h1>Hello from phasma</h1>
  <p>This page was rendered by PhantomJS without installing Chrome, Node.js, or any system package.</p>
  <div class="box">
    <strong>pip install phasma</strong> — that's all it takes.
  </div>
</body>
</html>"""


async def main():
    out = Path("render_output").resolve()
    out.mkdir(exist_ok=True)

    # write sample HTML to disk so we can open it as a file URL
    html_file = out / "sample.html"
    html_file.write_text(SAMPLE_HTML, encoding="utf-8")

    browser = await phasma.launch()
    try:
        # ── 1. render a local HTML file ───────────────────────────────────────
        print("── rendering local HTML file ──")
        page = await browser.new_page()
        await page.goto(html_file.as_uri(), wait_ms=100)

        title   = await page.evaluate("document.title")
        heading = await page.text_content("h1")
        body    = await page.text_content(".box")
        print(f"  title  : {title}")
        print(f"  h1     : {heading}")
        print(f"  .box   : {body}")

        # ── 2. screenshot at different viewport sizes ──────────────────────────
        print("\n── screenshots at different viewports ──")

        viewports = [
            ("desktop",  1280, 800),
            ("tablet",    768, 1024),
            ("mobile",    390, 844),
        ]

        for name, w, h in viewports:
            await page.set_viewport_size(w, h)
            await page.goto(html_file.as_uri(), wait_ms=100)   # re-render at new size
            path = out / f"screenshot_{name}_{w}x{h}.png"
            data = await page.screenshot(path)
            print(f"  {name:<8} {w}x{h}  →  {path.name}  ({len(data):,} bytes)")

        # ── 3. PDF output ─────────────────────────────────────────────────────
        print("\n── PDF variants ──")
        await page.set_viewport_size(1280, 800)
        await page.goto(html_file.as_uri(), wait_ms=100)

        pdf_variants = [
            ("A4 portrait",  "a4_portrait.pdf",  "A4",     False, "1cm"),
            ("A4 landscape", "a4_landscape.pdf",  "A4",     True,  "1cm"),
            ("Letter",       "letter.pdf",         "Letter", False, "2cm"),
            ("no margin",    "no_margin.pdf",      "A4",     False, "0"),
        ]

        for label, filename, fmt, landscape, margin in pdf_variants:
            path = out / filename
            data = await page.pdf(path, format=fmt, landscape=landscape, margin=margin)
            print(f"  {label:<14}  →  {filename}  ({len(data):,} bytes)")

        # ── 4. extract rendered HTML ───────────────────────────────────────────
        print("\n── rendered HTML ──")
        await page.goto(html_file.as_uri(), wait_ms=100)
        rendered = await page.evaluate("document.documentElement.outerHTML")
        rendered_file = out / "rendered.html"
        rendered_file.write_text(rendered, encoding="utf-8")
        print(f"  saved {len(rendered):,} chars  →  {rendered_file.name}")

    finally:
        await browser.close()

    print(f"\n✓ all outputs saved to ./{out}/")


if __name__ == "__main__":
    asyncio.run(main())
