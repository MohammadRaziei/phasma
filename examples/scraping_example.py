"""
Example showing how to use the new Playwright-like API for web scraping.
"""
import asyncio
import tempfile
from pathlib import Path

from phasma import launch, download_driver


async def scrape_example():
    """Example of scraping data from a webpage."""
    # Ensure PhantomJS driver is available
    download_driver()
    
    browser = await launch()
    
    try:
        page = await browser.new_page()
        
        # Navigate to a page (using example.com for this demo)
        print("Navigating to example.com...")
        await page.goto("http://example.com")
        
        # Extract various elements
        title = await page.text_content("h1")
        print(f"Main heading: {title}")
        
        # Get all paragraph text
        paragraphs = await page.evaluate("""
            Array.from(document.querySelectorAll('p')).map(p => p.textContent)
        """)
        print(f"Paragraphs found: {len(paragraphs)}")
        
        # Get page title
        page_title = await page.evaluate("document.title")
        print(f"Page title: {page_title}")
        
        # Get all links
        links = await page.evaluate("""
            Array.from(document.querySelectorAll('a')).map(a => ({
                text: a.textContent,
                href: a.href
            }))
        """)
        print(f"Links found: {len(links)}")
        
        # Take a screenshot of the page
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name
        
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
        
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_example())