"""
phasma browse — a browsh-like terminal browser powered by PhantomJS.

Real page text is drawn as real terminal characters; only <img> elements are
rasterized to ANSI half-block art. Requires the `browse` extra:

    pip install 'phasma[browse]'

Usage:
    phasma browse https://example.com
"""
from .app import main, run

__all__ = ["main", "run"]
