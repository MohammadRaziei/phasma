"""
DriverPersistent — wraps a long-lived PhantomJS process that exposes a tiny
HTTP/JSON RPC server (phantom_server.js).  One process per Browser instance,
reused for every page operation.

Communication:
    POST http://127.0.0.1:<port>/<action>
    body:  JSON params
    reply: {"ok": true,  "data": ...}
         | {"ok": false, "error": "..."}
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from .driver import Driver

# Path to the bundled JS server script
_SERVER_JS = Path(__file__).with_name("phantom_server.js")


class DriverPersistent(Driver):
    """Manages a persistent PhantomJS process and talks to it over HTTP."""

    def __init__(self) -> None:
        super().__init__()
        self._process: Optional[subprocess.Popen] = None
        self._port: Optional[int] = None
        self._base_url: Optional[str] = None
        self._is_closed: bool = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start_persistent_session(
        self,
        args: Optional[Sequence[str]] = None,
        startup_timeout: float = 15.0,
    ) -> None:
        """Launch the PhantomJS server process and wait until it is ready."""
        if self._process is not None and self._process.poll() is None:
            return  # already running

        env = os.environ.copy()
        env["OPENSSL_CONF"] = ""  # suppress OpenSSL warnings

        cmd = [
            str(self.bin_path),
            "--ssl-protocol=any",
            "--ignore-ssl-errors=true",
            str(_SERVER_JS),
            "0",            # port 0 → server picks a free port
        ]
        if args:
            cmd.extend(args)

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # Read the "READY <port>" line from stdout
        deadline = time.monotonic() + startup_timeout
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                stderr = self._process.stderr.read()
                raise RuntimeError(
                    f"PhantomJS exited during startup. stderr: {stderr}"
                )
            line = self._process.stdout.readline().strip()
            if line.startswith("READY "):
                self._port = int(line.split()[1])
                self._base_url = f"http://127.0.0.1:{self._port}"
                return

        self._process.kill()
        raise RuntimeError("PhantomJS did not become ready within timeout")

    def close(self) -> None:
        """Shut down the PhantomJS process cleanly."""
        if self._is_closed:
            return
        self._is_closed = True

        if self._process and self._process.poll() is None:
            try:
                self._rpc("exit", timeout=3.0)
            except Exception:
                pass
            try:
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._process.kill()

        self._process = None
        self._port = None
        self._base_url = None

    def __del__(self) -> None:
        if not self._is_closed:
            self.close()

    # ── RPC core ──────────────────────────────────────────────────────────────

    def _rpc(self, action: str, params: Optional[dict] = None, timeout: float = 60.0) -> Any:
        """
        POST JSON params to /<action>, return the 'data' field on success,
        raise RuntimeError on PhantomJS-level errors.
        """
        if self._base_url is None:
            raise RuntimeError("Session not started — call start_persistent_session() first")

        body = json.dumps(params or {}).encode()
        req = urllib.request.Request(
            f"{self._base_url}/{action}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            raise RuntimeError(f"RPC transport error ({action}): {exc}") from exc

        if not payload.get("ok"):
            raise RuntimeError(f"PhantomJS error ({action}): {payload.get('error')}")
        return payload.get("data")

    # ── public API (used by browser.py) ───────────────────────────────────────

    def navigate(self, url: str, wait_ms: int = 0, timeout: float = 60.0) -> str:
        """Navigate to *url*, return outer HTML after an optional settle delay."""
        return self._rpc("navigate", {"url": url, "wait": wait_ms}, timeout=timeout)

    def evaluate(self, expression: str, timeout: float = 60.0) -> Any:
        """Evaluate a JS expression and return the result."""
        return self._rpc("evaluate", {"expression": expression}, timeout=timeout)

    def click(self, selector: str, timeout: float = 60.0) -> bool:
        """Click the first element matching *selector*. Returns True if found."""
        return self._rpc("click", {"selector": selector}, timeout=timeout)

    def fill(self, selector: str, value: str, timeout: float = 60.0) -> bool:
        """Set the value of an input element. Returns True if found."""
        return self._rpc("fill", {"selector": selector, "value": value}, timeout=timeout)

    def take_screenshot(self, path: Union[str, Path], timeout: float = 60.0) -> str:
        """Render the current page to an image file."""
        return self._rpc("screenshot", {"path": str(path)}, timeout=timeout)

    def generate_pdf(
        self,
        path: Union[str, Path],
        format: Optional[str] = "A4",
        landscape: bool = False,
        margin: Union[str, dict] = "1cm",
        width: Optional[str] = None,
        height: Optional[str] = None,
        timeout: float = 60.0,
    ) -> str:
        """Render the current page to a PDF file.
        
        Pass width/height (e.g. '400px') for pixel-exact paper size,
        or format (e.g. 'A4') for standard paper sizes.
        """
        params: dict = {"path": str(path), "margin": margin}
        if width and height:
            params["width"] = width
            params["height"] = height
        else:
            params["format"] = format
            params["landscape"] = landscape
        return self._rpc("pdf", params, timeout=timeout)

    def set_viewport(self, width: int, height: int, timeout: float = 10.0) -> None:
        """Set the page viewport size."""
        self._rpc("set_viewport", {"width": width, "height": height}, timeout=timeout)

    # ── layout / terminal-browser primitives ────────────────────────────────

    def get_layout(self, timeout: float = 30.0) -> dict:
        """
        Walk the current page's DOM and return real text runs (never
        rasterized) plus the bounding boxes of <img> elements — the only
        thing meant to be turned into ASCII/ANSI art by a terminal renderer.
        All coordinates are viewport-relative (already account for scroll).
        """
        return self._rpc("layout", timeout=timeout)

    def scroll(self, dx: int = 0, dy: int = 0, *, absolute: bool = False, timeout: float = 10.0) -> dict:
        """Scroll the page by (dx, dy), or to (dx, dy) if absolute=True. Returns the new scroll position."""
        return self._rpc("scroll", {"dx": dx, "dy": dy, "absolute": absolute}, timeout=timeout)

    def region_screenshot(self, path: Union[str, Path], left: int, top: int, width: int, height: int,
                           timeout: float = 30.0) -> str:
        """Render only a sub-rectangle of the current viewport to a PNG file (used for <img> regions)."""
        return self._rpc(
            "region_screenshot",
            {"path": str(path), "left": left, "top": top, "width": width, "height": height},
            timeout=timeout,
        )

    def mouse_event(self, type: str, x: int, y: int, button: str = "left", timeout: float = 10.0) -> None:
        """Dispatch a mouse event at viewport coordinates (x, y). type: click|mousedown|mouseup|mousemove|doubleclick."""
        self._rpc("mouse", {"type": type, "x": x, "y": y, "button": button}, timeout=timeout)

    def send_key(self, text: Optional[str] = None, special: Optional[str] = None, timeout: float = 10.0) -> None:
        """Type literal *text* into the focused element, or send a *special* key
        (Backspace, Enter, Tab, Left, Right, Up, Down, Escape, Delete, Home, End)."""
        params = {"special": special} if special else {"text": text or ""}
        self._rpc("key", params, timeout=timeout)

    def active_element(self, timeout: float = 10.0) -> Optional[dict]:
        """Return {tag, editable, type} for document.activeElement, or None."""
        return self._rpc("active_element", timeout=timeout)

    def active_field(self, timeout: float = 10.0) -> Optional[dict]:
        """Rect + current value + placeholder of the focused <input>/<textarea>,
        or None. Uses a function-reference RPC action (not the generic
        string-based `evaluate`, which is blocked by any page whose CSP
        lacks 'unsafe-eval' - most real sites)."""
        return self._rpc("active_field", timeout=timeout)

    def set_active_value(self, value: str, timeout: float = 10.0) -> bool:
        """Set the focused element's value in one round trip and fire
        input/change so page JS still reacts to it."""
        return bool(self._rpc("set_active_value", {"value": value}, timeout=timeout))

    def blur_active(self, timeout: float = 10.0) -> None:
        """Blur document.activeElement, if any."""
        self._rpc("blur_active", timeout=timeout)

    # ── link hints ───────────────────────────────────────────────────────────

    def get_hints(self, timeout: float = 30.0) -> list:
        """Tag every clickable/focusable element in the viewport and return
        a list of {id, x, y, w, h, tag} for each (vimium-style link hints)."""
        return self._rpc("hints", timeout=timeout)

    def hint_click(self, hint_id: str, timeout: float = 10.0) -> None:
        """Click the element previously tagged with *hint_id* by get_hints()."""
        self._rpc("hint_click", {"id": hint_id}, timeout=timeout)

    def clear_hints(self, timeout: float = 10.0) -> None:
        """Remove any leftover hint tags (get_hints() also does this itself
        before retagging, so this is mainly for an explicit cancel)."""
        self._rpc("clear_hints", timeout=timeout)

    # ── find-in-page ─────────────────────────────────────────────────────────

    def find_text(self, query: str, index: int = 0, timeout: float = 15.0) -> dict:
        """Whole-document (not viewport-limited) case-insensitive search.
        Scrolls the match at *index* (wraps around) into view and returns
        {found, total, index, x, y, w, h} - or {found: False, total: 0} if
        there are no matches at all."""
        return self._rpc("find_text", {"query": query, "index": index}, timeout=timeout)
