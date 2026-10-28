# ClairObscurSDK v0.1.0-rc21

Experimental prerelease with native runtime 246. Use RC21 instead of RC20 for cinematic cast replacements and mixed movie/3D timelines.

This update makes the packaged Scene Editor and SDK runtime use the same source snapshot. RC20 could fail cast replacement with an unexpected latency argument and omitted the matching movie boundary implementation. The release packager now rejects missing SDK dependencies, stale runtime sources and mismatched public mod contents before creating downloads.

Nested sequence editing accepts verified shallow and deep Unreal copies. MyFlower P1's movie timing no longer depends on unsupported clock parameters in its separate 3D shot. Direct subsection signature reads are batched while preserving fresh correspondence checks and source ownership validation.

## Installation

Close the game and SDK controller, then extract Expedition33-SDK-0.1.0-rc21.zip beside Sandfall. Preserve settings and user maps. Individual mod and optional-mod downloads require RC21 and match the full download.

## Controls

Use the existing Scene Editor library and timeline for game-authored sequences. Drag tracks to seek. Backspace hides or restores the timeline. Flight view supports whole-scene placement with numpad 8/2, 6/4 and 9/3; Alt gives fine movement. Save keeps authored placement.

## Validation

Python suite: 3,017 tests passed, six skipped. Tests include package/source drift rejection, deep-copy provenance, nested movie timing and existing lifecycle checks. Earlier in-engine checks exercised MyFlower and Osquio movie playback, scrubbing, replacement actors, Blueprint NPCs, flight placement and cleanup while verifying original references unchanged. The corrected coherent frozen package passed a cold launch, title menu and save load, followed by MyFlower playback, movie-to-3D drag seeking, one replacement, one active Blueprint NPC, fine flight placement, timeline hide/show and cleanup without live code patches. All 75 original MyFlower subsection references and signatures remained unchanged. Qualification used an isolated game-root installation with the same SDK and mod file contents.

## Experimental limits

The 155-entry catalog is not exhaustive playback qualification. Large scenes still take seconds to import and prepare. Retarget appearance and body/facial animation quality need further scene-specific review. Repeated movie occurrences, multiple movies, speed changes and some camera-animation-owned edits remain unsupported. Original map geometry is not imported with a sequence.

No user saves, settings, generated caches, private research captures or personal mods are included.
