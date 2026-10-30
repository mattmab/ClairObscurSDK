# Encounter and cinematic completion audit — 2026-10-24

## Scope and evidence

This is a source and existing-evidence audit in the isolated capability-expansion
checkout. No encounter was started, game object changed, save loaded or modified,
SDK installed, or release produced. Historical live results below are historical
acceptance, not a new live test. Local raw logs, captures, settings, maps and private
content are not included in this report.

The implementation boundary is `mods/EnemySpawner`,
`src/expedition33/_original_trigger_fight.py`, `_original_trigger_sequences.py`,
`original_encounter_roster.py`, `original_helper_encounters.py`, and
`src/expedition33/cinematics`. The public RC17 acceptance record is
`docs/RELEASE_0.1.0_RC17.md`. Historical research was read from the existing local
`SDK-capability-review` directory without changing or copying its raw artifacts.

## The previously failed cutscene is identified

The exact historical failure was the **paired Duolliste encounter's phase
cutscene**, following the two-member CleasTower original battle. It was not
normal Simon's separately unimplemented cinematic handoff, and it was not main
Paintress, for which the user later reported all three phases and cutscenes.

The local historical `CONTROLLED_ENCOUNTER_RUN_2026-10-22.md`, section
“Pair user result and presentation failures,” records all of the following
together: original phase 2 transition succeeded; the player lost and returned to
exploration; the phase cutscene was not visible; foreground foliage obstructed
the combat camera. Thus the evidence establishes a presentation failure, not a
failure to progress to phase 2. It does not prove whether a sequence failed to
play, played behind occluders, or used an unsuitable original camera frame.

The exact original source retained by the profile is
`/Game/Levels/CleasTower/GameActions/DA_GA_SQT_DuallisteAlpha.DA_GA_SQT_DuallisteAlpha:BP_GameAction_TriggerBattle_C_1`.
The captured complete initial roster contains Duolliste A and B. Existing source
research identifies the original phase summon row `Duolliste_P2`; this is not a
reason to substitute the distinct main Duelliste or Clea Flying House encounters.

The separately investigated main Duelliste finisher
`/Game/Cinematics/ForgottenBattlefield/Finisher/CS_Finisher_Duallist.CS_Finisher_Duallist`
must not be presented as a proven repair for the pair. The SDK's positive
attribution/cleanup component explicitly admits only the exact main Duelliste
source, requiring reciprocal owned Epic-helper links. Baseline/delta observation
alone never authorizes destroying a game-created sequence actor.

## Actual completion matrix

| Route or feature | Proven available | Remaining boundary |
| --- | --- | --- |
| Main Duelliste | Original direct combat and return historically passed | Original exploration assembly and arbitrary-map cinematic relocation are not established; sequence cleanup has a narrow positive-ownership contract |
| Paired Duolliste | Exact A/B direct battle, phase 2, loss return | Camera/foliage visibility and original phase cinematic presentation; original exploration interaction assembly |
| Monolith Mirror Renoir | Original direct fight and return historically passed | Original outer intro/exploration presentation; distinct from unresolved world Mirror Blueprint and from Curator/Renoir |
| Chalier and Sciel tutorials | Original direct tutorials historically completed | Original callbacks can change party, completion and autosave; campaign-neutral execution is not proved |
| Osquio | Original direct combat; defeat/reload and same-session reuse historically passed | Original exploration cinematic Pawn assembly and arbitrary-map sequence relocation |
| Monoco and Scavenger | Original direct combat and return historically passed | Complete original world interaction/outer action presentation |
| Normal Simon stages 1 and 2 | Both original battles independently selectable and historically passed | Original intro, automatic inter-battle cinematic handoff, outro and complete exploration interaction |
| Main Paintress | Three phases and cutscenes historically passed | Arbitrary-map relocation of original phase arenas/cameras is not proved |
| Intro Paintress | Identified original invisible, invincible story target | Standalone fight deliberately disabled; requires original Monolith world presentation and campaign progression |
| Visages helper assembly | Exact qualified original assembly/arena and approach route | Does not establish every other boss assembly merely because they share base classes |
| Cinematic replay services | Exact-profile title/media adapters and mapped original game-action replay exist | Per-scene live acceptance, actor bindings, camera/input/audio restoration, and world readiness remain explicit requirements |

The 12 captured direct profiles are **not 12 complete original encounter
presentations**. Direct fights intentionally omit exploration characters and
outer campaign action chains. The catalog retains 683 entries and 193 original
world recipes; their presence is not evidence of individual combat acceptance.
An “approximately 95% complete” single number hides these different contracts.
Most requested special combats are available; full original presentation has
specific remaining assembly, binding and orchestration work.

## Safely completed source changes

EnemySpawner details contained stale statements contradicting the newer RC17
acceptance record. They now:

- Describe normal Simon's two separate original direct selectors and explicitly
  retain the missing automatic cinematic handoff/intro/outro limitation.
- Describe the historically tested Monolith Mirror direct battle without claiming
  that its world Blueprint or complete exploration presentation is qualified.
- Put the paired Duolliste cutscene/foliage limitation directly on that encounter's
  details page, including the fact that ground and party clearance do not prove
  camera visibility.

No admission gate, runtime capability, original action, camera, sequence ownership
rule or immutable source profile was relaxed to make these statements true.
The SHA-pinned `_original_trigger_recipes.json` is still an exact captured source
package. Several historical `admission` fields there predate later user tests and
remain false; these capture fields must not be mistaken for a current consolidated
acceptance receipt. Updating acceptance should use a separate versioned evidence
record rather than silently rewriting or weakening that source capture.

## Shortest defensible remaining work

1. **Pair presentation:** observe the original phase sequence at its exact original
   arena; identify its complete player/actor/camera binding graph and completion
   callbacks. Distinguish occlusion from missing playback with before/during/after
   evidence. Current party-footprint ground tests cannot answer that question.
   Any portable camera/arena solution must retain the original sequence and prove
   bindings, streaming, collision and camera restoration; open ground is a useful
   workaround, not a completed repair.
2. **Pair exploration entry:** historical `HUMAN_REVIEW.md` around lines 337–345
   identifies the CleasTower canvas dialogue and an exact streamed-cell frame
   actor. The relevant dialogue imports `DA_GA_SQT_DuallisteAlpha`, but co-imports
   do not prove per-instance dialogue assignment. Prove that assignment, inherited
   component assembly, visibility conditions and teardown before staging. The
   action also has a persistent completion-flag path; do not execute its outer
   chain just to obtain a preview.
3. **Simon full route:** preserve the two exact TriggerBattle children of
   `DA_GA_SQT_BossSimon` and decode the original ordering, cinematic completion and
   finish/abort behavior. Connecting the two existing selectors by a timer or
   replaying a visually similar movie is not the original handoff. This requires
   a fresh-world context and complete original sequence contract before dispatch.
4. **Shared lifecycle:** retain current one-shot dispatch, exact world identities,
   complete initial rosters and explicit deferred cleanup. World path equality is
   insufficient across reloads. Never adopt actors in a replacement world to
   satisfy an old world's teardown, and never retry an unknown battle dispatch.
5. **Acceptance:** test each completed presentation in a disposable context only
   after source/native ownership is proved. This audit did not authorize live
   persistent callbacks or install experimental builds.

## Validation

91 focused tests pass across `test_original_direct_menu.py`,
`test_original_game_action.py`, `test_alpha_menu.py`, `test_cinematics.py`,
`test_title_replay.py`, `test_sequence_pending.py`, and
`test_replay_presentation.py`. The regression exercises actual EnemySpawner views
with the exact catalog and direct recipe map, checks stage availability and the
missing-handoff warning, and retains world-spawn classification.

The test process used the existing bundled Python and a dedicated writable
`build/encounter-temp` directory because the sandbox's default temporary directory
denied fixture writes. Expected error-path logging remained enabled. No live
visual or runtime acceptance is claimed by these source tests.
