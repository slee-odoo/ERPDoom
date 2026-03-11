from odoo import http
from odoo.http import Response

# Emscripten port of Doom using SDL2 (audio) + WebGL (rendering).
# Engine: neilrackett/doom (GPL) — doom.js + doom.wasm + doom.data (IWAD)
# All three files are served from the module's own static directory so the
# module works entirely offline inside Docker.

DOOM_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>DOOM</title>
    <style>
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

        html, body {
            width: 100%; height: 100%;
            background: #000;
            overflow: hidden;
        }

        /* ── Canvas fills the whole viewport, centred ──────────────────── */
        #viewport {
            width: 100%; height: 100%;
            display: flex; align-items: center; justify-content: center;
        }

        #canvas {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
            /* Smooth (bilinear) upscaling — no extra pixelation */
            image-rendering: auto;
        }

        /* ── Loading splash ─────────────────────────────────────────────── */
        #splash {
            position: fixed; inset: 0;
            background: #000;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            gap: 22px; z-index: 20;
            font-family: 'Courier New', Courier, monospace;
        }
        #splash.gone { display: none; }

        .doom-logo {
            color: #cc0000;
            font-size: clamp(56px, 12vw, 108px);
            font-weight: 900; letter-spacing: .12em;
            text-shadow: 0 0 12px #ff0000, 0 0 28px #cc0000, 5px 5px 0 #550000;
            user-select: none;
        }
        .tagline { color: #555; font-size: 13px; letter-spacing: .18em; text-transform: uppercase; }

        .bar-wrap { width: min(380px, 80vw); }
        .bar-label {
            color: #cc0000; font-size: 11px; letter-spacing: .14em;
            text-transform: uppercase; text-align: center; margin-bottom: 6px;
        }
        .bar-outer { height: 16px; border: 2px solid #cc0000; background: #111; box-shadow: 0 0 8px #cc000055; }
        .bar-inner {
            height: 100%; width: 0%;
            background: linear-gradient(90deg, #880000, #ff2200);
            box-shadow: 0 0 6px #ff4400;
            transition: width .15s ease;
        }

        .hint {
            color: #3a3a3a; font-size: 11px; letter-spacing: .1em;
            line-height: 1.9; text-align: center;
            font-family: 'Courier New', Courier, monospace;
        }
        .hint b { color: #555; font-weight: normal; }

        /* ── Click-to-focus overlay ─────────────────────────────────────── */
        #focus-banner {
            position: fixed; bottom: 0; left: 0; right: 0;
            background: rgba(0,0,0,.8);
            color: #cc0000; font-size: 13px; letter-spacing: .1em;
            text-align: center; padding: 10px 0;
            display: none; z-index: 10;
            font-family: 'Courier New', Courier, monospace;
            cursor: pointer;
        }
    </style>
</head>
<body>

<div id="splash">
    <div class="doom-logo">DOOM</div>
    <div class="tagline">id Software &bull; 1993</div>

    <div class="bar-wrap">
        <div class="bar-label" id="bar-label">Initialising&hellip;</div>
        <div class="bar-outer"><div class="bar-inner" id="bar-inner"></div></div>
    </div>

    <div class="hint">
        <b>↑ ↓ ← →</b> Move &nbsp;&bull;&nbsp; <b>Ctrl</b> Shoot &nbsp;&bull;&nbsp;
        <b>Space</b> Use &nbsp;&bull;&nbsp; <b>Shift</b> Run &nbsp;&bull;&nbsp;
        <b>Alt + ← →</b> Strafe<br>
        <b>Enter</b> Confirm &nbsp;&bull;&nbsp; <b>Esc</b> Menu &nbsp;&bull;&nbsp;
        <b>F1–F6</b> Save/Load/Options &nbsp;&bull;&nbsp; <b>F11</b> Fullscreen
    </div>
</div>

<div id="viewport">
    <canvas id="canvas" width="1" height="1" tabindex="0" oncontextmenu="return false;"></canvas>
</div>

<div id="focus-banner" onclick="document.getElementById('canvas').focus()">
    Click here to capture keyboard &amp; audio input
</div>

<script>
(function () {
    'use strict';

    var splash    = document.getElementById('splash');
    var barInner  = document.getElementById('bar-inner');
    var barLabel  = document.getElementById('bar-label');
    var canvas    = document.getElementById('canvas');
    var focusBanner = document.getElementById('focus-banner');

    function setProgress(pct, label) {
        barInner.style.width = Math.min(100, pct) + '%';
        if (label) barLabel.textContent = label;
    }

    function showError(msg) {
        barLabel.textContent = 'ERROR: ' + msg;
        barInner.style.background = '#884400';
        barInner.style.width = '100%';
        console.error('DOOM init error:', msg);
    }

    // Catch unhandled JS errors (WASM traps surface here too).
    // Return true / preventDefault to suppress the browser's default error
    // handling — in an iframe context (Odoo backend) an unhandled error would
    // otherwise trigger the parent frame's error UI, which can steal focus from
    // the canvas and break SDL2 keyboard input.
    window.onerror = function (msg, src, line, col, err) {
        showError(String(err || msg));
        return true; // suppress default browser handling
    };
    window.onunhandledrejection = function (e) {
        showError(String(e.reason));
        e.preventDefault();
    };

    function hideSplash() {
        splash.classList.add('gone');
        // Give the canvas focus so keyboard + audio context work immediately.
        // Audio context is resumed on the first user gesture (canvas click/focus).
        canvas.focus();
    }

    // ── Emscripten Module config ─────────────────────────────────────────────
    // doom.js uses Module.locateFile() to resolve doom.wasm and doom.data.
    // We redirect those to our own static paths.
    var STATIC = '/doom_game/static/game/';

    window.Module = {
        canvas: canvas,

        // Pixel density for SDL rendering — 1 = native 320×200 (upscaled by CSS)
        // 2 = 640×400 internal res (sharper but still retro).
        doomPixelRatio: window.devicePixelRatio >= 2 ? 2 : 1,

        locateFile: function (path) {
            // Append file sizes as cache-busters so a browser that cached
            // the old diekmann wasm (6.8 MB) is forced to re-fetch the
            // current neilrackett builds.
            var busters = { 'doom.wasm': '1548861', 'doom.data': '4196020' };
            var qs = busters[path] ? '?v=' + busters[path] : '';
            return STATIC + path + qs;
        },

        // Progress callbacks from Emscripten file loading.
        // Emscripten signals "all done" by calling setStatus('') — empty string.
        setStatus: function (text) {
            if (!text) {
                // Loading complete — hide the splash.
                setProgress(100, 'Starting\u2026');
                setTimeout(hideSplash, 300);
                return;
            }
            var m = text.match(/([^(]+)\((\d+)\/(\d+)\)/);
            if (m) {
                var pct = (parseInt(m[2]) / parseInt(m[3])) * 100;
                setProgress(pct, m[1].trim() + '\u2026');
            } else {
                setProgress(5, text);
            }
        },

        monitorRunDependencies: function (left) {
            // Backup: also hide splash when all async dependencies resolve.
            if (left === 0) {
                setProgress(100, 'Starting\u2026');
                setTimeout(hideSplash, 300);
            }
        },

        print:    function (t) { console.log(t); },
        printErr: function (t) { console.warn(t); },

        onAbort: function (what) {
            showError('WASM abort: ' + what);
        },

        quit: function (status, toThrow) {
            showError('Doom exited with status ' + status + ': ' + toThrow);
            throw toThrow;
        },
    };

    // ── Save-file persistence (IndexedDB) ───────────────────────────────────
    // DOOM saves to files like doomsav0.dsg … doomsav5.dsg in MEMFS.
    // We mirror these to IndexedDB so they survive page reloads.
    //
    // IMPORTANT: We never use setInterval to poll Module.FS — touching
    // Emscripten's FS from a timer callback outside the game loop freezes
    // SDL2 input.  Instead we sync only on beforeunload / visibilitychange
    // (i.e. when the user navigates away or hides the tab) and restore once
    // when the splash hides.
    var DB_NAME = 'doom_saves';
    var DB_STORE = 'files';
    var SAVE_PATTERN = /^\/doomsav\d\.dsg$/;

    function openDB(cb) {
        try {
            var req = indexedDB.open(DB_NAME, 1);
            req.onupgradeneeded = function () { req.result.createObjectStore(DB_STORE); };
            req.onsuccess  = function () { cb(req.result); };
            req.onerror    = function () {
                console.warn('DOOM: IndexedDB unavailable, saves will not persist');
                cb(null);
            };
        } catch (e) {
            console.warn('DOOM: IndexedDB not available');
            cb(null);
        }
    }

    function restoreSaves() {
        openDB(function (db) {
            if (!db) return;
            var tx = db.transaction(DB_STORE, 'readonly');
            var store = tx.objectStore(DB_STORE);
            var req = store.getAll();
            var keyReq = store.getAllKeys();
            tx.oncomplete = function () {
                var keys = keyReq.result || [];
                var vals = req.result || [];
                for (var i = 0; i < keys.length; i++) {
                    try {
                        Module.FS.writeFile(keys[i], new Uint8Array(vals[i]));
                        console.log('DOOM: restored ' + keys[i]);
                    } catch (e) {
                        console.warn('DOOM: failed to restore ' + keys[i], e);
                    }
                }
            };
        });
    }

    function syncSaves() {
        var fs;
        try { fs = Module.FS; } catch (e) { return; }
        var files;
        try { files = fs.readdir('/'); } catch (e) { return; }
        var saves = files.filter(function (f) { return SAVE_PATTERN.test('/' + f); });
        if (!saves.length) return;
        openDB(function (db) {
            if (!db) return;
            var tx = db.transaction(DB_STORE, 'readwrite');
            var store = tx.objectStore(DB_STORE);
            saves.forEach(function (name) {
                try {
                    var data = fs.readFile('/' + name);
                    store.put(data.buffer, '/' + name);
                } catch (e) { /* file removed between readdir and readFile */ }
            });
        });
    }

    // Restore saves once after the splash hides (runtime is stable).
    // Use a one-shot MutationObserver on the splash element so we don't
    // need to modify hideSplash or hook into Emscripten at all.
    var _splashObserver = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
            if (splash.classList.contains('gone')) {
                _splashObserver.disconnect();
                restoreSaves();
                // Persist saves when the user leaves (no polling).
                window.addEventListener('beforeunload', syncSaves);
                document.addEventListener('visibilitychange', function () {
                    if (document.hidden) syncSaves();
                });
                console.log('DOOM: save persistence active');
                return;
            }
        }
    });
    _splashObserver.observe(splash, { attributes: true, attributeFilter: ['class'] });

    // ── Focus / audio context handling ───────────────────────────────────────
    canvas.addEventListener('focusin', function () {
        focusBanner.style.display = 'none';
    });
    canvas.addEventListener('focusout', function () {
        focusBanner.style.display = 'block';
    });
    document.addEventListener('keydown', function () {
        if (document.activeElement !== canvas) canvas.focus();
    });

    // When running inside an Odoo iframe, the parent frame can steal focus
    // (e.g. a notification toast, background RPC finishing, etc.).
    // Once the iframe window loses focus, SDL2 stops receiving keyboard events.
    // Reclaim focus automatically — but only when the tab is still visible
    // (document.hidden guards against fighting the user when they switch tabs).
    window.addEventListener('blur', function () {
        if (document.hidden) return;
        if (!splash.classList.contains('gone')) return;
        setTimeout(function () { canvas.focus(); }, 50);
    });

    // ── Fullscreen on F11 ────────────────────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.key === 'F11') {
            e.preventDefault();
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(function () {});
            } else {
                document.exitFullscreen().catch(function () {});
            }
        }
    });

    // Kick off the initial progress display
    setProgress(2, 'Loading DOOM\u2026');
    // Safety net: force-hide splash after 30 s if callbacks never fire
    setTimeout(hideSplash, 30000);
})();
</script>

<!-- Emscripten Doom — SDL2 (audio + input) + WebGL (rendering) -->
<script async src="/doom_game/static/game/doom.js"></script>

</body>
</html>
"""


class DoomController(http.Controller):

    @http.route('/doom/game', type='http', auth='user', csrf=False)
    def doom_game(self, **kwargs):
        """Standalone DOOM page served inside the Odoo backend iframe."""
        headers = {'Cache-Control': 'no-store'}
        return Response(DOOM_HTML, content_type='text/html; charset=utf-8', headers=headers)
