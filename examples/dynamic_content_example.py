#!/usr/bin/env python3
"""
Example script demonstrating how to handle pages with dynamic JavaScript content using phasma.
This shows how to handle pages where elements are updated by JavaScript execution.
"""

import asyncio

import phasma


async def demonstrate_dynamic_content_with_wait():
    """
    Demonstrate a page with dynamic content that updates after a delay.
    This example shows how to use the wait parameter to allow JavaScript to execute.
    """
    print("Demonstrating dynamic content with wait...")

    # HTML with JavaScript that updates content after 500ms
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dynamic Content Example</title>
    </head>
    <body>
        <h1>Dynamic Content Example</h1>
        <div id="content">Initial content</div>

        <script>
            // Update content after 300ms
            setTimeout(function() {
                document.getElementById('content').innerHTML = 'Updated by JavaScript after 300ms!';
            }, 300);
        </script>
    </body>
    </html>
    """

    # Demonstrate with different wait times to see the difference
    print("\n1. Rendering with 100ms wait (JavaScript may not have executed yet):")
    result_short_wait = await phasma.render_page_content(html_content, wait=100)
    content_short = "Updated by JavaScript" in result_short_wait
    print(f"Content with short wait: {'JavaScript executed' if content_short else 'JavaScript not executed'}")

    print("\n2. Rendering with 500ms wait (JavaScript should have executed):")
    result_long_wait = await phasma.render_page_content(html_content, wait=500)
    content_long = "Updated by JavaScript" in result_long_wait
    print(f"Content with long wait: {'JavaScript executed' if content_long else 'JavaScript not executed'}")

    return result_long_wait


async def demonstrate_dynamic_content_from_file():
    """
    Demonstrate dynamic content from an HTML file with JavaScript.
    """
    print("\n\nDemonstrating dynamic content from file...")

    # Use the example file we created
    import os
    html_file = os.path.join(os.path.dirname(__file__), "dynamic_content_example.html")

    # Render with sufficient wait time to allow JavaScript to execute
    result = await phasma.render_page_content(str(html_file), wait=800)
    print(f"JavaScript from file executed: {'Yes' if 'Auto-updated after 500ms!' in result else 'No'}")

    return result


async def demonstrate_interactive_elements():
    """
    Demonstrate pages with interactive elements that update content when clicked.
    """
    print("\n\nDemonstrating interactive elements...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Interactive Elements Example</title>
    </head>
    <body>
        <h1>Interactive Elements Example</h1>
        <div id="counter">Count: 0</div>
        <button id="incrementBtn">Increment</button>

        <script>
            let count = 0;
            document.getElementById('incrementBtn').addEventListener('click', function() {
                count++;
                document.getElementById('counter').innerHTML = 'Count: ' + count;
            });

            // Simulate a click after 200ms
            setTimeout(function() {
                document.getElementById('incrementBtn').click();
            }, 200);
        </script>
    </body>
    </html>
    """

    # Render with wait to allow simulated click to execute
    result = await phasma.render_page_content(html_content, wait=400)
    print(f"Interactive element click executed: {'Yes' if 'Count: 1' in result else 'No'}")

    return result


async def demonstrate_complex_dynamic_content():
    """
    Demonstrate a more complex example with multiple JavaScript updates.
    """
    print("\n\nDemonstrating complex dynamic content...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Complex Dynamic Content</title>
    </head>
    <body>
        <h1>Complex Dynamic Content</h1>
        <div id="status">Loading...</div>
        <ul id="list"></ul>

        <script>
            // Update status after 100ms
            setTimeout(function() {
                document.getElementById('status').innerHTML = 'Step 1: Loaded';
            }, 100);

            // Update status and add list items after 300ms
            setTimeout(function() {
                document.getElementById('status').innerHTML = 'Step 2: Processing';

                const list = document.getElementById('list');
                const item1 = document.createElement('li');
                item1.textContent = 'Item 1 added by JS';
                list.appendChild(item1);
            }, 300);

            // Final update after 600ms
            setTimeout(function() {
                document.getElementById('status').innerHTML = 'Step 3: Complete!';

                const list = document.getElementById('list');
                const item2 = document.createElement('li');
                item2.textContent = 'Item 2 added by JS';
                list.appendChild(item2);
            }, 600);
        </script>
    </body>
    </html>
    """

    # Render with sufficient wait for all updates
    result = await phasma.render_page_content(html_content, wait=800)

    # Check for various stages of updates
    checks = [
        ("Step 3: Complete!", "Final status update"),
        ("Item 1 added by JS", "First list item"),
        ("Item 2 added by JS", "Second list item")
    ]

    print("JavaScript execution results:")
    for check_text, description in checks:
        executed = check_text in result
        print(f"  {description}: {'Executed' if executed else 'Not executed'}")

    return result


async def main():
    """
    Main function to run all dynamic content examples.
    """
    print("Phasma Dynamic JavaScript Content Examples")
    print("=" * 50)

    await demonstrate_dynamic_content_with_wait()
    await demonstrate_dynamic_content_from_file()
    await demonstrate_interactive_elements()
    await demonstrate_complex_dynamic_content()

    print("\n" + "=" * 50)
    print("All dynamic content examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
