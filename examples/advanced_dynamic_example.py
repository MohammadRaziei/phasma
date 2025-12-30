#!/usr/bin/env python3
"""
Advanced example demonstrating complex JavaScript interactions with phasma.
This shows various scenarios where elements are updated by JavaScript execution.
"""

import asyncio
import tempfile
from pathlib import Path
import phasma


async def demonstrate_ajax_simulation():
    """
    Demonstrate a page that simulates AJAX content loading.
    """
    print("Demonstrating AJAX simulation...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AJAX Simulation Example</title>
    </head>
    <body>
        <h1>AJAX Content Loading</h1>
        <div id="loading">Loading...</div>
        <div id="content"></div>

        <script>
            // Simulate AJAX request
            setTimeout(function() {
                document.getElementById('loading').innerHTML = 'Loaded!';
                document.getElementById('content').innerHTML = '<p>AJAX content loaded dynamically</p>';
            }, 400);
        </script>
    </body>
    </html>
    """

    # Demonstrate with different wait times
    result_no_wait = await phasma.render_page_content(html_content, wait=100)
    print(f"Without sufficient wait: {'AJAX content loaded' in result_no_wait}")

    result_with_wait = await phasma.render_page_content(html_content, wait=600)
    print(f"With sufficient wait: {'AJAX content loaded' in result_with_wait}")

    return result_with_wait


async def demonstrate_form_submission_simulation():
    """
    Demonstrate a form that updates content on submission.
    """
    print("\nDemonstrating form submission simulation...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Form Submission Example</title>
    </head>
    <body>
        <h1>Form Example</h1>
        <form id="exampleForm">
            <input type="text" id="nameInput" value="John">
            <button type="submit">Submit</button>
        </form>
        <div id="result"></div>

        <script>
            document.getElementById('exampleForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const name = document.getElementById('nameInput').value;
                document.getElementById('result').innerHTML = 'Hello, ' + name + '!';
            });

            // Simulate form submission after 200ms
            setTimeout(function() {
                document.getElementById('exampleForm').dispatchEvent(new Event('submit', {cancelable: true}));
            }, 200);
        </script>
    </body>
    </html>
    """

    result = await phasma.render_page_content(html_content, wait=400)
    success = 'Hello, John!' in result
    print(f"Form submission result: {'Success' if success else 'Failed'}")

    return result


async def demonstrate_timer_based_updates():
    """
    Demonstrate content that updates based on timers.
    """
    print("\nDemonstrating timer-based updates...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Timer Updates Example</title>
    </head>
    <body>
        <h1>Timer Updates</h1>
        <div id="clock">00:00:00</div>
        <div id="counter">Count: 0</div>

        <script>
            let count = 0;

            // Update counter every 150ms
            const interval = setInterval(function() {
                count++;
                document.getElementById('counter').innerHTML = 'Count: ' + count;

                // Stop after 5 updates
                if (count >= 5) {
                    clearInterval(interval);
                }
            }, 150);

            // Update clock
            function updateClock() {
                const now = new Date();
                document.getElementById('clock').innerHTML =
                    now.toTimeString().split(' ')[0];
            }
            updateClock();
            setInterval(updateClock, 1000);
        </script>
    </body>
    </html>
    """

    # Wait long enough for multiple timer updates
    result = await phasma.render_page_content(html_content, wait=1000)

    # Check if counter reached at least 3 (should reach 5-6 with 1000ms wait)
    counter_updates = 'Count: 3' in result or 'Count: 4' in result or 'Count: 5' in result or 'Count: 6' in result
    print(f"Timer updates occurred: {'Yes' if counter_updates else 'No'}")

    return result


async def demonstrate_dom_manipulation():
    """
    Demonstrate dynamic DOM element creation and manipulation.
    """
    print("\nDemonstrating DOM manipulation...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DOM Manipulation Example</title>
    </head>
    <body>
        <h1>DOM Manipulation</h1>
        <div id="container"></div>

        <script>
            // Create and add elements dynamically
            setTimeout(function() {
                const container = document.getElementById('container');

                // Add a paragraph
                const p = document.createElement('p');
                p.textContent = 'Dynamically added paragraph';
                container.appendChild(p);

                // Add a list
                const ul = document.createElement('ul');
                for (let i = 1; i <= 3; i++) {
                    const li = document.createElement('li');
                    li.textContent = 'List item ' + i;
                    ul.appendChild(li);
                }
                container.appendChild(ul);

                // Add a button with event
                const btn = document.createElement('button');
                btn.textContent = 'Click me';
                btn.onclick = function() {
                    this.textContent = 'Clicked!';
                };
                container.appendChild(btn);
            }, 200);
        </script>
    </body>
    </html>
    """

    result = await phasma.render_page_content(html_content, wait=400)

    checks = [
        ("Dynamically added paragraph", "Paragraph creation"),
        ("List item 1", "List item 1"),
        ("List item 2", "List item 2"),
        ("List item 3", "List item 3")
    ]

    for check_text, description in checks:
        found = check_text in result
        print(f"{description}: {'Found' if found else 'Not found'}")

    return result


async def demonstrate_css_class_changes():
    """
    Demonstrate dynamic CSS class changes.
    """
    print("\nDemonstrating CSS class changes...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CSS Class Changes Example</title>
        <style>
            .active { background-color: yellow; }
            .hidden { display: none; }
            .highlight { font-weight: bold; color: red; }
        </style>
    </head>
    <body>
        <h1>CSS Class Changes</h1>
        <div id="element1" class="normal">Normal element</div>
        <div id="element2" class="hidden">Hidden element</div>

        <script>
            setTimeout(function() {
                // Change class of element1
                const elem1 = document.getElementById('element1');
                elem1.className = 'highlight active';

                // Show element2
                const elem2 = document.getElementById('element2');
                elem2.className = 'normal';
            }, 300);
        </script>
    </body>
    </html>
    """

    result = await phasma.render_page_content(html_content, wait=500)

    # Check if classes were updated (we can't see CSS directly, but we can see class attributes)
    class_changes = 'class="highlight active"' in result or 'highlight active' in result
    print(f"CSS class changes: {'Applied' if class_changes else 'Not applied'}")

    return result


async def main():
    """
    Main function to run all advanced dynamic content examples.
    """
    print("Advanced Phasma Dynamic Content Examples")
    print("=" * 50)

    await demonstrate_ajax_simulation()
    await demonstrate_form_submission_simulation()
    await demonstrate_timer_based_updates()
    await demonstrate_dom_manipulation()
    await demonstrate_css_class_changes()

    print("\n" + "=" * 50)
    print("All advanced dynamic content examples completed!")


if __name__ == "__main__":
    asyncio.run(main())