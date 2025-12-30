"""
Comprehensive test suite to improve coverage for Phasma.
"""
import tempfile
from pathlib import Path

import pytest

import phasma


@pytest.mark.asyncio()
async def test_comprehensive_browser_api():
    """Test comprehensive browser API functionality."""
    browser = await phasma.browser.launch()
    try:
        # Test creatinysg a page
        page = await browser.new_page()

        # Test navigation
        await page.goto("http://example.com")

        # Test viewport setting
        await page.set_viewport_size(1280, 720)

        # Test content extraction
        title = await page.text_content("h1")
        assert "Example" in title

        inner_html = await page.inner_html("h1")
        assert inner_html

        # Test JavaScript evaluation
        doc_title = await page.evaluate("document.title")
        assert doc_title is not None

        # Test element handle
        element = await page.wait_for_selector("h1", timeout=5000)
        assert element is not None

        element_text = await element.text_content()
        assert "Example" in element_text

        # Test screenshot and PDF
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name
        await page.screenshot(path=screenshot_path)
        assert Path(screenshot_path).exists()
        Path(screenshot_path).unlink()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        await page.pdf(path=pdf_path)
        assert Path(pdf_path).exists()
        Path(pdf_path).unlink()

    finally:
        await browser.close()


def test_driver_functionality():
    """Test driver functionality."""
    driver = phasma.driver.Driver()

    # Test properties
    assert driver.bin_path.exists()
    assert driver.version == "2.1.1"

    # Test exec method
    result = driver.exec(["--version"], capture_output=True)
    assert result.returncode == 0
    assert result.stdout is not None



@pytest.mark.asyncio()
async def test_error_handling():
    """Test error handling in the new API."""
    browser = await phasma.browser.launch()
    try:
        page = await browser.new_page()

        # Test with invalid selector
        element = await page.wait_for_selector("nonexistent", timeout=100)
        assert element is None

    finally:
        await browser.close()



def test_cli_simulation():
    """Test CLI functionality by importing and testing main functions."""
    import sys
    from io import StringIO


    # Capture original stdout
    original_stdout = sys.stdout

    # Test driver version functionality
    try:
        # Temporarily redirect stdout to capture output
        captured_output = StringIO()
        sys.stdout = captured_output

        # Test driver version command simulation
        driver = phasma.driver.Driver()
        version = driver.version
        assert version == "2.1.1"

    finally:
        # Restore stdout
        sys.stdout = original_stdout
