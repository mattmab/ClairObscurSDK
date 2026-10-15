# SDK 0.1.0-rc9 - World Builder

World Builder **0.29.0** requires the included SDK **v52 native adapter**. Upgrade both the SDK and mod; stock RC8 lacks the new commands.

## Changes

- Saved mouse sensitivity and camera flight-speed controls, upward mouse look, and stable preview-camera movement.
- Play from camera returns to gameplay at the builder camera location.
- Highlight modes: automatic, only on click, or off.
- Selecting a spawned gallery prop follows its asset in the menu for quick favoriting.
- F10 / Duplicate puts a copy of a spawned prop in your hand. The saved **Click copies** toggle makes gallery clicks create copies automatically; click again to place.
- **Alt+Z** undoes duplicate placement without changing the original. **Alt+Y** restores the copy at the same position, rotation and scale with its map tracking ID intact. Brief keypresses are queued reliably.
- **Z** is blocked from gameplay during builder camera mode to prevent mounting Esquie.
- Retains RC8 bulk galleries (up to 5,000 props), gallery floors, 6,000 tracked map objects, Close / F7, and travel-safe menu rebuilding.

## Downloads and installation

Download **Expedition33-SDK-0.1.0-rc9.zip** and **E33WorldBuilder-0.29.0-rc9.zip**. The thumbnail pack and source bundle are optional. Checksums and validation are attached.

Close the game and SDK controller before upgrading. Extract the SDK into the game folder, preserving settings, SDK_Assets and optional SDK_Mods. Do not overwrite an unrelated version.dll loader. Put E33WorldBuilder.sdkmod in SDK_Mods. The thumbnail ZIP includes an importer and instructions; it translates cache keys for your installation.

F7 toggles the menu; F8 toggles freecam. Escape closes the current preview/menu/camera layer. WASD flies, Space/Ctrl moves up/down, Shift accelerates, and Numpad refines placement. Save a named map before leaving.

## Validation and limits

64 World Builder tests and 11 SDK lease tests passed. The packaged SDK manifest, bootstrap, bundled mods, ZIP integrity and artifact hashes passed validation. In-game Alt+Y restored a placed copy with an exact match of all 4,997 saved object records; cleanup preserved all 4,996 original objects exactly. Z was verified blocked while freecam remained active. The tested v52 binaries are hash-identical to the packaged binaries. Final verification restarted the SDK controller in the running game; no fresh RC9 game-process launch or full combat regression is claimed.

Undo/redo is current-session history (64 entries), not persisted in map files. New edits clear redo. Cold Unreal asset loads can still cause stalls. Landscapes, foliage instances and some translucent surfaces are not selectable. No enemy controls are included.

The optional pack contains **5,991 previews for 6,376 catalog meshes**; 385 entries have no supplied image. Game imagery is not covered by the SDK code license. Personal scenes, settings, map screenshots and logs are excluded.
