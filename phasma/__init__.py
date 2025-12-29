# Import legacy functions for CLI compatibility
from .phasma import render_page, render_url, execjs
# Import new Playwright-like API
from .browser import launch, connect, Browser, BrowserContext, Page, ElementHandle, Error, TimeoutError, download_driver

__all__ = [
    "launch",
    "connect",
    "Browser",
    "BrowserContext",
    "Page",
    "ElementHandle",
    "Error",
    "TimeoutError",
    "download_driver"
]

# For backward compatibility in __main__ (CLI), also expose legacy functions
__all__ += ["render_page", "render_url", "execjs"]
