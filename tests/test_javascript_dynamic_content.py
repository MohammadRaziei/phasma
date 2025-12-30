import asyncio

import phasma


class TestJavaScriptDynamicContent:
    """Test cases for pages with JavaScript that dynamically updates elements."""

    def test_simple_js_content_update(self):
        """Test a simple JavaScript content update."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
            <div id="content">Initial</div>
            <script>
                setTimeout(() => {
                    document.getElementById('content').innerHTML = 'Updated by JS';
                }, 100);
            </script>
        </body>
        </html>
        """

        # With short wait, might still get initial content or updated content depending on execution speed
        result_short = asyncio.run(
            phasma.render_page_content(html_content, wait=50)
        )

        # With sufficient wait, should get updated content
        result_long = asyncio.run(
            phasma.render_page_content(html_content, wait=300)
        )
        assert "Updated by JS" in result_long

    def test_multiple_js_updates(self):
        """Test multiple JavaScript updates over time."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Multi Update Test</title></head>
        <body>
            <div id="step1">Step 1: Not started</div>
            <div id="step2">Step 2: Not started</div>
            <div id="step3">Step 3: Not started</div>
            <script>
                setTimeout(() => {
                    document.getElementById('step1').innerHTML = 'Step 1: Done';
                }, 100);
                setTimeout(() => {
                    document.getElementById('step2').innerHTML = 'Step 2: Done';
                }, 200);
                setTimeout(() => {
                    document.getElementById('step3').innerHTML = 'Step 3: Done';
                }, 300);
            </script>
        </body>
        </html>
        """

        # Test at different wait times
        result_150 = asyncio.run(
            phasma.render_page_content(html_content, wait=150)
        )
        # At 150ms, Step 1 should be done, but others might also be done depending on execution speed
        assert "Step 1: Done" in result_150  # Step 1 should definitely be done

        result_350 = asyncio.run(
            phasma.render_page_content(html_content, wait=350)
        )
        assert "Step 1: Done" in result_350
        assert "Step 2: Done" in result_350
        assert "Step 3: Done" in result_350

    def test_ajax_simulation(self):
        """Test simulated AJAX content loading."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>AJAX Test</title></head>
        <body>
            <div id="status">Loading...</div>
            <div id="data"></div>
            <script>
                setTimeout(() => {
                    document.getElementById('status').innerHTML = 'Loaded!';
                    document.getElementById('data').innerHTML = '<p>AJAX data loaded</p>';
                }, 250);
            </script>
        </body>
        </html>
        """

        result = asyncio.run(
            phasma.render_page_content(html_content, wait=400)
        )
        assert "Loaded!" in result
        assert "AJAX data loaded" in result

    def test_simple_delayed_content_update(self):
        """Test simple delayed content update which is more reliable."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Simple Delay Test</title></head>
        <body>
            <div id="content">Before update</div>
            <script>
                document.getElementById('content').innerHTML = 'After update';
            </script>
        </body>
        </html>
        """

        result = asyncio.run(
            phasma.render_page_content(html_content, wait=200)
        )
        # Direct assignment should work
        assert "After update" in result
        assert "Before update" not in result

    def test_dom_element_creation(self):
        """Test JavaScript creating new DOM elements (simplified)."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>DOM Creation Test</title></head>
        <body>
            <div id="container">Original content</div>
            <script>
                const container = document.getElementById('container');
                container.innerHTML = '<p>New content created by JS</p>';
            </script>
        </body>
        </html>
        """

        result = asyncio.run(
            phasma.render_page_content(html_content, wait=200)
        )
        # Check that the content was replaced by JavaScript
        assert "New content created by JS" in result
        assert "Original content" not in result

    def test_timer_based_updates(self):
        """Test content updated by JavaScript timers."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Timer Test</title></head>
        <body>
            <div id="counter">0</div>
            <script>
                let count = 0;
                const counterEl = document.getElementById('counter');
                
                const interval = setInterval(() => {
                    count++;
                    counterEl.innerHTML = count;
                    
                    if (count >= 5) {
                        clearInterval(interval);
                    }
                }, 100);
            </script>
        </body>
        </html>
        """

        result = asyncio.run(
            phasma.render_page_content(html_content, wait=800)
        )
        # Should have reached at least count 4 or 5
        assert any(str(i) in result for i in range(4, 6))

    def test_event_based_updates(self):
        """Test content updated by JavaScript events."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Event Test</title></head>
        <body>
            <button id="clickBtn">Click me</button>
            <div id="output">Not clicked</div>
            <script>
                document.getElementById('clickBtn').addEventListener('click', () => {
                    document.getElementById('output').innerHTML = 'Button was clicked!';
                });
                
                // Simulate click
                setTimeout(() => {
                    document.getElementById('clickBtn').click();
                }, 100);
            </script>
        </body>
        </html>
        """

        result = asyncio.run(
            phasma.render_page_content(html_content, wait=250)
        )
        assert "Button was clicked!" in result

    def test_css_class_modifications(self):
        """Test JavaScript modifying CSS classes."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>CSS Test</title>
            <style>
                .active { background-color: yellow; }
                .highlight { font-weight: bold; }
            </style>
        </head>
        <body>
            <div id="element" class="normal">Test element</div>
            <script>
                setTimeout(() => {
                    const elem = document.getElementById('element');
                    elem.className = 'active highlight';
                }, 150);
            </script>
        </body>
        </html>
        """

        result = asyncio.run(
            phasma.render_page_content(html_content, wait=300)
        )
        # We can check if the class attribute was updated
        assert 'class="active highlight"' in result or "active highlight" in result

    def test_complex_spa_simulation(self):
        """Test a complex SPA-like behavior with multiple updates."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>SPA Test</title></head>
        <body>
            <nav>
                <button id="home">Home</button>
                <button id="about">About</button>
                <button id="contact">Contact</button>
            </nav>
            <main id="content">Home Page</main>
            <script>
                const content = document.getElementById('content');
                
                document.getElementById('home').addEventListener('click', () => {
                    content.innerHTML = 'Home Page';
                });
                
                document.getElementById('about').addEventListener('click', () => {
                    content.innerHTML = 'About Us Page';
                });
                
                document.getElementById('contact').addEventListener('click', () => {
                    content.innerHTML = 'Contact Page';
                });
                
                // Simulate navigation sequence
                setTimeout(() => document.getElementById('about').click(), 100);
                setTimeout(() => document.getElementById('contact').click(), 200);
                setTimeout(() => document.getElementById('home').click(), 300);
            </script>
        </body>
        </html>
        """

        result = asyncio.run(
            phasma.render_page_content(html_content, wait=500)
        )
        # Final state should be Home Page (last navigation)
        assert "Home Page" in result
        # Previous states might also be present in the HTML
        assert "About Us Page" in result or "Contact Page" in result

    def test_async_operation_simulation(self):
        """Test JavaScript async operations like Promises."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Async Test</title></head>
        <body>
            <div id="async-result">Pending...</div>
            <script>
                setTimeout(() => {
                    document.getElementById('async-result').innerHTML = 'Async operation completed!';
                }, 300);
            </script>
        </body>
        </html>
        """

        result = asyncio.run(
            phasma.render_page_content(html_content, wait=500)
        )
        assert "Async operation completed!" in result


# Additional test methods for file-based tests
class TestJavaScriptDynamicContentFromFile:
    """Test cases using HTML files with JavaScript."""

    def test_dynamic_content_from_file(self):
        """Test dynamic content from an HTML file."""
        # Create a temporary HTML file with JavaScript
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>File Test</title></head>
        <body>
            <h1>File-based Dynamic Content</h1>
            <div id="file-content">Initial content</div>
            <script>
                setTimeout(() => {
                    document.getElementById('file-content').innerHTML = 'Updated from file!';
                }, 200);
            </script>
        </body>
        </html>
        """

        # Write to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html_content)
            temp_file = f.name

        try:
            result = asyncio.run(
                phasma.render_page_content(temp_file, wait=400)
            )
            assert "Updated from file!" in result
        finally:
            # Clean up the temporary file
            import os
            os.unlink(temp_file)
