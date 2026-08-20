"""
Raw terminal input reading.

`blessed.Terminal.inkey()` is built to resolve known terminfo key sequences
(arrows, function keys, ...) but SGR mouse-reporting sequences
(`ESC [ < btn ; x ; y M`) aren't in that keymap. In practice this makes
`inkey()` hand the bytes back split across several calls in a
terminal-dependent way, so mouse clicks (and therefore focusing/typing into
inputs, which starts with a click) can silently never be recognized.

This module reads raw bytes directly from the tty (assuming the terminal is
already in cbreak/raw mode, e.g. via `blessed.Terminal.cbreak()`) and
assembles complete escape sequences itself, so mouse and special-key
handling is deterministic regardless of terminal/multiplexer quirks.
"""
from __future__ import annotations

import os
import select
from typing import Optional


class Key(str):
    """A decoded keypress. Behaves like the raw string (for printable chars
    and for full escape sequences like SGR mouse reports), with an optional
    `.name` set for recognized special keys (matches blessed's KEY_* names
    so the rest of the app doesn't need to know which reader produced it)."""

    def __new__(cls, seq: str, name: Optional[str] = None) -> "Key":
        obj = super().__new__(cls, seq)
        obj.name = name
        return obj


_CSI_FINAL_MAP = {
    "A": "KEY_UP", "B": "KEY_DOWN", "C": "KEY_RIGHT", "D": "KEY_LEFT",
    "H": "KEY_HOME", "F": "KEY_END",
}
_CSI_TILDE_MAP = {
    "1": "KEY_HOME", "3": "KEY_DELETE", "4": "KEY_END",
    "5": "KEY_PGUP", "6": "KEY_PGDOWN",
}
_SS3_MAP = {"H": "KEY_HOME", "F": "KEY_END"}


def _read_exact(fd: int, n: int, timeout: float) -> bytes:
    out = b""
    while len(out) < n:
        r, _, _ = select.select([fd], [], [], timeout)
        if fd not in r:
            break
        chunk = os.read(fd, n - len(out))
        if not chunk:
            break
        out += chunk
    return out


def _decode_csi(fd: int) -> Key:
    """Called right after reading 'ESC ['. Reads until a final byte
    (0x40-0x7E) and classifies the result."""
    body = ""
    while True:
        b = _read_exact(fd, 1, timeout=0.05)
        if not b:
            break
        ch = b.decode("latin-1")
        body += ch
        if "\x40" <= ch <= "\x7e":
            break
    seq = "\x1b[" + body
    if body.startswith("<"):
        return Key(seq, "MOUSE")
    if body.endswith("~"):
        return Key(seq, _CSI_TILDE_MAP.get(body[:-1]))
    if body and body[-1] in _CSI_FINAL_MAP:
        return Key(seq, _CSI_FINAL_MAP[body[-1]])
    return Key(seq, None)


def _decode_ss3(fd: int) -> Key:
    b = _read_exact(fd, 1, timeout=0.05)
    ch = b.decode("latin-1") if b else ""
    return Key("\x1bO" + ch, _SS3_MAP.get(ch))


def read_key(fd: int, timeout: Optional[float]) -> Optional[Key]:
    """Block up to *timeout* seconds (or forever if None) for one logical
    keypress on *fd*. Returns None on timeout with nothing available."""
    r, _, _ = select.select([fd], [], [], timeout)
    if fd not in r:
        return None

    first = os.read(fd, 1)
    if not first:
        return None

    if first == b"\x1b":
        nxt = _read_exact(fd, 1, timeout=0.05)
        if not nxt:
            return Key("\x1b", "KEY_ESCAPE")
        if nxt == b"[":
            return _decode_csi(fd)
        if nxt == b"O":
            return _decode_ss3(fd)
        # unrecognized 2-byte escape - surface it as-is, no special name
        return Key("\x1b" + nxt.decode("latin-1"), None)

    if first in (b"\r", b"\n"):
        return Key("\n", "KEY_ENTER")
    if first in (b"\x7f", b"\x08"):
        return Key(first.decode("latin-1"), "KEY_BACKSPACE")
    if first == b"\t":
        return Key("\t", "KEY_TAB")

    # UTF-8 continuation bytes for a multi-byte character
    lead = first[0]
    if lead >= 0xF0:
        extra = 3
    elif lead >= 0xE0:
        extra = 2
    elif lead >= 0xC0:
        extra = 1
    else:
        extra = 0
    raw = first + _read_exact(fd, extra, timeout=0.05) if extra else first
    try:
        ch = raw.decode("utf-8")
    except UnicodeDecodeError:
        ch = ""
    return Key(ch, None)
