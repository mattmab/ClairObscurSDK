# ClairObscurSDK v0.1.0-rc19

This prerelease packages the current cinematics and Scene Editor work with native runtime 245.

## Downloads and installation

Use **Expedition33-SDK-0.1.0-rc19.zip** for the complete SDK and 13 public mod packages. Close the game and SDK controller, then extract into the Expedition 33 game directory beside `Sandfall`. Keep your existing settings and user maps. Enable the desired mods in Mods at the title screen or from Pause.

The optional-mod bundle and individual mod downloads contain the same packages as the complete SDK download. They require RC19. The source bundle includes the development sources and a separate snapshot of the qualified runtime Python sources and mod packages used by this release.

## Included work

- Game-authored sequences integrated into the existing Scene Editor library and timeline, with cast controls, Blueprint NPC tracks and saved authored edits.
- Flight view and whole-scene placement. Numpad 8/2 moves forward/back, 6/4 moves right/left, and 9/3 moves up/down. Hold Alt for fine movement. Backspace hides or restores the timeline. Save keeps authored placement.
- Timeline drag seeking, playback controls, camera restoration and cleanup improvements.
- Larger bounded MovieScene cast observations: cooked scenes with more than 256 declarations can expose their complete supported cast. Null templates remain visible as unavailable declarations, without blocking the other cast controls.
- Numbered asset-name loading, including EvequeIntro's numbered sequence asset, and media-source parsing fixes.
- The current public cinematic, encounter, lifecycle and menu foundations are included in the source snapshot.

## Validation

- Python suite: 2,977 tests passed, six skipped.
- Native runtime/probe 245 compiled; bounded cast-array and numbered-name fixtures passed.
- In-engine EvequeIntro qualification exercised playback, a cast override, a Blueprint NPC, flight placement, hide/show, drag seeking and cleanup on the preceding numbered-name candidate.
- In-engine runtime 245 qualification imported MeetingRealRenoir's 3,288-node graph and exposed 536 cast bindings. Its edited preview played with one override owner and one Blueprint NPC owner. Flight placement retained both owners; fine Z movement, timeline hide/show, drag seeking and return to exploration were checked.

## Experimental limits

The 155-entry catalog is not a promise that every scene is fully playable. ScavengerIntro, MeetingThePaintress and TheEndOfOsquio still need reader/import work; default-active credits movies also need additional playback support. Large sources can still take seconds to import and prepare: the measured Renoir import was about 16 seconds.

Actor overrides and Blueprint NPC controls are experimental. An owned override or matching skeleton does not establish correct final body/facial animation in every shot. Cross-scene character compatibility, nested bindings, animation evaluation and mixed movie/sequence timelines still need work. This RC does not claim complete replacement correctness for every listed scene.

No user saves, settings, generated caches, local research captures or personal mods are included.

