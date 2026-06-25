<div align="center">

<img src="https://github.com/MohammadRaziei/phasma/raw/master/docs/images/phasma.jpg" width="25%" style="min-width:180px" alt="Phasma"/>

# phasma

**Headless browser automation that works with `pip install` alone.**

No `apt`. No `npm`. No Chrome. No system dependencies.

[![PyPI](https://img.shields.io/pypi/v/phasma)](https://pypi.org/project/phasma/)
[![Python](https://img.shields.io/pypi/pyversions/phasma)](https://pypi.org/project/phasma/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

## Why phasma?

Most headless browser tools require installing Chrome, Chromium, or Node.js at the system level — which isn't always possible.

**phasma was built for environments where `apt` is locked but `pip` is open**: corporate servers, HPC clusters, minimal Docker images, restricted CI/CD pipelines. The PhantomJS binary ships inside the wheel. After `pip install phasma`, everything works immediately, no further setup required.

---

## Installation

```bash
pip install phasma
```

**Requirements:** Python 3.10+  
**Platforms:** Linux, macOS, Windows (x86 32-bit & 64-bit)

---

## Quick start

```python
import asyncio
import phasma

async def main():
    browser = await phasma.launch()
    try:
        page = await browser.new_page()
        await page.goto("https://example.com")

        title  = await page.evaluate("document.title")
        heading = await page.text_content("h1")
        print(title, heading)

        await page.screenshot(path="shot.png")
        await page.pdf(path="page.pdf")
    finally:
        await browser.close()

asyncio.run(main())
```

One persistent PhantomJS process handles every operation — no per-call restarts.

---

## Browser API

The API mirrors [Playwright](https://playwright.dev/python/) so it feels familiar.

### `launch()` / `connect()`

```python
browser = await phasma.launch()
```

### `Browser`

| Method | Returns | Description |
|---|---|---|
| `new_page()` | `Page` | Open a new page |
| `new_context(options?)` | `BrowserContext` | Create an isolated context |
| `close()` | — | Shut down the browser |
| `is_connected()` | `bool` | Whether the process is alive |

### `Page`

**Navigation**

```python
await page.goto(url, timeout=30_000, wait_ms=0)
await page.set_viewport_size(1280, 720)
```

**DOM / JavaScript**

```python
title   = await page.evaluate("document.title")
text    = await page.text_content("h1")
html    = await page.inner_html("#content")
result  = await page.eval_on_selector("a", "this.href")
element = await page.wait_for_selector(".loaded", timeout=5000)
```

**Interaction**

```python
await page.click("#submit")
await page.fill("#email", "user@example.com")
```

**Output**

```python
png_bytes = await page.screenshot("out.png")
pdf_bytes = await page.pdf("out.pdf", format="A4", landscape=False, margin="1cm")
```

### `ElementHandle`

```python
el = await page.wait_for_selector(".result")
await el.click()
await el.fill("value")
text = await el.text_content()
html = await el.inner_html()
```

### Errors

```python
phasma.Error        # base browser error
phasma.TimeoutError # operation exceeded timeout
```

---

## SVG Rendering

Convert SVG to PNG, JPEG, or PDF — no Inkscape, no cairosvg, no extra installs.

```python
from phasma.svg import SvgRenderer

async with SvgRenderer() as r:
    png = await r.to_png("<svg ...>...</svg>")
    jpg = await r.to_jpeg(Path("diagram.svg"), scale=2.0)
    pdf = await r.to_pdf("chart.svg", output="chart.pdf", pdf_landscape=True)
```

One `SvgRenderer` instance = one PhantomJS process reused across all conversions.

| Method | Options |
|---|---|
| `to_png(source, output?, scale?, background?)` | PNG bytes |
| `to_jpeg(source, output?, scale?, background?)` | JPEG bytes |
| `to_pdf(source, output?, scale?, pdf_format?, pdf_landscape?, pdf_margin?)` | PDF bytes — `pdf_format=None` fits paper to SVG size |

`source` accepts an SVG string, a file path string, or a `Path` object.

---

## Utility functions

For simple one-shot operations without managing a browser session:

```python
# render HTML
html = await phasma.render_page_content("<h1>Hello</h1>")
html = await phasma.render_url_content("https://example.com")

# execute JavaScript
result = await phasma.execute_js_script("1 + 1")

# screenshot / PDF
await phasma.take_screenshot("https://example.com", "out.png")
await phasma.generate_pdf("https://example.com", "out.pdf")

# sync versions (no asyncio.run needed)
html = phasma.sync_render_page_content("<h1>Hello</h1>")
phasma.sync_take_screenshot("https://example.com", "out.png")
```

---

## Examples

### Scraping

```python
async with phasma.launch() as browser:  # also works as context manager
    page = await browser.new_page()
    await page.goto("https://example.com")

    data = await page.evaluate("""({
        title: document.title,
        links: Array.from(document.querySelectorAll('a'))
                    .map(a => ({ text: a.textContent.trim(), href: a.href }))
    })""")
```

### Form interaction

```python
page = await browser.new_page()
await page.goto("https://example.com/login")
await page.fill("#username", "user@example.com")
await page.fill("#password", "secret")
await page.click("#submit")
await page.wait_for_selector(".dashboard")
```

### Batch screenshots

```python
browser = await phasma.launch()
try:
    for url in urls:
        page = await browser.new_page()
        await page.goto(url, timeout=15_000)
        name = url.replace("https://", "").replace("/", "_") + ".png"
        await page.screenshot(name)
finally:
    await browser.close()
```

### Batch SVG export

```python
svgs = Path("assets").glob("*.svg")

async with SvgRenderer() as r:
    for svg in svgs:
        await r.to_png(svg, output=svg.with_suffix(".png"), scale=2.0)
```

---

## CLI

```bash
# driver management
phasma driver --version
phasma driver --path
phasma driver download --force

# run a PhantomJS script directly
phasma driver exec script.js
phasma driver exec script.js --ssl --timeout 30

# render HTML to stdout or file
phasma render-page file.html
phasma render-page file.html -o out.html --viewport 1920x1080 --wait 500
phasma render-url https://example.com -o page.html --wait 2000

# execute JavaScript
phasma execjs "document.title"
phasma execjs -                          # read from stdin

# screenshot
phasma screenshot https://example.com shot.png --viewport 1280x720 --wait 1000

# PDF
phasma pdf https://example.com doc.pdf --format A4 --landscape --margin 2cm

# SVG conversion
phasma svg diagram.svg -o diagram.png
phasma svg diagram.svg -o diagram.png --scale 2.0
phasma svg diagram.svg -o diagram.jpg --format jpeg --background white
phasma svg diagram.svg -o diagram.pdf --format pdf
phasma svg diagram.svg -o diagram.pdf --format pdf --pdf-format A4 --landscape
phasma svg - -o out.png                  # read SVG from stdin
```

---

## Troubleshooting

**Installing from source** — binary is not bundled when cloning the repo. Run once:
```bash
phasma driver download
```

**Timeout errors** — increase the `timeout` parameter in `goto()` or `wait_for_selector()`.

**SSL errors** — set `OPENSSL_CONF=""` in your environment, or pass `--ssl-protocol=any` via CLI.

**Check binary path:**
```bash
phasma driver --path
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Contributing

1. Fork and create a feature branch
2. Add tests for new functionality
3. Run `pytest tests/` — all must pass
4. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">
<b>phasma</b> — headless browser automation, batteries included.
</div>
