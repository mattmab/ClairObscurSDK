# SDK 0.1.0-rc17 — Scene Editor and original encounters

RC17 adds the Scene Editor and Enemy Spawner packages and updates the combined
native runtime to v202. Install the matching SDK ZIP before the optional mods.
Existing user settings and saved maps are preserved and are absent from these
downloads.

## Changes

- Enemy Spawner preserves the 683-entry catalog and 193 original-world recipes,
  and adds separately identified direct original-fight routes. Direct fights use
  their captured original arena components and authored battle parameters.
- Live user tests passed for main Duelliste, the paired Duolliste encounter,
  Mirror Renoir, Chalier and Sciel tutorials, Osquio, enemy Monoco, Scavenger,
  both normal Simon combat stages, and all three main Paintress phases with
  cutscenes. These are representative controlled tests, not a claim that every
  catalog entry was individually fought.
- World-map reload cleanup now retires the SDK's collector storage after the
  engine purges its original actors. Osquio defeat, another encounter in the
  same SDK session, and another defeat/reload all passed without restarting.
  Transient read failures retry observations without repeating battle entry.
- Intro Paintress is identified as an invisible, invincible story target that
  relies on the original Monolith world scene. Standalone fight start is disabled.
- Scene Editor preserves ordered character IDs, all 2,689 animation clips, saved
  scene compatibility, and the Noco/Golgra hair assemblies. It remains separate
  from World Builder. The optional bundle includes both editors.
- Portable startup and packaging select the v202 runtime. Encounter details show
  their own labels and limitations instead of a shared Duelliste description.

## Experimental encounter limits

Direct fights do not create an exploration character or walk-up interaction.
They use authored level, health and difficulty. The surrounding campaign intro
and reward action chain is omitted; original tutorial callbacks can still change
party/completion state and autosave. Use the in-game labels before starting one.

Normal Simon's two original battles are separate selectors in this RC. Automatic
intro/transition/outro orchestration is not implemented. Main Paintress retains
its original phase-arena references; the user completed all three phases and
cutscenes, but arbitrary-map cinematic relocation is not claimed. Paired Duolliste
can have obstructed camera views in foliage; its phase transition worked in the
controlled test. Open ground is preferable for direct fights.

## Validation

- 1,399 source tests passed, with 8 existing skips.
- 467 focused encounter regression tests passed.
- 86 reconciled Scene Editor tests passed.
- 9 targeted world-reload lifecycle tests passed.
- The v202 native DLL/probe rebuilt with warnings treated as errors; native
  ownership, collector retirement, arena and other build fixtures passed.

See the downloadable validation receipt for package integrity and portable
startup checks. Archives use explicit public inputs, including recursive scans
of nested mod archives; no personal configuration, saved maps or private mods
are distributed.
