"""
Example showing form interaction with the Playwright-like API.
"""
import asyncio
import tempfile
from pathlib import Path

import phasma


async def form_interaction_example():
    """Example of interacting with forms (using a simple test form)."""
    # Create a simple HTML form for testing
    form_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Form</title></head>
    <body>
        <h1>Test Form</h1>
        <form id="test-form">
            <label for="name">Name:</label>
            <input type="text" id="name" name="name" placeholder="Enter your name"><br><br>
            
            <label for="email">Email:</label>
            <input type="email" id="email" name="email" placeholder="Enter your email"><br><br>
            
            <label for="message">Message:</label>
            <textarea id="message" name="message" placeholder="Enter your message"></textarea><br><br>
            
            <button type="submit">Submit</button>
        </form>
        
        <div id="result"></div>
        
        <script>
            document.getElementById('test-form').addEventListener('submit', function(e) {
                e.preventDefault();
                const name = document.getElementById('name').value;
                const email = document.getElementById('email').value;
                const message = document.getElementById('message').value;
                
                document.getElementById('result').innerHTML = 
                    '<h3>Form Submitted!</h3>' +
                    '<p>Name: ' + name + '</p>' +
                    '<p>Email: ' + email + '</p>' +
                    '<p>Message: ' + message + '</p>';
            });
        </script>
    </body>
    </html>
    """
    
    # Save the form HTML to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(form_html)
        form_path = f.name
    
    try:

        browser = await phasma.launch()
        
        try:
            page = await browser.new_page()
            
            # Navigate to the form
            file_url = Path(form_path).resolve().as_uri()
            await page.goto(file_url)
            
            # Fill in the form fields
            print("Filling form fields...")
            await page.fill("#name", "John Doe")
            await page.fill("#email", "john@example.com")
            await page.fill("#message", "This is a test message from phasma!")
            
            # Click the submit button
            print("Submitting form...")
            await page.click("button[type='submit']")
            
            # Wait a bit for the JavaScript to execute
            await asyncio.sleep(0.5)
            
            # Check the result
            result_text = await page.text_content("#result")
            print(f"Form result: {result_text[:100]}...")  # First 100 chars
            
            # Take a screenshot of the filled form
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                screenshot_path = f.name
            
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot of filled form saved: {screenshot_path}")
            
        finally:
            await browser.close()
            
    finally:
        # Clean up the temporary form file
        Path(form_path).unlink()


if __name__ == "__main__":
    asyncio.run(form_interaction_example())