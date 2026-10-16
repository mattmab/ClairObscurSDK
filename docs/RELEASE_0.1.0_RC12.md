# SDK 0.1.0-rc12 and World Builder 0.30.1

Prepared for release on 2026-10-15. These are two separate downloads; World
Builder remains experimental and requires SDK RC12 for the native targeting fixes.

## SDK changes

- Packages the post-RC11 startup improvements: bounded widget construction,
  gameplay/pause readiness gating, and menu preparation before optional mods.
- Retains text sizing (0.75–2.75, Reset 1.35), independent settings/keybind
  scrolling, enable toggles, and press-a-key rebinding with conflict reporting.
- World Builder targeting checks full-scene depth before individual props,
  considers candidates beyond the previous 32-bound limit, and rejects stale
  hits after camera movement. Capture/readback ownership stays paired.
- Bundles only SDK Management, Introspection Harness and LiveObjectViewer.

Prior live startup measurements were 2.17 seconds for widget construction versus
10.60, and 9.06 seconds for SDK readiness versus 17.42. The readiness gate changed;
these are individual observations, not a performance guarantee. See
[the recorded startup checks](STARTUP_MENU_VALIDATION.md).

## World Builder changes

- A closed read worker is retired and replaced on the next operation.
- Failed widget operations are not replayed. Healthy recovery resumes status
  polling without clearing scene edits or unloading the mod.
- F7 opens/closes the catalog; F8 enters/leaves the builder camera. Both were
  checked in game after recovery, with all 28 existing tracked edits retained.
- Keeps catalog, camera settings, maps, thumbnails, placement, and undo/redo in
  the standalone mod. The SDK owns shared native services.

## Installation and upgrade

Close the game and SDK before installing. Extract `Expedition33-SDK-0.1.0-rc12.zip`
into the game folder beside `Sandfall`. Extract `E33WorldBuilder-0.30.1.zip` there
as well, leaving `SDK_Mods/E33WorldBuilder.sdkmod` intact. Start normally, load a
save, then enable World Builder in Pause > Mods. No separate Python is required.
Preserve `SDK/settings`, including World Builder maps, camera preferences and cache.
Resolve an existing unidentified `Sandfall/Binaries/Win64/version.dll` before
installing this loader. See [installation details](INSTALLABLE_RELEASE.md).

Save a builder map before disabling World Builder or exiting the SDK: cleanup
restores world edits and removes spawned props. Saved builder maps are not game
save files. F9 restores edits; F8 only leaves the camera.

## Compatibility and known limits

Targets the verified Windows Steam executable SHA-256
`218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618`.
Other executable builds fail the native fingerprint check.

Landscape and individual foliage/instanced models remain unsupported. Dense
candidate overlap can add targeting delay; transparent surfaces without scene
depth may not be selectable. Some registry assets cannot load in every world.
Load saved maps in their original level with the relevant area streamed in.
A recent restore needed retries after transform/path errors; this release does
not claim to resolve that separate map-loading problem.

The final RC12 and World Builder 0.30.1 archives were tested in game on a clean
SDK install on 2026-10-15, without inherited settings or optional mods. Checks
passed for Pause > Mods (AutoHotkey held Escape), enabling World Builder,
Keybinds, press-a-key rebinding, text sizing/reset, F7 catalog open/close, F8
camera off/on, front/rear cube targeting, drag and console execution afterward.
Construction took 2.27 seconds; SDK readiness took 9.29 seconds from the gameplay
readiness gate in this run. These timings are observations, not guarantees.
Unavailable temporary catalog assets produced skipped-thumbnail errors without
tearing down the SDK. Reader fault recovery was covered by the earlier live run;
this clean run did not inject a reader failure or retest every asset or panel.
See [targeting validation](WORLD_BUILDER_TARGETING_VALIDATION.md).

## Build and package

From an x64 Visual Studio tools prompt:

```bat
scripts\build-release-runtime.cmd
runtime\python.exe scripts\run_regressions.py
runtime\python.exe scripts\package_release_candidate.py dist\nexus-rc12\sdk --version 0.1.0-rc12
runtime\python.exe scripts\package_world_builder.py dist\nexus-rc12\world-builder
```

Each output includes `artifact.json` with its SHA-256. The packaging scripts
select release files and exclude personal settings, maps, caches and game assets.
