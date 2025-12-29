# Import new Playwright-like API
from .browser import launch, connect, Browser, BrowserContext, Page, ElementHandle, Error, TimeoutError
# Import utility functions
from .phasma import (
    render_page_content,
    render_url_content,
    execute_js_script,
    take_screenshot,
    generate_pdf,
    sync_render_page_content,
    sync_render_url_content,
    sync_execute_js_script,
    sync_take_screenshot,
    sync_generate_pdf,
)

__all__ = [
    "launch",
    "connect",
    "Browser",
    "BrowserContext",
    "Page",
    "ElementHandle",
    "Error",
    "TimeoutError",
    # Utility functions
    "render_page_content",
    "render_url_content",
    "execute_js_script",
    "take_screenshot",
    "generate_pdf",
    "sync_render_page_content",
    "sync_render_url_content",
    "sync_execute_js_script",
    "sync_take_screenshot",
    "sync_generate_pdf",
]
