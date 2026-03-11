{
    'name': 'DOOM',
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Rip and tear through your workday. Play classic DOOM inside Odoo.',
    'description': """
        Play id Software's classic DOOM (shareware) directly inside Odoo.

        Uses js-dos (DOSBox compiled to WebAssembly) to run the original DOS game in your browser.
        Requires an internet connection to load the game files on first launch.

        Controls:
        - Arrow keys: Move
        - Ctrl: Shoot
        - Space: Open doors / Activate
        - Alt+Enter: Toggle fullscreen
        - F1-F6: Various in-game functions
    """,
    'author': 'Custom',
    'depends': ['web'],
    'data': [
        'views/doom_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'doom_game/static/src/js/doom_client_action.js',
            'doom_game/static/src/scss/doom.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
