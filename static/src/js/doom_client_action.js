/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, onMounted, useRef } from "@odoo/owl";

/**
 * DoomGameAction
 *
 * A full-viewport client action that embeds the DOOM game page
 * (served by the Python controller at /doom/game) inside an iframe.
 *
 * Using an iframe keeps the DOSBox WebAssembly context isolated from
 * Odoo's JS bundle, avoiding any namespace or memory conflicts.
 */
class DoomGameAction extends Component {
    static template = xml`
        <div class="o_doom_wrapper">
            <iframe
                t-ref="gameFrame"
                src="/doom/game"
                title="DOOM"
                allowfullscreen="true"
                allow="autoplay; fullscreen"
            />
        </div>
    `;

    static props = ["*"];

    setup() {
        this.frameRef = useRef("gameFrame");

        onMounted(() => {
            // Give the iframe keyboard focus immediately so DOOM controls work
            // without the user having to click first.
            const frame = this.frameRef.el;
            if (frame) {
                frame.focus();
            }
        });
    }
}

// Register under the tag used by the ir.actions.client record
registry.category("actions").add("doom_game_action", DoomGameAction);
