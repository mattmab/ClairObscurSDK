# SDK 0.1.0-rc13 - World Builder 0.31.0

World Builder 0.31.0 requires the matching RC13 SDK; install both downloads.

## World Builder

- F5 opens live duplication for the selected spawned prop. The left side stays
  clear so the world preview is visible. Combine X/Y/Z offsets, choose copy
  count and world/local axes, then Apply copies to retain map-tracked copies.
  Leaving the tab cancels unapplied previews; the original is preserved.
- Delete removes the current spawned selection. Alt+Z restores the deleted
  prop at the same position, rotation and scale with its stable map ID.
  Alt+Y repeats the deletion. Duplicate and deletion history work together.
- Deleted assets are retained while history needs them, so delayed undo still
  works after the game would otherwise unload their mesh. History is session-local.
- F7 from duplication switches directly to the Build prop catalog. F7 in Build
  closes the menu. Escape closes duplication without opening game pause.
- Current Selection and Controls HUD, menu cursor ownership improvements,
  moving-camera selection fixes and grouped actor selection are included.

## Matching SDK

Packages native v65-selection and command validation for deletion history and
menu routing. Includes optional-mod startup ordering, World Builder priority
when installed/enabled, Picto restoration batching, Mods configuration layout
fixes and keybind counts. Core services still initialize before optional mods.
See STARTUP_ORDER.txt for order configuration. No personal settings are bundled.

## Install

Close the game and SDK. Extract Expedition33-SDK-0.1.0-rc13.zip and
E33WorldBuilder-0.31.0.zip beside Sandfall. Preserve SDK/settings. Enable World
Builder in Pause > Mods if this is a first install. Existing enable choices
remain saved. The SDK bundles only Management, Introspection Harness and Live
Object Viewer; Map Overlays is not included in this download.

The optional thumbnail ZIP contains a portable cache and importer. Extract it
outside the game, then run the included import_thumbnails.py using the SDK's
bundled Python with --game pointing at the game folder. Run with the SDK closed.
Only existing neutral asset captures are included, not personal map previews.

## Validation and limits

Validated the native build with warnings treated as errors. World Builder:
107 tests; native command wire: 4; startup order: 4; management: 54; workspace
scroll: 5; Picto restoration: 15. Package integrity and nested archive audits
are checked before upload.

Live game checks on 2026-10-16 passed repeated deletion/undo/redo cycles with
saved transform and stable map ID checks, mixed duplicate/deletion history,
delayed keyboard Alt+Z/Alt+Y, F5 to F7 props, and Escape closing duplication.
The packaged runtime is hash-matched to that tested build. This is not a claim
that every feature or asset was tested from the final downloaded release.

Level streaming can reset the position of moved built-in world objects when
the game unloads and reloads those assets. Custom-placed props do not
participate in level streaming and are unaffected by those unload/reload cycles.

Supports the verified Steam executable fingerprint documented in
INSTALLABLE_RELEASE.md. Landscape and individual foliage/instanced models,
transparent surfaces without scene depth, and unavailable streamed assets
remain limited. Save maps in their original level. New edits clear redo;
undo history does not survive restarting the game.
