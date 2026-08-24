/**
 * PhantomJS HTTP server - persistent session with JSON RPC over HTTP.
 * Started by DriverPersistent, listens on a random port, communicates via JSON.
 *
 * Protocol:
 *   POST /<action>   body: JSON params
 *   Response:        {"ok": true,  "data": ...}
 *                 or {"ok": false, "error": "..."}
 *
 * Actions: navigate, evaluate, click, fill, screenshot, set_viewport, exit,
 *          layout, scroll, region_screenshot, mouse, key, active_element
 */

"use strict";

var webpage = require('webpage');
var server  = require('webserver').create();
var system  = require('system');

// ── helpers ──────────────────────────────────────────────────────────────────

function ok(response, data) {
    var body = JSON.stringify({ ok: true, data: data === undefined ? null : data });
    response.statusCode = 200;
    response.headers = { 'Content-Type': 'application/json' };
    response.write(body);
    response.close();
}

function err(response, message) {
    var body = JSON.stringify({ ok: false, error: String(message) });
    response.statusCode = 200;          // keep 200 so Python reads the body
    response.headers = { 'Content-Type': 'application/json' };
    response.write(body);
    response.close();
}

function parseBody(request) {
    try {
        return JSON.parse(request.post || '{}');
    } catch (e) {
        return {};
    }
}

// ── page pool ─────────────────────────────────────────────────────────────────
// Simple single-page model (one active page per session).
// Extend to a map keyed by page_id if you need multi-tab support later.

var page = webpage.create();
page.settings.javascriptEnabled     = true;
page.settings.localToRemoteUrlAccess = true;
page.viewportSize = { width: 1024, height: 768 };

// ── layout extraction (in-page function, injected via page.evaluate) ───────────
// Walks the DOM and returns text runs (as real characters, never rasterized)
// plus the bounding boxes of image elements (the only thing meant to be
// rasterized by the terminal renderer). All rects are viewport-relative, i.e.
// already account for the current scroll position.

function _phasmaComputeLayout(viewportW, viewportH) {
    var results = { texts: [], images: [], fields: [], texts_truncated: false };
    var body = document.body;
    if (!body) return results;

    function isVisible(el) {
        var style = window.getComputedStyle(el);
        if (!style) return true;
        if (style.display === 'none' || style.visibility === 'hidden') return false;
        if (parseFloat(style.opacity) === 0) return false;
        return true;
    }

    function ancestorsVisible(el) {
        while (el) {
            if (!isVisible(el)) return false;
            el = el.parentElement;
        }
        return true;
    }

    function intersectsViewport(rect) {
        return rect.right > 0 && rect.left < viewportW &&
               rect.bottom > 0 && rect.top < viewportH;
    }

    // Effective background of an element: its own, or the nearest ancestor's
    // if it (and everything below that ancestor) is transparent. This
    // matters a lot for text contrast - a light-themed content card (e.g.
    // a README's markdown body) sitting inside an otherwise dark page would
    // otherwise report "no local background", making dark text on that
    // light card invisible once it falls back to the dark *page* background
    // instead. Memoized on the element itself since many words share the
    // same parent (or nearby ancestors), which matters on pages with
    // thousands of text runs.
    function effectiveBg(el) {
        var chain = [];
        var cur = el;
        while (cur) {
            if (cur.__phasmaEffBg !== undefined) {
                for (var i = 0; i < chain.length; i++) chain[i].__phasmaEffBg = cur.__phasmaEffBg;
                return cur.__phasmaEffBg;
            }
            chain.push(cur);
            var c = window.getComputedStyle(cur).backgroundColor;
            var m = /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)/.exec(c);
            if (m) {
                var a = (m[4] !== undefined) ? parseFloat(m[4]) : 1;
                if (a > 0) {
                    for (var j = 0; j < chain.length; j++) chain[j].__phasmaEffBg = c;
                    return c;
                }
            }
            cur = cur.parentElement;
        }
        for (var k = 0; k < chain.length; k++) chain[k].__phasmaEffBg = null;
        return null;
    }

    var MAX_RUNS = 20000; // safety valve against pathological pages
    var range = document.createRange();
    var walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, null, false);
    var node;
    // Tracks whether the previous piece of text (possibly in a different
    // text node / across an inline element boundary) ended in whitespace.
    // Needed because old WebKit sometimes collapses whitespace that sits
    // exactly at an inline-element boundary to zero width in the actual
    // layout (not just in Range measurement), which would otherwise make
    // e.g. "and <i>italic</i>" look like "anditalic" once placed in the
    // terminal grid. See grid.py's use of `gapBefore`.
    var pendingSpace = true;

    while ((node = walker.nextNode())) {
        if (results.texts.length >= MAX_RUNS) { results.texts_truncated = true; break; }

        var raw = node.nodeValue;
        if (!raw || !/\S/.test(raw)) { pendingSpace = pendingSpace || /\s/.test(raw || ''); continue; }

        var parentEl = node.parentElement;
        if (!parentEl) continue;
        var parentTag = parentEl.tagName;
        if (parentTag === 'SCRIPT' || parentTag === 'STYLE' || parentTag === 'NOSCRIPT' ||
            parentTag === 'TITLE' || parentTag === 'TEMPLATE') continue;

        // Cheap pre-filter: skip the whole node if its parent element's box
        // doesn't intersect the viewport at all (avoids per-char DOM calls).
        var parentRect = parentEl.getBoundingClientRect();
        if (!intersectsViewport(parentRect)) continue;
        if (!ancestorsVisible(parentEl)) continue;

        var style = window.getComputedStyle(parentEl);
        var color = style.color;
        var bg = effectiveBg(parentEl);
        var weight = parseInt(style.fontWeight, 10);
        var bold = style.fontWeight === 'bold' || (!isNaN(weight) && weight >= 600);
        var italic = style.fontStyle === 'italic';
        var decoration = String(style.textDecorationLine || style.textDecoration || '');
        var underline = decoration.indexOf('underline') !== -1;

        // Measure whole words at a time (not individual characters): far
        // fewer DOM calls, and it sidesteps a WebKit quirk where an
        // isolated whitespace Range measures as zero-width, which would
        // otherwise make adjacent words from different text nodes appear
        // to visually merge. Whitespace itself is never measured or drawn
        // (blank cells already default to space).
        var tokens = raw.match(/\S+/g);
        if (!tokens) continue;
        var searchPos = 0;

        for (var ti = 0; ti < tokens.length; ti++) {
            if (results.texts.length >= MAX_RUNS) { results.texts_truncated = true; break; }
            var word = tokens[ti];
            var wordStart = raw.indexOf(word, searchPos);
            if (wordStart < 0) continue;
            var wordEnd = wordStart + word.length;
            var gapBefore = (ti > 0) || (wordStart > 0) || pendingSpace;
            searchPos = wordEnd;

            range.setStart(node, wordStart);
            range.setEnd(node, wordEnd);
            var rects = range.getClientRects();

            if (rects.length === 1) {
                var r = rects[0];
                if (r.width <= 0 || r.height <= 0) continue;
                if (!intersectsViewport(r)) continue;
                results.texts.push({
                    text: word, x: r.left, y: r.top, w: r.width, h: r.height,
                    color: color, bg: bg, bold: bold, italic: italic, underline: underline,
                    gapBefore: gapBefore
                });
            } else if (rects.length > 1) {
                // Rare: a single word wraps across more than one visual
                // line. Fall back to per-character measurement for just
                // this word so each visual line still gets its own run.
                var runX = null, runY = null, runW = 0, runH = 0, runText = '';
                for (var ci = 0; ci < word.length; ci++) {
                    range.setStart(node, wordStart + ci);
                    range.setEnd(node, wordStart + ci + 1);
                    var crects = range.getClientRects();
                    if (!crects.length) continue;
                    var cr = crects[0];
                    if (cr.width <= 0 || cr.height <= 0) continue;
                    var sameLine = runY !== null && Math.abs(cr.top - runY) < 2;
                    if (sameLine) {
                        runText += word[ci];
                        runW = cr.right - runX;
                        runH = Math.max(runH, cr.height);
                    } else {
                        if (runText && intersectsViewport({ left: runX, top: runY, right: runX + runW, bottom: runY + runH })) {
                            results.texts.push({
                                text: runText, x: runX, y: runY, w: runW, h: runH,
                                color: color, bg: bg, bold: bold, italic: italic, underline: underline,
                                gapBefore: gapBefore
                            });
                            gapBefore = false; // only the word's first visual line inherits the real gap
                        }
                        runX = cr.left; runY = cr.top; runW = cr.width; runH = cr.height; runText = word[ci];
                    }
                }
                if (runText && intersectsViewport({ left: runX, top: runY, right: runX + runW, bottom: runY + runH })) {
                    results.texts.push({
                        text: runText, x: runX, y: runY, w: runW, h: runH,
                        color: color, bg: bg, bold: bold, italic: italic, underline: underline,
                        gapBefore: gapBefore
                    });
                }
            }
        }
        pendingSpace = wordEnd < raw.length; // does this node's raw text trail off in whitespace?
        if (results.texts_truncated) break;
    }

    var imgs = body.querySelectorAll('img');
    for (var k = 0; k < imgs.length; k++) {
        var img = imgs[k];
        if (!ancestorsVisible(img)) continue;
        var rect = img.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;
        if (!intersectsViewport(rect)) continue;
        results.images.push({
            src: img.src, x: rect.left, y: rect.top, w: rect.width, h: rect.height,
            alt: img.alt || ''
        });
    }

    // <input>/<textarea> values are NOT DOM text nodes - they're native
    // form-control content, invisible to the TreeWalker above. Collect them
    // separately so the terminal renderer can still show what's typed.
    var fields = body.querySelectorAll('textarea, input:not([type=checkbox]):not([type=radio]):not([type=hidden]):not([type=button]):not([type=submit]):not([type=file])');
    for (var fi = 0; fi < fields.length; fi++) {
        var field = fields[fi];
        if (!ancestorsVisible(field)) continue;
        var frect = field.getBoundingClientRect();
        if (frect.width <= 0 || frect.height <= 0) continue;
        if (!intersectsViewport(frect)) continue;
        var fstyle = window.getComputedStyle(field);
        var isPassword = (field.type === 'password');
        var rawValue = field.value || '';
        results.fields.push({
            value: isPassword ? new Array(rawValue.length + 1).join('\u2022') : rawValue,
            placeholder: field.placeholder || '',
            x: frect.left, y: frect.top, w: frect.width, h: frect.height,
            color: fstyle.color, bg: fstyle.backgroundColor, focused: (document.activeElement === field),
            tag: field.tagName
        });
    }

    results.pageWidth = Math.max(
        body.scrollWidth, document.documentElement.scrollWidth
    );
    results.pageHeight = Math.max(
        body.scrollHeight, document.documentElement.scrollHeight
    );
    results.scrollX = window.pageXOffset;
    results.scrollY = window.pageYOffset;
    results.title = document.title;

    // The page's own effective background - reuses the same effectiveBg()
    // walk as each text run's local background (see above), starting from
    // <body>. If that walk finds nothing (body and everything above it is
    // transparent) we fall back to sampling whatever element is actually
    // rendered at a safe point in the viewport and walking up from there -
    // some sites set their real background on an inner wrapper div that
    // isn't a text run's own ancestor at all.
    results.pageBackground = effectiveBg(body);
    if (!results.pageBackground) {
        try {
            var sample = document.elementFromPoint(
                Math.min(5, viewportW - 1), Math.min(5, viewportH - 1)
            );
            results.pageBackground = sample ? effectiveBg(sample) : null;
        } catch (e) { /* elementFromPoint can throw in edge cases - ignore */ }
    }

    return results;
}

// ── find-in-page (in-page function, injected via page.evaluate) ────────────
// Whole-document (not viewport-limited) case-insensitive text search.
// Scrolls the requested match into view and returns its post-scroll rect.
// A match that spans more than one DOM text node is skipped (rare, and
// not worth the added complexity here).

function _phasmaFindText(query, matchIndex) {
    if (!query) return { found: false, total: 0 };
    var q = String(query).toLowerCase();
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    var node;
    var matches = [];
    var MAX_MATCHES = 2000;

    while ((node = walker.nextNode())) {
        var parentTag = node.parentElement ? node.parentElement.tagName : '';
        if (parentTag === 'SCRIPT' || parentTag === 'STYLE' || parentTag === 'NOSCRIPT' ||
            parentTag === 'TITLE' || parentTag === 'TEMPLATE') continue;
        var raw = node.nodeValue;
        if (!raw) continue;
        var lower = raw.toLowerCase();
        var pos = 0;
        while (true) {
            var idx = lower.indexOf(q, pos);
            if (idx < 0) break;
            matches.push({ node: node, start: idx, end: idx + q.length });
            pos = idx + q.length;
            if (matches.length >= MAX_MATCHES) break;
        }
        if (matches.length >= MAX_MATCHES) break;
    }

    var total = matches.length;
    if (total === 0) return { found: false, total: 0 };
    var idx2 = ((matchIndex % total) + total) % total;
    var m = matches[idx2];
    try {
        var range = document.createRange();
        range.setStart(m.node, m.start);
        range.setEnd(m.node, m.end);
        var el = m.node.parentElement;
        if (el && el.scrollIntoView) el.scrollIntoView({ block: 'center', inline: 'nearest' });
        var rect = range.getBoundingClientRect();
        return {
            found: true, total: total, index: idx2,
            x: rect.left, y: rect.top, w: rect.width, h: rect.height
        };
    } catch (e) {
        return { found: false, total: total };
    }
}

// ── link hints (in-page function, injected via page.evaluate) ──────────────
// Tags every clickable/focusable element currently in the viewport with a
// temporary data-phasma-hint="hN" attribute (used as a lookup key so a
// later, separate RPC call can find and .click() the exact element without
// needing to hold a live JS reference across round trips) and returns each
// one's id + rect so the terminal can overlay a label on it.

function _phasmaComputeHints(viewportW, viewportH) {
    var results = [];
    var stale = document.querySelectorAll('[data-phasma-hint]');
    for (var s = 0; s < stale.length; s++) stale[s].removeAttribute('data-phasma-hint');

    var SELECTOR = "a[href], button, input:not([type=hidden]), textarea, select, " +
                    "[onclick], [role=button], [role=link]";
    var nodes = document.querySelectorAll(SELECTOR);
    var idx = 0;
    for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        var style = window.getComputedStyle(el);
        if (!style || style.display === 'none' || style.visibility === 'hidden') continue;
        var rect = el.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;
        if (rect.right <= 0 || rect.left >= viewportW || rect.bottom <= 0 || rect.top >= viewportH) continue;

        var id = 'h' + idx;
        el.setAttribute('data-phasma-hint', id);
        results.push({ id: id, x: rect.left, y: rect.top, w: rect.width, h: rect.height, tag: el.tagName });
        idx++;
    }
    return results;
}

// ── request router ────────────────────────────────────────────────────────────

function handleRequest(request, response) {
    var action = request.url.replace(/^\//, '').split('?')[0];
    var params  = parseBody(request);

    // navigate ----------------------------------------------------------------
    if (action === 'navigate') {
        var url = params.url;
        if (!url) { err(response, 'missing url'); return; }

        page.open(url, function (status) {
            if (status !== 'success') {
                err(response, 'Failed to load: ' + url);
                return;
            }
            // small settle delay so JS on the page can run
            setTimeout(function () {
                var html = page.evaluate(function () {
                    return document.documentElement.outerHTML;
                });
                ok(response, html);
            }, params.wait || 0);
        });
        return;
    }

    // evaluate ----------------------------------------------------------------
    if (action === 'evaluate') {
        var expr = params.expression;
        if (expr === undefined) { err(response, 'missing expression'); return; }
        try {
            var result = page.evaluate(function (e) { return eval(e); }, expr);
            ok(response, result);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // click -------------------------------------------------------------------
    if (action === 'click') {
        var selector = params.selector;
        if (!selector) { err(response, 'missing selector'); return; }
        var found = page.evaluate(function (sel) {
            var el = document.querySelector(sel);
            if (!el) return false;
            var ev = document.createEvent('MouseEvent');
            ev.initMouseEvent('click', true, true, window,
                              0, 0, 0, 0, 0, false, false, false, false, 0, null);
            el.dispatchEvent(ev);
            return true;
        }, selector);
        ok(response, found);
        return;
    }

    // fill --------------------------------------------------------------------
    if (action === 'fill') {
        var selector = params.selector;
        var value    = params.value;
        if (!selector) { err(response, 'missing selector'); return; }
        var found = page.evaluate(function (sel, val) {
            var el = document.querySelector(sel);
            if (!el) return false;
            el.value = val;
            ['input', 'change'].forEach(function (evName) {
                var ev = document.createEvent('Event');
                ev.initEvent(evName, true, true);
                el.dispatchEvent(ev);
            });
            return true;
        }, selector, value === undefined ? '' : value);
        ok(response, found);
        return;
    }

    // screenshot --------------------------------------------------------------
    if (action === 'screenshot') {
        var path = params.path;
        if (!path) { err(response, 'missing path'); return; }
        try {
            page.render(path);
            ok(response, path);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // pdf ---------------------------------------------------------------------
    if (action === 'pdf') {
        var path   = params.path;
        var format = params.format;
        var landscape = params.landscape || false;
        var margin = params.margin || '0';
        var width  = params.width;   // custom CSS size e.g. "400px"
        var height = params.height;  // custom CSS size e.g. "300px"
        if (!path) { err(response, 'missing path'); return; }
        try {
            var marginObj = (typeof margin === 'string')
                ? { top: margin, bottom: margin, left: margin, right: margin }
                : margin;

            if (width && height) {
                // custom pixel-exact paper size
                page.paperSize = {
                    width:  width,
                    height: height,
                    margin: marginObj
                };
            } else {
                page.paperSize = {
                    format:      format || 'A4',
                    orientation: landscape ? 'landscape' : 'portrait',
                    margin:      marginObj
                };
            }
            page.render(path, { format: 'pdf' });
            page.paperSize = {};
            ok(response, path);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // set_viewport ------------------------------------------------------------
    if (action === 'set_viewport') {
        page.viewportSize = {
            width:  params.width  || 1024,
            height: params.height || 768
        };
        ok(response, null);
        return;
    }

    // layout --------------------------------------------------------------------
    // Returns real text (never rasterized) plus the bounding boxes of <img>
    // elements only — those are the sole things the terminal renderer turns
    // into ASCII/ANSI block art.
    if (action === 'layout') {
        try {
            var vp = page.viewportSize;
            var data = page.evaluate(_phasmaComputeLayout, vp.width, vp.height);
            // Same page.evaluate() null->'' marshalling quirk as active_field
            // below can affect this nested property too.
            if (data && data.pageBackground === '') data.pageBackground = null;
            ok(response, data);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // scroll --------------------------------------------------------------------
    if (action === 'scroll') {
        try {
            var pos = page.evaluate(function (dx, dy, absolute) {
                if (absolute) {
                    window.scrollTo(dx, dy);
                } else {
                    window.scrollBy(dx, dy);
                }
                return { x: window.pageXOffset, y: window.pageYOffset };
            }, params.dx || 0, params.dy || 0, !!params.absolute);
            ok(response, pos);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // region_screenshot -----------------------------------------------------
    // Renders only a sub-rectangle of the current viewport to a PNG file.
    // Used exclusively for <img> regions — never for text.
    if (action === 'region_screenshot') {
        var rpath = params.path;
        if (!rpath) { err(response, 'missing path'); return; }
        try {
            var prevClip = page.clipRect;
            page.clipRect = {
                left: params.left || 0, top: params.top || 0,
                width: params.width || 1, height: params.height || 1
            };
            page.render(rpath);
            page.clipRect = prevClip || {};
            ok(response, rpath);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // mouse -----------------------------------------------------------------
    // type: 'click' | 'mousedown' | 'mouseup' | 'mousemove' | 'doubleclick'
    if (action === 'mouse') {
        try {
            var mtype = params.type || 'click';
            page.sendEvent(mtype, params.x || 0, params.y || 0, params.button || 'left');
            ok(response, null);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // key ---------------------------------------------------------------------
    // Either {text: "abc"} to type literal characters, or {special: "Backspace"}
    // for a named key (Backspace, Enter, Tab, Left, Right, Up, Down, Escape,
    // Delete, Home, End).
    if (action === 'key') {
        try {
            if (params.special) {
                var code = page.event.key[params.special];
                if (code === undefined) { err(response, 'unknown special key: ' + params.special); return; }
                // Enter needs the full keydown -> keypress -> keyup sequence:
                // React-based forms and most "submit on Enter" handlers
                // listen on 'keydown', not 'keypress' (deprecated for
                // non-character keys in some engines and may not even fire
                // for them at all) - a bare keypress alone silently does
                // nothing on many real sites. Other special keys
                // (Backspace, arrows, ...) already have their expected
                // single-action behavior tied to just 'keypress' here, and
                // additionally sending 'keydown' for those double-fires
                // the browser's own default action (e.g. Backspace would
                // delete two characters instead of one) - so only Enter
                // gets the extra events.
                if (params.special === 'Enter') {
                    page.sendEvent('keydown', code);
                    page.sendEvent('keypress', code);
                    page.sendEvent('keyup', code);
                } else {
                    page.sendEvent('keypress', code);
                }
            } else {
                page.sendEvent('keypress', params.text || '');
            }
            ok(response, null);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // active_element ------------------------------------------------------------
    if (action === 'active_element') {
        try {
            var info = page.evaluate(function () {
                var el = document.activeElement;
                if (!el) return null;
                var tag = el.tagName;
                var editable = (tag === 'INPUT' || tag === 'TEXTAREA' || el.isContentEditable);
                var type = tag === 'INPUT' ? (el.type || 'text') : null;
                return { tag: tag, editable: !!editable, type: type };
            });
            ok(response, info);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // active_field ------------------------------------------------------------
    // Rect + current value + placeholder of the focused <input>/<textarea>.
    // Deliberately implemented via a function reference (like layout/hints),
    // NOT via the generic string-based `evaluate` action - that one calls
    // eval() internally and is silently blocked by any page with a
    // script-src CSP lacking 'unsafe-eval' (i.e. most real production
    // sites, GitHub and PyPI included). Function-reference page.evaluate()
    // is a privileged PhantomJS binding, not a page-context eval() call, so
    // it isn't subject to that restriction.
    if (action === 'active_field') {
        try {
            var field = page.evaluate(function () {
                var el = document.activeElement;
                if (!el) return null;
                var t = el.tagName;
                if (t !== 'INPUT' && t !== 'TEXTAREA') return null;
                var r = el.getBoundingClientRect();
                return {
                    value: el.value || '', placeholder: el.placeholder || '',
                    x: r.left, y: r.top, w: r.width, h: r.height,
                    isPassword: (el.type === 'password')
                };
            });
            // PhantomJS's page.evaluate() marshalling can turn a JS `null`
            // return value into an empty string when crossing back out of
            // the page context - normalize defensively so callers reliably
            // see either a real object or JSON null, never ''.
            if (!field || typeof field !== 'object') field = null;
            ok(response, field);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // set_active_value ------------------------------------------------------------
    // Sets the focused element's value in one round trip (used by the
    // debounced local-echo flush) and fires input/change so page JS
    // (search-as-you-type, validation, ...) still reacts to it.
    if (action === 'set_active_value') {
        try {
            var applied = page.evaluate(function (v) {
                var el = document.activeElement;
                if (!el) return false;
                el.value = v;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }, params.value || '');
            ok(response, applied);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // blur_active -----------------------------------------------------------------
    if (action === 'blur_active') {
        try {
            page.evaluate(function () {
                if (document.activeElement && document.activeElement.blur) {
                    document.activeElement.blur();
                }
            });
            ok(response, null);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // find_text -----------------------------------------------------------------
    // Whole-document text search (not just the current viewport) -
    // scrolls the Nth match into view and returns its rect so the
    // terminal can highlight it. Vimium-style `/` + n/N.
    if (action === 'find_text') {
        try {
            var found = page.evaluate(_phasmaFindText, params.query || '', params.index || 0);
            if (!found || typeof found !== 'object') found = { found: false, total: 0 };
            ok(response, found);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // hints -----------------------------------------------------------------
    // Link-hints mode (vimium-style): tags every clickable/focusable element
    // in the viewport and returns id+rect for each so the terminal can
    // overlay a label; hint_click(id) later performs the actual click.
    if (action === 'hints') {
        try {
            var vp = page.viewportSize;
            var targets = page.evaluate(_phasmaComputeHints, vp.width, vp.height);
            ok(response, targets);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // hint_click --------------------------------------------------------------
    if (action === 'hint_click') {
        var hintId = params.id || '';
        try {
            var clicked = page.evaluate(function (id) {
                var el = document.querySelector('[data-phasma-hint="' + id + '"]');
                if (!el) return false;
                el.click();
                if (el.focus) { el.focus(); }
                return true;
            }, hintId);
            if (clicked) {
                ok(response, null);
            } else {
                err(response, 'hint not found: ' + hintId);
            }
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // clear_hints ---------------------------------------------------------------
    if (action === 'clear_hints') {
        try {
            page.evaluate(function () {
                var tagged = document.querySelectorAll('[data-phasma-hint]');
                for (var i = 0; i < tagged.length; i++) tagged[i].removeAttribute('data-phasma-hint');
            });
            ok(response, null);
        } catch (e) {
            err(response, e.message);
        }
        return;
    }

    // exit --------------------------------------------------------------------
    if (action === 'exit') {
        ok(response, null);
        setTimeout(function () { phantom.exit(0); }, 50);
        return;
    }

    // unknown -----------------------------------------------------------------
    err(response, 'unknown action: ' + action);
}

// ── startup ───────────────────────────────────────────────────────────────────

var port = parseInt(system.args[1], 10) || 0;

// If port 0 is requested, try ports starting from 19700 until one is free.
// PhantomJS webserver.listen() returns false on failure.
if (port === 0) {
    port = 19700;
    while (!server.listen(port, handleRequest)) {
        port += 1;
        if (port > 19800) {
            system.stderr.write('ERROR: no free port found\n');
            phantom.exit(1);
        }
    }
} else {
    if (!server.listen(port, handleRequest)) {
        system.stderr.write('ERROR: cannot listen on port ' + port + '\n');
        phantom.exit(1);
    }
}

// Print the actual port to stdout so Python can read it.
system.stdout.write('READY ' + port + '\n');
system.stdout.flush();

// PhantomJS event loop keeps running — no phantom.exit() here.
