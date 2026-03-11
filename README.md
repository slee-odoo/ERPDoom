# ERPDoom 🔫

> *Rip and tear through your workday.*

An Odoo 19 addon that embeds the classic **id Software DOOM** (shareware) directly inside your Odoo backend — because every ERP needs a stress relief valve.

---

## Features

- Play the original 1993 DOS DOOM entirely within the Odoo web interface
- Runs via [js-dos](https://js-dos.com/) (DOSBox compiled to WebAssembly) — no plugins, no installs
- Full-viewport, fullscreen-capable gameplay
- Isolated in an iframe so the game never conflicts with Odoo's JS bundle
- Keyboard focus is grabbed automatically — no click required to start playing

---

## Requirements

- Odoo 19
- A modern browser with WebAssembly support (Chrome, Firefox, Edge, Safari)
- An internet connection on first launch (js-dos loads game files remotely)

---

## Installation

1. Clone or copy the `doom_game` module into your Odoo addons path:

   ```bash
   git clone https://github.com/slee-odoo/ERPDoom.git /path/to/odoo/addons/doom_game
   ```

2. Restart your Odoo server and update the app list:

   ```bash
   ./odoo-bin -u all
   ```

3. In Odoo, go to **Apps**, search for **DOOM**, and click **Install**.

4. A new **DOOM** menu entry will appear in the top navigation. Click it and rip and tear.

---

## Controls

| Key | Action |
|---|---|
| Arrow keys | Move / Turn |
| Ctrl | Shoot |
| Space | Open doors / Activate |
| Alt + Enter | Toggle fullscreen |
| F1 | Help |
| F2 | Save game |
| F3 | Load game |
| F5 | Detail level |
| F6 | Quicksave |

---

## How It Works

The addon registers an Odoo client action (`doom_game_action`) backed by an OWL component. The component renders a full-viewport `<iframe>` pointing to `/doom/game`, a route served by a Python controller that returns the js-dos HTML shell. The WebAssembly DOSBox runtime and DOOM shareware files are loaded from the js-dos CDN at runtime, keeping the addon's repository footprint small (the `static/game/` directory contains only the necessary bootstrap assets).

The iframe isolation ensures the DOSBox WebAssembly memory context never collides with Odoo's own JavaScript runtime.

---

## License

LGPL-3 — see [LICENSE](https://www.gnu.org/licenses/lgpl-3.0.html).

DOOM (shareware) is a trademark of id Software. This addon uses only the freely distributable shareware episode. No commercial DOOM content is included or redistributed.

---

## Disclaimer

Productivity losses caused by this module are the sole responsibility of the person who installed it.
