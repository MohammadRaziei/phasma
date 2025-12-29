"""
Example demonstrating the Playwright-like API for phasma.
This shows how to use the new API which is similar to Playwright but uses PhantomJS.
"""
import asyncio
import tempfile
from pathlib import Path

import phasma


async def main():
    print("Launching browser with pre-bundled PhantomJS engine...")

    # Launch a new browser instance (uses pre-bundled PhantomJS engine)
    browser = await phasma.launch()
    
    try:
        # Create a new page
        page = await browser.new_page()
        
        # Navigate to a webpage
        print("Navigating to example.com...")
        await page.goto("http://example.com")
        
        # Get the page title
        title = await page.evaluate("document.title")
        print(f"Page title: {title}")
        
        # Get text content of an element
        heading = await page.text_content("h1")
        print(f"Main heading: {heading}")
        
        # Take a screenshot
        print("Taking screenshot...")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name
        
        try:
            screenshot_bytes = await page.screenshot(screenshot_path)
            print(f"Screenshot saved to: {screenshot_path}")
            print(f"Screenshot size: {len(screenshot_bytes)} bytes")
        except Exception as e:
            print(f"Screenshot failed: {e}")
        
        # Generate a PDF
        print("Generating PDF...")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        
        try:
            pdf_bytes = await page.pdf(pdf_path)
            print(f"PDF saved to: {pdf_path}")
            print(f"PDF size: {len(pdf_bytes)} bytes")
        except Exception as e:
            print(f"PDF generation failed: {e}")
        
        # Wait for an element to appear (with timeout)
        element = await page.wait_for_selector("h1", timeout=5000)
        if element:
            print("Found the h1 element!")
            element_text = await element.text_content()
            print(f"Element text: {element_text}")
        
        # Example of filling and clicking (on a form if available)
        # This is a simple example - in practice you'd navigate to a page with forms
        print("Example completed successfully!")
        
    finally:
        # Close the browser when done
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())