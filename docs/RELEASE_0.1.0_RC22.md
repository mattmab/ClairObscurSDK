# ClairObscurSDK v0.1.0-rc22

Experimental prerelease with native runtime 246. Includes the current SDK, Scene Editor, Cinematics, encounter tools and public mods in one coherent package.

## Changes since RC21

Private cinematic curve validation now batches fresh signature observations and reads each source/private channel pair together. Identity, ownership, full-channel comparison and native write/readback checks remain enforced. Missing batch targets and changed private signatures reject the edit before a native write.

Timeline preparation skips empty key and section edit passes while retaining generated movie suppression edits and activity suppression. Title menu installation can retry after an early rejected target without submitting an empty identity batch.

The existing Scene Editor includes game-sequence browsing, cast replacements, Blueprint NPC tracks, drag scrubbing, timeline hide/show, flight view and whole-scene placement. This release carries those features forward with the preparation fixes above.

## Installation and controls

Close the game and SDK controller, then extract Expedition33-SDK-0.1.0-rc22.zip beside Sandfall. Preserve settings and user maps. Individual mod and optional-mod downloads require RC22 and match the full download.

Drag timeline tracks to seek. Backspace hides or restores the timeline. In flight view, numpad 8/2, 6/4 and 9/3 move the whole scene; Alt gives fine movement. Save keeps authored placement.

## Validation

Python suite: 3,024 tests passed, six skipped. The frozen package passed a cold launch and save load, then MyFlower P1 playback, drag seeking, one replacement actor, one active Blueprint NPC, timeline visibility, fine whole-scene flight placement and preview cleanup without live implementation patches. Fresh reads confirmed all 75 original MyFlower subsection signatures and sequence references unchanged.

In one comparable MyFlower run, curve-edit preparation decreased from 3,858 ms to 1,224 ms and total preview preparation from 18,457 ms to 16,099 ms. Import took 7,259 ms. These are individual live measurements, not a guarantee for every scene or machine. Earlier qualified checks also covered ending movies and keyless movie activity suppression.

## Experimental limits

The 155-entry catalog is not exhaustive playback qualification. Large scenes still take seconds to import and prepare. Retarget appearance and body/facial animation quality need further scene-specific review. Repeated movie occurrences, multiple movies, speed changes and some camera-animation-owned edits remain unsupported. Original map geometry is not imported with a sequence.

No user saves, settings, generated caches, private research captures or personal mods are included.
