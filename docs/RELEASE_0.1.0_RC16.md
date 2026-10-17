# SDK 0.1.0-rc16 - Map Travel, readiness and World Builder controls

RC16 adds Map Travel 0.2.2 and updates World Builder to 0.32.1-experimental.
Install the matching SDK before updating optional mods. Close the game and SDK,
then extract the game-root ZIPs beside Sandfall. Existing settings and saved maps
are preserved; release archives contain no personal configuration or saved maps.

## Changes

- Map Travel groups matching map names and invokes the game's normal zone
  transition, arriving at the table-defined entrance in one load. The SDK resumes
  through the game's pause callback first. Full Unreal FName suffix comparison
  fixes numbered map variants. A rejected preflight no longer automatically
  reopens a menu with stale Slate focus.
- Mods and Map Travel scrolling retain fixed widget rows for the current catalog.
  Pause entries keep Mods above Map Travel across rebuilds.
- The Mods pause entry is the first SDK UI built. It shows widget construction,
  saved-mod counts and SDK readiness before the full menu is opened. The Mods
  menu includes a readiness progress bar. Enabled mods restore in saved order
  while the pause menu is open, with readiness waits between startup steps.
- Shared pause-click observers own their renewal deadline; rebuilding one button
  cannot postpone renewal beyond the original observer expiry. Confirmed expired
  or capped observers recover without restarting the SDK.
- World Builder: P plays from the current camera using the existing placement
  checks; H hides/shows the complete builder HUD. Both are remappable. F7 displays
  Building Widgets... while constructing its menu and restores help afterward.
- Introspection reads bounded FString fields inside reflected structures and up
  to 256 array entries, supporting the game's 185 console-autocomplete entries.
- Asset converter updates include opaque-eye layer handling and iris/sclera baking.

## Validation and limits

231 focused automated tests ran: 230 passed and one installed-game-manifest
check was skipped outside the game installation. The new numbered-name native
fixture passed, and the v68 runtime/controller and string-aware read worker built.

Live testing verified Frozen Heart -> Boat Graveyard 2 -> Boat Graveyard 1 in one
SDK session, with entrance arrival and reconstructed pause entries. Earlier tests
verified the paused normal transition to Ancient Sanctuary. All maps have not
been individually playtested. Menu cleanup still takes about 9-10 seconds before
travel starts; this release adds feedback rather than claiming to remove it.

Expired pause observers were repaired in a running session, and both Mods and
Map Travel buttons reopened successfully. Mods scrolling and readiness advancing
from 5/9 through 9/9 were checked in game. The pause readiness label and new
World Builder P/H controls passed automated checks but await fresh-start visual
and input validation. Fixed mod rows cover up to 36 entries; larger mod lists
retain the previous recycled-row fallback. Map Travel supports 72 fixed rows.

Picto Editor can still suspend on a stale reflected identity after travel; this
is separate from the core SDK and map-route fixes. World Builder templates,
Custom Map Loader and other RC15 functionality remain available. Existing limits
on streamed built-in geometry and experimental character replacement still apply.
