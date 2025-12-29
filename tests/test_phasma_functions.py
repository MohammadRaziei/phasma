"""
Test suite for the new utility functions in phasma.py.
Tests the async and sync versions of render_page_content, render_url_content,
execute_js_script, take_screenshot, and generate_pdf functions.
"""
import asyncio
import tempfile
import pytest
from pathlib import Path
import phasma


class TestPhasmaFunctions:
    """Test suite for the new utility functions in phasma.py."""

    @pytest.mark.asyncio
    async def test_async_render_page_content_file(self):
        """Test async render_page_content function with a file."""
        html_file = Path(__file__).parent / "data" / "test_page.html"
        
        result = await phasma.render_page_content(str(html_file))
        
        assert result is not None
        assert "<h1>Hello, Phasma!</h1>" in result
        assert "This is a test page." in result

    @pytest.mark.asyncio
    async def test_async_render_page_content_string(self):
        """Test async render_page_content function with HTML string."""
        html_string = "<html><body><h1>Test String Content</h1></body></html>"
        
        result = await phasma.render_page_content(html_string)
        
        assert result is not None
        assert "Test String Content" in result

    @pytest.mark.asyncio
    async def test_async_render_page_content_with_output(self):
        """Test async render_page_content function with output file."""
        html_string = "<html><body><h1>Test Output</h1></body></html>"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            result = await phasma.render_page_content(html_string, output_path=output_path)
            
            # When output_path is provided, result should be None
            assert result is None
            
            # Check that file was created and contains expected content
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Test Output" in content
        finally:
            # Clean up
            Path(output_path).unlink()

    @pytest.mark.asyncio
    async def test_async_render_url_content(self):
        """Test async render_url_content function."""
        # Use a simple URL that should always be available
        result = await phasma.render_url_content("http://httpbin.org/html")
        
        assert result is not None
        assert "<html" in result.lower()
        assert "html>" in result.lower()

    @pytest.mark.asyncio
    async def test_async_render_url_content_with_output(self):
        """Test async render_url_content function with output file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            result = await phasma.render_url_content("http://httpbin.org/html", output_path=output_path)
            
            # When output_path is provided, result should be None
            assert result is None
            
            # Check that file was created
            assert Path(output_path).exists()
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "<html" in content.lower()
        finally:
            # Clean up
            Path(output_path).unlink()

    @pytest.mark.asyncio
    async def test_async_execute_js_script(self):
        """Test async execute_js_script function."""
        result = await phasma.execute_js_script("2 + 2")

        assert result == 4

    @pytest.mark.asyncio
    async def test_async_execute_js_script_with_url(self):
        """Test async execute_js_script function with a specific URL."""
        result = await phasma.execute_js_script("document.title", url="http://httpbin.org/html")

        assert result is not None

    @pytest.mark.asyncio
    async def test_async_take_screenshot(self):
        """Test async take_screenshot function."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            screenshot_path = f.name

        try:
            await phasma.take_screenshot("http://httpbin.org/html", screenshot_path)
            
            # Check that file was created and has content
            assert Path(screenshot_path).exists()
            assert Path(screenshot_path).stat().st_size > 0
        finally:
            # Clean up
            Path(screenshot_path).unlink()

    @pytest.mark.asyncio
    async def test_async_generate_pdf(self):
        """Test async generate_pdf function."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_path = f.name

        try:
            await phasma.generate_pdf("http://httpbin.org/html", pdf_path)
            
            # Check that file was created and has content
            assert Path(pdf_path).exists()
            assert Path(pdf_path).stat().st_size > 0
        finally:
            # Clean up
            Path(pdf_path).unlink()

    def test_sync_render_page_content_file(self):
        """Test sync render_page_content function with a file."""
        html_file = Path(__file__).parent / "data" / "test_page.html"
        
        result = phasma.sync_render_page_content(str(html_file))
        
        assert result is not None
        assert "<h1>Hello, Phasma!</h1>" in result
        assert "This is a test page." in result

    def test_sync_render_page_content_string(self):
        """Test sync render_page_content function with HTML string."""
        html_string = "<html><body><h1>Sync Test String Content</h1></body></html>"
        
        result = phasma.sync_render_page_content(html_string)
        
        assert result is not None
        assert "Sync Test String Content" in result

    def test_sync_render_page_content_with_output(self):
        """Test sync render_page_content function with output file."""
        html_string = "<html><body><h1>Sync Test Output</h1></body></html>"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            result = phasma.sync_render_page_content(html_string, output_path=output_path)
            
            # When output_path is provided, result should be None
            assert result is None
            
            # Check that file was created and contains expected content
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Sync Test Output" in content
        finally:
            # Clean up
            Path(output_path).unlink()

    def test_sync_render_url_content(self):
        """Test sync render_url_content function."""
        result = phasma.sync_render_url_content("http://httpbin.org/html")
        
        assert result is not None
        assert "<html" in result.lower()
        assert "html>" in result.lower()

    def test_sync_render_url_content_with_output(self):
        """Test sync render_url_content function with output file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            result = phasma.sync_render_url_content("http://httpbin.org/html", output_path=output_path)
            
            # When output_path is provided, result should be None
            assert result is None
            
            # Check that file was created
            assert Path(output_path).exists()
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "<html" in content.lower()
        finally:
            # Clean up
            Path(output_path).unlink()

    def test_sync_execute_js_script(self):
        """Test sync execute_js_script function."""
        result = phasma.sync_execute_js_script("3 + 3")

        assert result == 6

    def test_sync_execute_js_script_with_url(self):
        """Test sync execute_js_script function with a specific URL."""
        result = phasma.sync_execute_js_script("document.title", url="http://httpbin.org/html")

        assert result is not None

    def test_sync_take_screenshot(self):
        """Test sync take_screenshot function."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            screenshot_path = f.name

        try:
            phasma.sync_take_screenshot("http://httpbin.org/html", screenshot_path)
            
            # Check that file was created and has content
            assert Path(screenshot_path).exists()
            assert Path(screenshot_path).stat().st_size > 0
        finally:
            # Clean up
            Path(screenshot_path).unlink()

    def test_sync_generate_pdf(self):
        """Test sync generate_pdf function."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_path = f.name

        try:
            phasma.sync_generate_pdf("http://httpbin.org/html", pdf_path)
            
            # Check that file was created and has content
            assert Path(pdf_path).exists()
            assert Path(pdf_path).stat().st_size > 0
        finally:
            # Clean up
            Path(pdf_path).unlink()

    @pytest.mark.asyncio
    async def test_async_render_page_content_with_custom_viewport(self):
        """Test async render_page_content with custom viewport."""
        html_string = "<html><body><h1>Viewport Test</h1></body></html>"
        
        result = await phasma.render_page_content(html_string, viewport="1920x1080")
        
        assert result is not None
        assert "Viewport Test" in result

    @pytest.mark.asyncio
    async def test_async_take_screenshot_with_custom_viewport(self):
        """Test async take_screenshot with custom viewport."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            screenshot_path = f.name

        try:
            await phasma.take_screenshot(
                "http://httpbin.org/html", 
                screenshot_path, 
                viewport="1280x720", 
                wait=500
            )
            
            # Check that file was created and has content
            assert Path(screenshot_path).exists()
            assert Path(screenshot_path).stat().st_size > 0
        finally:
            # Clean up
            Path(screenshot_path).unlink()

    @pytest.mark.asyncio
    async def test_async_generate_pdf_with_custom_options(self):
        """Test async generate_pdf with custom options."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_path = f.name

        try:
            await phasma.generate_pdf(
                "http://httpbin.org/html", 
                pdf_path,
                format="A3",
                landscape=True,
                margin="0.5cm"
            )
            
            # Check that file was created and has content
            assert Path(pdf_path).exists()
            assert Path(pdf_path).stat().st_size > 0
        finally:
            # Clean up
            Path(pdf_path).unlink()


if __name__ == "__main__":
    # Run the tests manually if executed as a script
    pytest.main([__file__, "-v"])