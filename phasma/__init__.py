# Import new Playwright-like API
from .browser import launch, connect, Browser, BrowserContext, Page, ElementHandle, Error, TimeoutError

__all__ = [
    "launch",
    "connect",
    "Browser",
    "BrowserContext",
    "Page",
    "ElementHandle",
    "Error",
    "TimeoutError",
]
