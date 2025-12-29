"""
Example showing JavaScript execution using Phasma.
This demonstrates how Phasma can execute JavaScript code in PhantomJS context.
"""
import asyncio
import tempfile
from pathlib import Path

import phasma


async def javascript_execution_example():
    """Example of executing JavaScript code."""
    print("Demonstrating JavaScript execution...")
    
    # Execute JavaScript using the new Playwright-like API
    # This shows the core JavaScript execution capability
    print("\n--- Direct JavaScript execution ---")

    # Launch a browser instance for JavaScript execution
    browser = await phasma.launch()
    try:
        page = await browser.new_page()

        # Navigate to a blank page first
        await page.goto("about:blank")

        # Simple JavaScript execution
        output1 = await page.evaluate("console.log('Hello from PhantomJS!'); 'Execution completed';")
        print(f"Simple output: {output1}")

        # JavaScript with calculations
        output2 = await page.evaluate("""
            var a = 5;
            var b = 10;
            var result = a + b;
            console.log('Calculation result: ' + result);
            result;
        """)
        print(f"Calculation output: {output2}")

        # JavaScript that returns a value
        output3 = await page.evaluate("""
            var obj = {name: 'Phasma', version: 1.0, features: ['js-execution', 'dom-access']};
            JSON.stringify(obj);
        """)
        print(f"Object output: {output3}")

    finally:
        await browser.close()
    
    print("\n--- Browser-based JavaScript execution ---")
    
    browser = await phasma.launch()

    try:
        page = await browser.new_page()

        # Navigate to a page
        print("Navigating to example.com...")
        await page.goto("http://example.com")
        
        # Get basic page information
        title = await page.evaluate("document.title")
        print(f"Page title: {title}")
        
        # Get heading text using text_content (which works with the current architecture)
        heading = await page.text_content("h1")
        print(f"Main heading: {heading}")
        
        # Take a screenshot to capture the page
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name
        
        await page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved: {screenshot_path}")
        
        # Generate a PDF of the page
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        
        await page.pdf(path=pdf_path)
        print(f"PDF saved: {pdf_path}")
        
        print("\nJavaScript execution example completed successfully!")
        
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(javascript_execution_example())