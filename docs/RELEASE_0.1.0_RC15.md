# SDK 0.1.0-rc15 - World Builder and Custom Map Loader

World Builder 0.32.0-experimental adds reusable region templates and faster live placement. Map Overlays is now **Custom Map Loader 0.2.0**, which assigns a World Builder save to each vanilla level and spawns it when that level loads.

## Changes
- F3/F4 select region corners; rotate, move, resize or scale the visible bounds, including individual-corner adjustment and held +/- buttons.
- Save reusable templates with mesh transforms and instanced props. Preview, position and apply an entire group as tracked map assets.
- Batch region scans, preview spawning and up to 128 transforms per native request, with a 4 ms transform work budget.
- Drag the open left side to look around in template, duplication and bounds menus. While dragging, WASD flies, Space/E rises, Ctrl/Q lowers, and Shift boosts.
- Large previews spawn closer to the camera; Bring preview here relocates the unapplied group.
- F1 collapses Controls help while keeping Current Selection visible.
- Custom Map Loader works with builder camera on or off. Unavailable built-in world edits are skipped with a count instead of blocking custom props. Skipped edits are not retried during that visit; the original save remains unchanged.

## Installation and compatibility
Close the game and SDK. Extract the SDK ZIP into the game directory, then extract the World Builder and Custom Map Loader ZIPs there. Replace existing files.

Custom Map Loader intentionally keeps `SDK_Mods/E33MapOverlays.sdkmod` and its existing internal ID. This preserves enabled state, startup order and assignments; do not install another copy under a new filename. World Builder must load first. F2 opens the custom-map assignment menu.

Use the matching RC15 SDK: template scans, group transforms and menu navigation require its native operations. Existing maps, templates, thumbnails and settings remain local and are not bundled. The optional thumbnail archive includes its import instructions.

## Validation and limits
147 automated tests passed across World Builder, builder packet/menu recovery, templates, packaging and startup order. Prior in-game testing verified a 2,003-prop template with batch movement and camera navigation in placement menus. The latest mapping-load fixes were tested in game with 1,798 custom props and two available built-in edits; the user confirmed successful loading. Missing built-in edits are covered by regression tests.

Built-in object edits remain subject to level streaming. Templates copy supported loaded static meshes and transforms, not gameplay scripts, skeletal actors or material overrides. A new fresh-launch test of the final RC15 archives has not been performed.
