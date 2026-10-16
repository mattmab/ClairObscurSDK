# Nexus release upload kit

Status: finalized for manual Nexus upload; not uploaded to Nexus or published there.
Use the ZIPs and checksums in `dist/nexus-rc12-final`, not the earlier test kit.

## Files to upload

| Listing | Main file | Version | File description |
| --- | --- | --- | --- |
| Clair Obscur: Expedition 33 SDK | sdk/Expedition33-SDK-0.1.0-rc12.zip | 0.1.0-rc12 | SDK RC12: faster menu construction and corrected World Builder surface targeting. Includes bundled Python and three core SDK mods. |
| E33 World Builder - Experimental | world-builder/E33WorldBuilder-0.30.1.zip | 0.30.1 | Standalone World Builder with closed-reader recovery for F7/F8. Requires SDK 0.1.0-rc12 or newer. |

Use the descriptions below for the two listings. Add the SDK listing as a required
Nexus dependency on World Builder. Do not upload staging folders or artifact JSON
as mod files. checksums.sha256 accompanies the two ZIPs. No media is included.
Both packages target the verified Windows Steam game build; manual installation
is the documented method. License: MIT for project code; SDK includes Python
third-party notices. No game assets are redistributed.

## SDK listing description

Clair Obscur: Expedition 33 SDK provides a shared native runtime and Python mod
controller. Launch the game normally, load a save, and manage mods from Pause >
Mods. Bundled Python means no separate Python installation is needed.

The Mods menu includes enable/disable switches, search and filters, text sizing,
separate scrolling settings and keybind panels, and press-a-key rebinding with
conflict reporting. SDK Management, Introspection Harness and LiveObjectViewer
are included. World Builder and other gameplay mods are separate downloads.

RC12 packages faster batched menu construction and prepares the menu before
optional mods. It also corrects World Builder foreground selection and stale GPU
hits. Startup still waits for gameplay and pause-menu readiness; it is not instant.

INSTALL: Close the game and SDK, then extract the SDK ZIP into the game folder
containing Sandfall. SDK and SDK_Mods must sit beside Sandfall. If
Sandfall/Binaries/Win64/version.dll already belongs to another loader, resolve
that conflict before installing. Start the game and load a save. Preserve
SDK/settings when updating. Run SDK/launch-sdk.cmd --check for an integrity check.

COMPATIBILITY: Windows Steam executable SHA-256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
Other builds are rejected by the runtime fingerprint check. This is a release
candidate; not every optional mod operation or game transition has been tested.

## World Builder listing description

Explore with a free camera, select ordinary world props, move them, browse the
game's asset catalog, spawn props, and save builder scenes. World Builder is an
optional mod using the Expedition 33 SDK's shared runtime.

Features include asset search, favorites, previews and cached thumbnails; prop
placement and duplication; undo/redo; galleries; saved maps; and camera settings.

REQUIRED: Install Expedition 33 SDK 0.1.0-rc12 or newer first. Updating only this
mod will not install the SDK's native targeting fixes.

INSTALL: Close the game and SDK. Extract this ZIP into the game folder beside
Sandfall so SDK_Mods/E33WorldBuilder.sdkmod is installed. Leave the .sdkmod intact.
Start the game, load a save, and enable World Builder in Pause > Mods. Existing
maps and preferences stay in SDK/settings/E33WorldBuilder.

CONTROLS: F8 enters/leaves free camera; F7 toggles the asset catalog. WASD flies,
Space/Ctrl moves vertically, and Shift speeds up movement. Hold left mouse to
grab a supported prop and release to place it. F10 duplicates a selected spawned
prop. Alt+Z/Alt+Y undo/redo. F9 restores edits. Rebind through Pause > Mods >
Keybinds. The included README explains the additional controls and catalog tools.

SAVE YOUR SCENE: F8 leaves placed props in the loaded session. Disabling the mod,
F9, and SDK shutdown restore world edits and remove spawned props. Save a builder
map before exiting. Builder maps are separate from game saves.

WHAT'S NEW IN 0.30.1: Closed read workers recover on the next operation without
replaying failed widget mutations or clearing scene edits. Status polling resumes
after recovery. With SDK RC12, scene-depth targeting rejects obscured/stale hits
and considers props beyond the previous 32-candidate limit.

EXPERIMENTAL LIMITS: Landscape and individual foliage/instanced components are
unsupported. Transparent surfaces that do not write depth may not be selectable.
Dense overlap can add targeting delay, and some catalog assets cannot load in
all worlds. Load maps in their original level and streamed area; transform/path
errors during restoration are a known remaining issue. Static lighting may stay
at its original baked location. Use in a quiet, unmounted exploration area.

## Changelog fields

SDK 0.1.0-rc12: Package post-RC11 startup improvements; batch menu construction;
prepare menus before optional mods; correct World Builder depth occlusion,
candidate truncation, stale hits and capture ownership.

World Builder 0.30.1: Recover closed persistent readers at the next operation;
resume polling; preserve edits; do not replay failed widget operations. Requires
RC12 for updated native targeting.

## Validation scope

Release runtime/probe/thumbnail builds and the native targeting regression passed.
SDK and World Builder regression results are recorded in VALIDATION.txt.
Archive CRC, manifest integrity and SDK runtime/license hashes were checked.
The final RC12 and World Builder 0.30.1 ZIPs passed a clean-install live run on
2026-10-15: Pause > Mods, text sizing/reset, Keybinds and rebinding, foreground/rear
cube targeting and drag, F7/F8, and subsequent console execution. Widget
construction took 2.27 seconds; readiness took 9.29 seconds from the gameplay
gate. Unavailable temporary assets logged skipped-thumbnail errors. Streamed map
restoration remains a separate known limitation. See RELEASE_0.1.0_RC12.md.
