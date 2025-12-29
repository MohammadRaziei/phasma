import asyncio
import pytest
import tempfile
from pathlib import Path
import phasma


class TestPhasma:
    """Test suite for the Phasma functions using the new Playwright-like API."""
    @pytest.mark.asyncio
    async def test_page_navigation(self):
        """Test page navigation functionality."""
        browser = await phasma.launch()
        try:
            page = await browser.new_page()

            # Test with a local HTML file
            html_file = Path(__file__).parent / "data" / "test_page.html"
            file_url = html_file.resolve().as_uri()

            await page.goto(file_url)

            # Check that we can get content
            title = await page.text_content("h1")
            assert "Hello, Phasma!" in title

            page_title = await page.evaluate("document.title")
            assert page_title is not None  # Title might be empty but shouldn't be None

        finally:
            await browser.close()

    @pytest.mark.asyncio
    async def test_page_content_extraction(self):
        """Test extracting content from pages."""
        browser = await phasma.launch()
        try:
            page = await browser.new_page()

            # Test with a local HTML file
            html_file = Path(__file__).parent / "data" / "test_page.html"
            file_url = html_file.resolve().as_uri()

            await page.goto(file_url)

            # Extract various content
            heading = await page.text_content("h1")
            assert "Hello, Phasma!" in heading

            title = await page.text_content("title")
            assert "Test Page" in title

        finally:
            await browser.close()

    @pytest.mark.asyncio
    async def test_screenshot_generation(self):
        """Test screenshot generation."""
        browser = await phasma.launch()
        try:
            page = await browser.new_page()

            # Navigate to a page
            await page.goto("http://example.com")

            # Take a screenshot
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                screenshot_path = f.name

            try:
                screenshot_bytes = await page.screenshot(screenshot_path)
                assert len(screenshot_bytes) > 0
                assert Path(screenshot_path).exists()
                assert Path(screenshot_path).stat().st_size > 0
            finally:
                # Clean up
                Path(screenshot_path).unlink()

        finally:
            await browser.close()

    @pytest.mark.asyncio
    async def test_pdf_generation(self):
        """Test PDF generation."""
        browser = await phasma.launch()
        try:
            page = await browser.new_page()

            # Navigate to a page
            await page.goto("http://example.com")

            # Generate a PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                pdf_path = f.name

            try:
                pdf_bytes = await page.pdf(pdf_path)
                assert len(pdf_bytes) > 0
                assert Path(pdf_path).exists()
                assert Path(pdf_path).stat().st_size > 0
            finally:
                # Clean up
                Path(pdf_path).unlink()

        finally:
            await browser.close()

    @pytest.mark.asyncio
    async def test_element_interaction(self):
        """Test element interaction methods."""
        browser = await phasma.launch()
        try:
            page = await browser.new_page()

            # Navigate to example.com
            await page.goto("http://example.com")

            # Test element selection and interaction
            heading = await page.text_content("h1")
            assert "Example Domain" in heading

            # Test waiting for elements
            element = await page.wait_for_selector("h1", timeout=5000)
            assert element is not None

            # Test evaluate JavaScript
            title = await page.evaluate("document.title")
            assert title is not None

        finally:
            await browser.close()
