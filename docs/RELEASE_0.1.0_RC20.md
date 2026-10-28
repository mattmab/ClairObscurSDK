# ClairObscurSDK v0.1.0-rc20

This experimental prerelease includes the RC19 Scene Editor, flight placement and public mods, plus native runtime 246 and nested cinematic editing fixes.

## Installation

Close the game and SDK controller, then extract **Expedition33-SDK-0.1.0-rc20.zip** beside Sandfall in the game directory. Preserve existing settings and user maps. Individual mod packages and the optional bundle require RC20 and match the complete download.

## Changes

- Copy edited nested sequences into a private hierarchy before changing their sections, preserving original game assets.
- Support proven single-occurrence nested movie timing, including TheEndOfOsquio, and default-active ending credits movies. Edited movie ranges control the visible playback window.
- Expand bounded reference traversal for larger cooked scenes and aggregate track diagnostics to 4,096 tracks; per-array bounds remain enforced.
- Retain Scene Editor timeline playback, drag seeking, hide/show, cast replacements, Blueprint NPC controls and whole-scene flight placement. Backspace toggles the timeline; Numpad 8/2, 6/4 and 9/3 move the scene; Alt gives fine movement.

## Validation

The release is based on runtime 246 in-engine checks of Osquio, ScavengerIntro, MeetingThePaintress, BreakingTheBarrier, AliciaBirthP3PreRender, rolling credits and both ending credits movies. Checks covered nested movie boundaries, playback, edited credits ranges and cleanup. Osquio also exercised a Sciel replacement, a Blueprint NPC, body/facial pose observations, flight placement, timeline hide/show and drag seeking. Original source references and credits activity were checked unchanged. These are individual checks, not exhaustive coverage of the catalog.

Python suite: 3,007 tests passed, six skipped. Runtime 246 and its probe compiled with warnings treated as errors; bounded occurrence fixtures passed. Archive validation results accompany the downloads. The final packaged ZIP has integrity checks; a separate cold-launch qualification of this exact final archive has not been completed.

## Remaining limitations

Not every one of the 155 catalog entries has been playback-tested. Large scenes still take seconds to import and prepare. Repeated movie occurrences, multiple movies, non-unit playback speed and some camera-animation-owned edits remain unsupported. Body/facial retarget quality needs further visual review; correct bindings do not guarantee identical animation. Original-map environment geometry is not imported with scenes.

No personal mods, user settings, saves, generated caches or private research captures are included.
