"""
Example showing how to use multiple pages and contexts with the Playwright-like API.
"""
import asyncio
from pathlib import Path

import phasma


async def multi_page_example():
    """Example of using multiple pages and contexts."""

    browser = await phasma.launch()

    try:
        # Create a new context
        context1 = await browser.new_context()

        # Create pages in the first context
        page1 = await context1.new_page()
        page2 = await context1.new_page()

        # Navigate to different URLs in each page
        print("Navigating to different pages...")
        await page1.goto("http://example.com")
        await page2.goto("https://httpbin.org/html")  # Another simple HTML page

        # Get titles from both pages
        title1 = await page1.evaluate("document.title")
        title2 = await page2.evaluate("document.title")
        print(f"Page 1 title: {title1}")
        print(f"Page 2 title: {title2}")

        # Create a second context (though PhantomJS doesn't truly isolate contexts like modern browsers)
        context2 = await browser.new_context()
        page3 = await context2.new_page()

        await page3.goto("https://httpbin.org/json")  # JSON response page
        page3_title = await page3.evaluate("document.title")
        print(f"Page 3 title: {page3_title}")

        # Get content from all pages
        content1 = await page1.text_content("h1")
        content2 = await page2.text_content("h1")

        print(f"Page 1 H1: {content1}")
        print(f"Page 2 H1: {content2}")

        # Close the second context
        await context2.close()

        # Take screenshots of each page
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot1_path = f.name
        await page1.screenshot(path=screenshot1_path)
        print(f"Screenshot 1 saved: {screenshot1_path}")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot2_path = f.name
        await page2.screenshot(path=screenshot2_path)
        print(f"Screenshot 2 saved: {screenshot2_path}")

    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(multi_page_example())
