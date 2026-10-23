# SDK 0.1.0-rc18 — startup preparation and Mods menus

RC18 pairs the SDK with native runtime210. Install the matching SDK ZIP before
updating optional mods. Downloads contain SDK runtime files and public mod sources/assets; existing
user settings, saved maps and local custom packages are not included.

## Changes

- World Builder prepares its detached catalog and HUD before gameplay and now
  retires its native resources on world changes. Saved ON choices reactivate
  after returning to title and loading again in the same SDK session.
- Map Travel prepares its pause entry during loading and adopts that exact
  owner at activation. Flight prepares copied function schemas and starts its
  read worker before the save loads. Map Loader starts its passive context observer during preparation.
- The foreground world-check worker starts during loading. Every activation
  still reads the current world, save, local-player and pawn binding twice;
  copied background selectors only avoid repeated discovery.
- Synchronous activation no longer repaints the closed Mods menu or polls all
  earlier mods between every enable. Open menus still receive current state.
- Foreign mod presenters are not deep-copied into the shared menu cache; their
  model objects can own worker locks and Sessions without breaking menu open.
- Public mods can prepare management metadata before a save loads. The title
  screen Mods button stages desired enable states, options and keybinds;
  gameplay activation waits for a loaded-world admission.
- Title and pause menus retain exact widget and metadata identities before
  caching calls. Owned cleanup and acknowledged native outcomes remain required.
- Keybind lists use fixed row widgets and bounded active callback windows.
  Native focus ownership accommodates the larger reusable list.
- Native lease release batching and colored startup status are included in210.
- World retirement revokes queued world actions and uses explicit native cleanup
  for borrowed UI and SDK-owned props. Cleanup owners remain retained until
  acknowledgments arrive; unsupported or unknown outcomes stay held without
  automatically replaying gameplay changes.
- The `startuptiming` console command separates measured preparation and enable work from
  time until a mod reports its feature entry usable. Activations above 200 ms
  appear yellow in that report, which includes total activation work. Detailed
  timings are recorded silently and stay out of normal startup output.
  Mods without an explicit readiness signal report usability as unreported.
  Readiness does not mean every asset used by future actions is already loaded.
- Cinematics prepares its installed manifest/catalog before world activation,
  while current-save unlock/history checks remain live. Picto activation keeps
  baseline capture and saved gameplay restoration before optional catalog/UI
  preparation. A failed Picto restore is reported as failed activation.
- Scene Editor revokes queued editor actions before cleanup. Enemy Spawner
  preserves the RC17 encounter routes and the `-` catalog shortcut.

These changes preserve the representative RC17 encounter and cinematic results;
they do not imply every catalog entry has been individually tested. Startup and
menu timings depend on the installation and current game state.

## Validation

- 1,995 SDK tests completed successfully (8 existing skips); 140 World Builder tests passed.
- Runtime210 and its native fixtures compiled with MSVC `/W4 /WX`.
- Live title and gameplay Mods-button opens measured approximately 150–197 ms
  after preparation. Initial preparation and individual mod activation
  still take additional time; `startuptiming` reports those costs separately.
- A clean runtime210 load restored seven gameplay mods in 1.59 seconds after
  the owner-thread exploration-ready observation, versus about 11 seconds
  before these changes. World Builder finished 10.35 seconds of preparation
  before selecting the save. This is not a zero-delay gameplay-readiness claim.
- Title → save → title → save retained the SDK process and menu shell. Map
  Travel, Continent Flight, Scene Editor, WorldBuilder Map Loader and Enemy
  Spawner retired and reactivated with acknowledged cleanup and no pending leases.
- Active cinematic presentations/media, Scene visual-arena restitution and
  encounter tuning still retain unsupported retirement owners rather than
  restoring old-world state. Ordinary inactive browser/editor cleanup is supported.

## Optional map loader upgrade

Use `WorldBuilderMapLoader.sdkmod`. It replaces the legacy
`E33MapOverlays.sdkmod`; do not install both. With the game and SDK closed,
remove the old `SDK_Mods/E33MapOverlays.sdkmod` and its generated
`SDK/mods/E33MapOverlays` cache before installing the replacement. Keep user
settings and saved maps. The replacement includes its prepared-map store and
context observer.

## Release inventory

The SDK archive contains runtime210, its matching native controller, the bundled
Python runtime, public SDK Python sources, licensing notices and core mods.
Optional mods, World Builder, Scene Editor, Enemy Spawner and Asset Converter
are separate downloads. The source archive includes `gpu/` dependencies and the
public build scripts. Build runtime210 with
`scripts/build-rc18-native.cmd` (including the thumbnail worker), prepare the
pinned runtime and bootstrap with their existing scripts, then package a new destination with
`scripts/package_rc18.py` after committing the reviewed public source inputs.

The packager recursively audits nested `.sdkmod` and ZIP archives, rejects local
state and saved maps, and writes SHA-256 checksums for the final artifacts.
