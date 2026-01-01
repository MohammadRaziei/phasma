# Import new Playwright-like API
from .browser import (
    Browser,
    BrowserContext,
    ElementHandle,
    Error,
    Page,
    TimeoutError,
    connect,
    launch,
)

# Import driver classes
from .driver import Driver, DriverPersistent

# Import utility functions
from .phasma import (
    execute_js_script,
    generate_pdf,
    render_page_content,
    render_url_content,
    sync_execute_js_script,
    sync_generate_pdf,
    sync_render_page_content,
    sync_render_url_content,
    sync_take_screenshot,
    take_screenshot,
)

__all__ = [
    "Browser",
    "BrowserContext",
    "Driver",
    "DriverPersistent",
    "ElementHandle",
    "Error",
    "Page",
    "TimeoutError",
    "connect",
    "execute_js_script",
    "generate_pdf",
    "launch",
    # Utility functions
    "render_page_content",
    "render_url_content",
    "sync_execute_js_script",
    "sync_generate_pdf",
    "sync_render_page_content",
    "sync_render_url_content",
    "sync_take_screenshot",
    "take_screenshot",
]
