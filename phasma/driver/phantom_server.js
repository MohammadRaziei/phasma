/**
 * PhantomJS HTTP server - persistent session with JSON RPC over HTTP.
 * Started by DriverPersistent, listens on a random port, communicates via JSON.
 *
 * Protocol:
 *   POST /<action>   body: JSON params
 *   Response:        {"ok": true,  "data": ...}
 *                 or {"ok": false, "error": "..."}
 *
 * Actions: navigate, evaluate, click, fill, screenshot, set_viewport, exit
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
