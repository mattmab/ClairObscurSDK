# E33 World Builder 0.30.0 — RC10 prerelease

Requires **Expedition33 SDK 0.1.0-rc10**, including the World Builder v53 native
adapter. Stock RC6 rejects the required commands and cannot run this mod.
Windows Steam build 23765773 is the supported target. Other builds are unverified.

Close the game and SDK controller. Install the RC10 SDK into the game folder,
preserving your settings, SDK_Assets and optional SDK_Mods. Do not overwrite an
unrelated version.dll loader. Put E33WorldBuilder.sdkmod in SDK_Mods. Start the
game, load an exploration save, and enable E33 World Builder in SDK Management.

Optional thumbnails: extract the thumbnail ZIP to any folder. With the SDK
controller closed, run the following in PowerShell, substituting your paths:

```powershell
& 'C:/YourGame/SDK/runtime/python.exe' 'C:/ThumbnailPack/import_thumbnails.py' --game 'C:/YourGame'
```

The importer verifies image hashes and the executable hash/container inventory,
then translates image filenames to your installation's cache keys. Existing
local pictures are preserved. The game still enumerates its own catalog.
Missing images can be generated with the in-game cache controls. Captured
images depict game assets; the SDK's code license does not license those assets.

F7 toggles the catalog. The top-right Close / F7 button closes the menu. F8 toggles builder camera, including from the catalog.
Escape closes the current preview/menu/camera layer. WASD flies; Space/Ctrl
move up/down; Shift accelerates. Hold left mouse to carry the aimed prop.
Numpad adjusts placement/rotation; Alt makes fine adjustments; Alt+Z undoes.
Save a named map before leaving: scene objects are session-owned.

Build browses/spawns assets; Gallery arranges batches; Library manages scene
instances; Maps saves/loads tracked scene assets and preview images. No enemy
controls are included. Landscapes, foliage instances and some translucent
surfaces are not selectable. Asset loading can still cause occasional stalls.

RC9 includes asynchronous GPU picking and background full-image readback,
neutral thumbnail processing, and the larger menu/resource capacities. It
retains the development native runtime's model/hair code, but this release's
packaging checks do not establish full model/hair gameplay regression coverage.

RC9 adds registry-indexed native mesh spawn batches, a 6,000-object scene
capacity, paginated map saves, and galleries of up to 5,000 static meshes.
Gallery batches have an owned floor; clearing or replacing a gallery removes
its floor and exhibits while preserving other scene objects. Oversized exhibits
are scaled to the spacing value (50-10,000 cm); saved map objects keep their
original transforms. Invalid or unloadable assets are reported and skipped.

Each native spawn command yields after approximately 4 ms of work. A single
cold Unreal asset load cannot be interrupted and can exceed that budget.
The menu processes short bursts and updates only progress text during spawning.

RC9 adds saved mouse sensitivity and flight speed, upward mouse look and stable
preview camera rotation, plus Play from camera. Highlighting supports Auto,
Click-only and Off. Selecting a gallery prop follows its asset in the catalog
for quick favoriting. F10 duplicates a spawned prop into your hand; the saved
Click copies toggle makes clicking gallery props create copies automatically.
Click again to place. Copies remain tracked for map saving.

Alt+Z undoes moves and duplicate placements. Alt+Y restores them with the same
transform and map tracking ID. New edits clear redo; history is limited to the
current session (64 entries), not stored in map files. Z is blocked from gameplay
while the builder camera is active so it cannot mount Esquie. Menu text entry
remains available. The shortcuts use queued key events to catch brief presses.

RC10 speeds up the catalog with cached path discovery, smaller UI planning observations, startup menu/HUD prewarming, a scoped reusable read-only worker, and bounded incremental thumbnail imports. SDK v53 adds validated image-brush batches (layout protocol 3). Warm folder transitions measured 0.2-0.4 seconds; first open after prewarming about 2.9 seconds; warm reopen about 0.9 seconds. Startup prewarming still takes approximately 6-8 seconds. Measurements vary with hardware and other enabled mods. Actor indexing refreshes on demand. Texture retention remains bounded and old-page queues are discarded on navigation.
