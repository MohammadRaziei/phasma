#!/usr/bin/env python3
"""
Best practices for handling JavaScript-heavy pages with phasma.
This example shows different strategies for handling dynamic content.
"""

import asyncio

import phasma


async def demonstrate_optimal_wait_time():
    """
    Demonstrate finding the optimal wait time for JavaScript execution.
    """
    print("Finding optimal wait times for JavaScript execution...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Optimal Wait Example</title>
    </head>
    <body>
        <h1>Optimal Wait Example</h1>
        <div id="step1">Step 1: Not started</div>
        <div id="step2">Step 2: Not started</div>
        <div id="step3">Step 3: Not started</div>

        <script>
            // Step 1: Update after 100ms
            setTimeout(function() {
                document.getElementById('step1').innerHTML = 'Step 1: Completed';
            }, 100);

            // Step 2: Update after 300ms
            setTimeout(function() {
                document.getElementById('step2').innerHTML = 'Step 2: Completed';
            }, 300);

            // Step 3: Update after 600ms
            setTimeout(function() {
                document.getElementById('step3').innerHTML = 'Step 3: Completed';
            }, 600);
        </script>
    </body>
    </html>
    """

    # Demonstrate different wait times
    wait_times = [50, 150, 350, 650, 800]

    for wait_time in wait_times:
        result = await phasma.render_page_content(html_content, wait=wait_time)

        step1_complete = "Step 1: Completed" in result
        step2_complete = "Step 2: Completed" in result
        step3_complete = "Step 3: Completed" in result

        print(f"Wait {wait_time}ms: Step1={step1_complete}, Step2={step2_complete}, Step3={step3_complete}")

    return result


async def demonstrate_content_polling():
    """
    Demonstrate a strategy where we wait until specific content appears.
    This is more reliable than fixed wait times.
    """
    print("\nDemonstrating content polling strategy...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Content Polling Example</title>
    </head>
    <body>
        <h1>Content Polling Example</h1>
        <div id="dynamic-content">Loading...</div>

        <script>
            // Simulate delayed content loading
            setTimeout(function() {
                document.getElementById('dynamic-content').innerHTML = 'Content loaded successfully!';
            }, 400);
        </script>
    </body>
    </html>
    """

    # Try with different wait times until content appears
    for wait_time in [100, 200, 300, 500, 700]:
        result = await phasma.render_page_content(html_content, wait=wait_time)
        content_loaded = "Content loaded successfully!" in result
        print(f"Wait {wait_time}ms: Content loaded = {content_loaded}")
        if content_loaded:
            print(f"  -> Optimal wait time is around {wait_time}ms")
            break


async def demonstrate_complex_single_page_app():
    """
    Demonstrate a more complex example simulating a single-page application.
    """
    print("\nDemonstrating complex SPA-like behavior...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SPA Simulation</title>
    </head>
    <body>
        <div id="app">
            <nav>
                <button id="home-btn">Home</button>
                <button id="about-btn">About</button>
                <button id="contact-btn">Contact</button>
            </nav>
            <main id="content">Welcome to Home</main>
        </div>

        <script>
            const contentDiv = document.getElementById('content');

            document.getElementById('home-btn').addEventListener('click', () => {
                contentDiv.innerHTML = 'Welcome to Home';
            });

            document.getElementById('about-btn').addEventListener('click', () => {
                contentDiv.innerHTML = 'About Us Page';
            });

            document.getElementById('contact-btn').addEventListener('click', () => {
                contentDiv.innerHTML = 'Contact Information';
            });

            // Simulate navigation sequence
            setTimeout(() => {
                document.getElementById('about-btn').click();
            }, 200);

            setTimeout(() => {
                document.getElementById('contact-btn').click();
            }, 400);

            setTimeout(() => {
                document.getElementById('home-btn').click();
            }, 600);
        </script>
    </body>
    </html>
    """

    # Demonstrate with sufficient wait for all navigation events
    result = await phasma.render_page_content(html_content, wait=800)

    checks = [
        ("Welcome to Home", "Home content"),
        ("About Us Page", "About content"),
        ("Contact Information", "Contact content")
    ]

    print("SPA content checks:")
    for check_text, description in checks:
        found = check_text in result
        print(f"  {description}: {'Found' if found else 'Not found'}")

    # The final state should be "Welcome to Home" since that was the last navigation
    final_state_correct = result.count("Welcome to Home") >= 1  # It might appear multiple times
    print(f"  Final state correct: {'Yes' if final_state_correct else 'No'}")


async def demonstrate_ajax_with_data_fetching():
    """
    Demonstrate simulating AJAX data fetching and display.
    """
    print("\nDemonstrating AJAX data fetching simulation...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AJAX Data Fetching</title>
    </head>
    <body>
        <h1>AJAX Data Fetching</h1>
        <div id="status">Ready</div>
        <div id="data-container"></div>

        <script>
            document.getElementById('status').innerHTML = 'Fetching data...';

            // Simulate AJAX data fetch
            setTimeout(function() {
                document.getElementById('status').innerHTML = 'Data received!';

                // Add fetched data
                const container = document.getElementById('data-container');
                container.innerHTML = '<ul>' +
                    '<li>User: John Doe</li>' +
                    '<li>Email: john@example.com</li>' +
                    '<li>ID: 12345</li>' +
                '</ul>';
            }, 350);
        </script>
    </body>
    </html>
    """

    result = await phasma.render_page_content(html_content, wait=500)

    print("AJAX data fetching results:")
    checks = [
        ("Fetching data...", "Initial fetch status"),
        ("Data received!", "Success status"),
        ("User: John Doe", "User data"),
        ("Email: john@example.com", "Email data"),
        ("ID: 12345", "ID data")
    ]

    for check_text, description in checks:
        found = check_text in result
        print(f"  {description}: {'Found' if found else 'Not found'}")


async def demonstrate_wait_strategies():
    """
    Demonstrate different wait strategies for different scenarios.
    """
    print("\nDemonstrating different wait strategies:")

    scenarios = [
        {
            "name": "Simple DOM update",
            "html": """
            <div id="simple">Initial</div>
            <script>setTimeout(() => document.getElementById('simple').innerHTML = 'Updated', 100);</script>
            """,
            "recommended_wait": 200
        },
        {
            "name": "Complex animation/transition",
            "html": """
            <div id="complex">Loading</div>
            <script>
            setTimeout(() => document.getElementById('complex').innerHTML = 'Step 1', 200);
            setTimeout(() => document.getElementById('complex').innerHTML = 'Step 2', 400);
            setTimeout(() => document.getElementById('complex').innerHTML = 'Complete', 600);
            </script>
            """,
            "recommended_wait": 800
        },
        {
            "name": "API call simulation",
            "html": """
            <div id="api">Waiting</div>
            <script>
            setTimeout(() => {
                document.getElementById('api').innerHTML = 'API Response: Success';
            }, 500);
            </script>
            """,
            "recommended_wait": 700
        }
    ]

    for scenario in scenarios:
        print(f"\n  Demonstrating: {scenario['name']}")
        result = await phasma.render_page_content(scenario["html"], wait=scenario["recommended_wait"])

        # Simple check - if it contains "Success", "Complete", or "Response", consider it successful
        success_indicators = ["Success", "Complete", "Response", "Updated"]
        success = any(indicator in result for indicator in success_indicators)
        print(f"    Result: {'Success' if success else 'Incomplete'}")


async def main():
    """
    Main function to run all JavaScript handling strategy examples.
    """
    print("JavaScript-Heavy Page Handling Strategies with Phasma")
    print("=" * 60)

    await demonstrate_optimal_wait_time()
    await demonstrate_content_polling()
    await demonstrate_complex_single_page_app()
    await demonstrate_ajax_with_data_fetching()
    await demonstrate_wait_strategies()

    print("\n" + "=" * 60)
    print("All JavaScript handling strategy examples completed!")
    print("\nKey takeaways:")
    print("- Use appropriate wait times based on your JavaScript execution time")
    print("- Try with multiple wait times to find the optimal duration")
    print("- Consider the complexity of your JavaScript operations")
    print("- Pages with simple DOM updates need less wait time than complex SPAs")


if __name__ == "__main__":
    asyncio.run(main())
