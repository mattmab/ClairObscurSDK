Custom Map Loader 0.2.0 (formerly Map Overlays)
Requires World Builder and the matching RC15 SDK.
Enable World Builder and Custom Map Loader in Mods. Press F2 to choose a saved
World Builder map for the current vanilla level. Each level remembers its own
assignment and loads it once per visit when exploration is ready.
Close the menu or use Load now to apply it in a clean visit. Builder camera may
be active or inactive; loading preserves that mode. Existing tracked scene edits
are never silently cleared. Failed attempts require re-entering the level.
Unloaded built-in world edits are skipped with a count so custom props can load.
Skipped edits are not retried later in that visit. The original saved map is
unchanged. Built-in edits remain subject to level streaming.
The archive and internal ID remain E33MapOverlays for upgrade compatibility.
Existing enabled state, startup order, assignments and saved maps are preserved.
Extract the archive into the game directory, replacing E33MapOverlays.sdkmod;
do not install a second copy under a different name. Close the game and SDK first.
Disable Custom Map Loader to stop future automatic loads; existing objects remain
managed by World Builder. No personal saves or assignments ship in this package.
