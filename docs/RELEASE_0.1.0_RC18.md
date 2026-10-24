# SDK 0.1.0-rc18 — startup preparation and Mods menus

RC18 pairs the SDK with native runtime213 and WorldBuilder Map Loader 0.2.4. Install the matching SDK ZIP before
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
- Title attachment defers confirmed stale/busy reference acquisition and pure
  discovery races before borrowed UI mutations. Previously these timing races
  could exit the SDK controller during a cold launch. Completed acquisitions
  remain owned, and unknown outcomes are not replayed.
- Title and pause menus retain exact widget and metadata identities before
  caching calls. Owned cleanup and acknowledged native outcomes remain required.
- Keybind lists use fixed row widgets and bounded active callback windows.
  Native focus ownership accommodates the larger reusable list.
- Native lease release batching and colored startup status remain included.
- Controller replacement retires only the old pause entry when the shared menu
  belongs to Process UI. An already-disposed shared tree now triggers an
  acknowledged shell replacement instead of waiting indefinitely for detachment.
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

## Loading and title refresh

- Prepare core menus, World Builder widgets and title/pause button contents
  during engine startup loading. Fresh authored title-widget proof allows the
  Mods button to attach before the title menu fades in.
- Warm the read worker before it is needed, batch World Builder construction
  and menu visibility updates, and preserve current-world ownership checks.
- Defer read-only loading/GC proof races without failing untouched mods or
  rebuilding already-owned trees. Keep uncertain native cleanup owners held.
- Includes Continent Flight 0.4.3, Map Travel 0.2.4 and World Builder
  0.32.5-experimental. The custom-map loading update uses native runtime213
  and WorldBuilder Map Loader 0.2.4.

## Custom-map loading readiness

- Assigned maps are decoded and validated into immutable spawn plans during
  loading preparation. Referenced `/Game/` and `/Engine/` static-mesh assets
  are prepared under process-owned leases before destination spawning; these
  preparations do not retain a gameplay world or spawn into a departing world.
- Original petal/gold artwork with ornate ClairObscureSDK lettering is bundled
  in WorldBuilderMapLoader.sdkmod under assets/map-loading.png. The mod supplies
  its own image to the SDK overlay; the SDK includes a matching fallback.
  The texture and opaque fallback are prepared before save loading. The native gate
  observes the game's load and map-change flags and displays that prepared
  cover before destination possession. It does not activate a menu, change
  focus or borrow the destination pause menu. Travel detachments are checked
  against actual viewport membership.
- The movement guard now remains held beyond spawn acknowledgments. Reveal
  requires all owned actors to be live and visible, five nearby floor-support
  traces to succeed, SDK-owned supporting geometry to have a recent render observation,
  settled level streaming, and matching current world, pawn and save generation.
  Mandatory map restoration finishes before player control is released.
- A 15-second readiness deadline and independent 60-second native recovery
  deadline bound failed preparation or a lost controller. These are recovery
  limits, not fixed waits used to declare success. Cleanup revokes only the
  current owner's presentation and movement state; stale callbacks cannot
  acknowledge a newer world visit.
- `startuptiming` retains preparation, asset, spawn, collision, visual-readiness
  and player-release measurements. Detailed timings remain hidden during
  ordinary startup.

Recent-render observations are not GPU fences or a guarantee that every texture
mip is resident. A supporting floor outside the camera frustum can fail the
recent-render check even when spawning has completed. Missing or invalid maps
and readiness failures recover presentation/control with a diagnostic; a save
whose floor is absent may still leave the player unsupported. A cancellation back to the same non-title world and pawn may wait for the native
60-second recovery deadline when no positive cancel signal exists.

## Validation and measured limits

- Native runtime213 and its fixtures compile with MSVC /W4 /WX. The SDK suite
  passes 2,160 tests with 8 skips; 140 integrated World Builder tests pass, as do 78 tests in the separate project.
- Final cold loading prepared 129 assets during game loading in 4.94 seconds.
  Restoring 1,798 custom props, validating support and revealing the world took
  1.416 seconds beneath the cover; the final travel return took 1.485 seconds.
  Post-load asset preflight was below 0.5 ms. Placement still needs the admitted
  destination world; these measurements do not claim zero destination work.
- Live checks covered custom and normal saves, floor movement, same-session
  title/reload, travel away/back, menu availability and invalid-map recovery.
  The final native213 run verified the texture during travel and all seven mods
  ready afterward. Readiness uses five local support traces and settled streaming;
  recent-render evidence is required for SDK-owned support, not invisible vanilla
  collision proxies.

The following measurements describe the earlier runtime210 release baseline,
not the final custom-map loading update:

- 2,060 SDK tests passed (8 skips); 140 World Builder tests passed.
- Native runtime210 and its fixtures were previously compiled with MSVC /W4 /WX.
- Live cold launch showed Mods alongside the authored title buttons during
  fade-in. A prepared title Mods opening measured 167 ms.
- In the final cold run, the core menu prepared in 6.25 seconds, World Builder
  in 3.40 seconds and Flight in 0.68 seconds, before save selection. Flight
  activated from its loading snapshot in 44 ms. All seven enabled gameplay
  mods restored successfully, with normal Flight toggle/restore and stable
  keybind scrolling.
- Title/save handoff retains the reusable shell; same-session title return
  reattaches the title button. World ownership and cleanup acknowledgments
  remain required before reuse.
- Remaining limits: final restoration took 0.65 seconds after owner-thread
  exploration readiness, excluding earlier UI handoff and pause attachment.
  First-visible-gameplay zero-delay readiness and an 80 ms immediate-pause
  bound are not established. Switching between Mods and Map Travel still
  repaints the shared panel and measured about 0.69 seconds. The 200 ms goal
  is met by the measured prepared Mods open, not every view change.
- Active cinematic presentations/media, Scene visual-arena restitution and
  encounter tuning retain unsupported retirement owners rather than restoring
  old-world state. Ordinary inactive browser/editor cleanup is supported.

## Optional map loader upgrade

Use `WorldBuilderMapLoader.sdkmod`. It replaces the legacy
`E33MapOverlays.sdkmod`; do not install both. With the game and SDK closed,
remove the old `SDK_Mods/E33MapOverlays.sdkmod` and its generated
`SDK/mods/E33MapOverlays` cache before installing the replacement. Keep user
settings and saved maps. The replacement includes its prepared-map store and
context observer.

## Release inventory

The SDK archive contains runtime213, its matching native controller, the bundled
Python runtime, public SDK Python sources, licensing notices and core mods.
Optional mods, World Builder, Scene Editor, Enemy Spawner and Asset Converter
are separate downloads. The source archive includes `gpu/` dependencies and the
public build scripts. Build runtime213 with
`scripts/build-rc18-native.cmd` (including the thumbnail worker), prepare the
pinned runtime and bootstrap with their existing scripts, then package a new destination with
`scripts/package_rc18.py` after committing the reviewed public source inputs.

The packager recursively audits nested `.sdkmod` and ZIP archives, rejects local
state and saved maps, and writes SHA-256 checksums for the final artifacts.
