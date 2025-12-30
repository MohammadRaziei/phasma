"""
Example showing how to use the new Playwright-like API for web scraping.
"""
import asyncio
import tempfile

import phasma


async def scrape_example():
    """Example of scraping data from a webpage."""

    browser = await phasma.launch()

    try:
        page = await browser.new_page()

        # Navigate to a page (using example.com for this demo)
        print("Navigating to example.com...")
        await page.goto("http://example.com")

        # Extract various elements
        title = await page.text_content("h1")
        print(f"Main heading: {title}")

        # Get page title (simpler evaluation)
        page_title = await page.evaluate("document.title")
        print(f"Page title: {page_title}")

        # Get the main heading again to verify page state
        main_heading = await page.text_content("h1")
        print(f"Main heading: {main_heading}")

        # Get paragraph text
        paragraph_text = await page.text_content("p")
        print(f"Paragraph text: {paragraph_text[:100]}...")  # First 100 chars

        # Take a screenshot of the page
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name

        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")

    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_example())
