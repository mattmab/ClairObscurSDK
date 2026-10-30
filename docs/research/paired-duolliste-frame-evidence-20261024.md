# Paired Duolliste presentation implementation evidence

This focused continuation concerns the exact pair, not the main Duelliste
finisher. It adds read-only diagnostics and an exact original-world frame guard;
it does not claim live visual acceptance or a portable cinematic repair.

## Concrete original graph

The source phase graph invokes
`/Game/Cinematics/ForgottenBattlefield/DuallistePhase2/CS_FB_DuollistePhase2.CS_FB_DuollistePhase2`
with ID `DuollistPhase2`. Main Duelliste instead uses
`CS_FB_DuallistePhase2` and ID `DuallistPhase2`: the spelling difference is
semantically significant. The pair's original latent completion resumes at
virtual offset 492, restores battle UI/input/visibility and summons the authored
`DuollistPhase2Summon` into slot 2. No standalone P2 spawn is introduced here.

The complete outer `DA_GA_SQT_DuallisteAlpha` graph was also decoded. Its
Sequential class joins by exact public export hash `10094890037900881323`.
Its entire 28-byte root payload contains exactly two inline wrappers, in order:
`BP_GameAction_TriggerBattle_C_1`, then
`BP_GameAction_WritePersistentFlag_C_0`. There is no separate outer phase
cinematic action. The second action's authored `NamedID` points to
`NID_BeatDuallisteAlpha` (public hash `12510772144510802246`); its omitted `Value`
inherits **true**, established from the exact WritePersistentFlag class CDO.
The captured root package SHA256 is
`9d9371a5c49d5d71b8e4b8195af6cd7622a73f468ca3d1c260566ad15e78fa7d`.

## New exact-package findings

A single exact cached package-index selection was extracted with retoc into the
isolated worktree's ignored `build/paired-presentation/offline` directory. No live
asset load, game invocation, container enumeration or installation occurred.
The original sequence has 569 exports, 12 spawnables and 26 possessables. Its
spawnable prefix and binding records were decoded using the existing bounded
offline Reader from the Simon source investigation.

The sequence owns four camera templates, the exact paired A/B/P2 battle-class
templates, lights, effects and a `Sphere_Attach` template. All 12 authored
spawnable transforms are identity. Eleven attachment sections include the exact
Sphere binding GUID `(2513776276,1290965607,1938845825,274934800)`. All four
camera cuts resolve to the corresponding camera spawnable GUIDs.

The Sphere transform track (149, section 137) has constant channel defaults:
translation `(-47913,-5718,-18084)`, yaw `72`, unit scale. Its camera/combatant
attachment-track coordinates are authored around `(5500..7000,-11000..-12500,
-9000..-10100)` in the attached frame. Those transforms map into the original
CleasTower arena vicinity rather than an arbitrary current-pawn location. The
exact pinned arena root is `(-35030.83759038431,-3713.4009074234305,-28225.771533)`,
yaw `-50.23245300000002`.

The bounded channel parser checked all nine contiguous channel storage records
for each of 12 transform sections: 4-byte frame times, 32-byte keyed values,
matching counts, finite numeric values, default flags, and 24000/1 tick rate.
The later 42-byte section tails were preserved rather than assigned guessed
semantics. Attachment rule bytes were not promoted to named enum semantics
without a native schema. These are serialized source findings, not evaluated
world-transform or visibility observations.

The original CinematicSystem `StartLevelSequence` path creates the sequence
player and plays the authored asset. The inspected body establishes no
transform-origin override that follows the SDK's relocated battle arena. The
original phase continuing therefore does not prove the cutscene was visible at
that relocated site. Foliage-free placement cannot establish that fact either.

## Implemented interfaces

`pair_source.observe_graph(catalog, root)` reads and validates the complete
two-action array plus `NamedID`/`Value` on its persistent tail. `validate_graph`
rejects missing/truncated/ambiguous/reordered wrappers, stale identities,
foreign classes and alternate source objects. `validate_tail` requires the
exact original NamedID and strict true value. `validate_original_context`
checks the active CleasTower world identity, exact original arena source path,
class and outer chain, exact soft arena reference and original frame. These
helpers do not dispatch or grant campaign neutrality: running the original
outer graph really writes its original completion flag.

`_paired_phase_frame.original_pose(world_path)` returns the existing native arena
12-number pose only in the exact original CleasTower world.
`require_original_frame(world_path, pose)` rejects another world, translation,
orientation, reserved values, scale, nonfinite coordinates or boolean numbers.
The constants are regression-checked against the pinned original recipe.
This is a precondition helper: ownership, current world identities, physical
support, streaming and sequence dependencies still need independent checks.

`_paired_phase_observation.observe(scope, expected_context=...)` copies the
current-world CinematicSystem request ID and state, exact sequence actor/player
asset relation, player status and camera manager view target. It checks scope and
world/controller identity before and after. The observer performs filtered
discovery and selected reference reads, never game function invocation. It owns
no actors and destroys nothing. Its classifications intentionally say
`pair_sequence_started`, **never** `visible` or `passed`.

Use observations at phase boundaries or bounded cadence. A diagnostic read
failure must be surfaced as unavailable evidence rather than triggering an
alternative dispatch, retry or destruction. Live visual proof remains required.

## Validation and integration boundary

Fifteen tests pass for exact graph/tail ordering and identities, source-recipe consistency, original-world/frame
validation, equivalent quaternion, malformed input, exact asset matching,
actor/player reciprocity, context changes, copied immutable output and no native
commands. They do not prove evaluated playback. Root controls all installation,
live UI, save-copy management and battle mutations. The first defensible live
candidate is original CleasTower plus its exact original arena frame; arbitrary
map relocation needs a separately proved sequence-frame mechanism.

## Runnable original-context candidate

`paired_original.prepare(scope, disposable_test=True)` now prepares the complete
unchanged two-action original graph using the existing explicit typed Blueprint
executor API. It retains the exact root and paired phase LevelSequence, validates
the copied original graph/tail and starting encounter row, reads the actual
source soft arena reference, requires its current original arena/root frame,
and requires idle battle/executor/cinematic services. `start()` revalidates the
source graph/arena/context and is one-shot. It never swaps a source parameter,
advances a phase manually or injects a cinematic.

`poll()` follows the shared original-action monitor and samples the paired phase
observer while a sequence player is present. Idle after activity is a diagnostic
state, never completion or visibility acceptance. A world/controller replacement
is terminal; uncertain dispatch remains non-replayable. `close()` only releases
the SDK's own planning copies and asset holds. Engine-owned actions, sequences
and callbacks continue through their original lifetime.

The adapter is intentionally first-run only until a faithful repeat policy is
proved: it rejects already-played `DuollistPhase2` history rather than clearing
history or changing the game's original `AllowRepeat` field. `disposable_test`
asserts caller-verified save/config isolation; the adapter performs no copying,
travel or installation. The original live arena must already be streamed; an
inactive loaded World export is not accepted as current presentation context.

The combined pair/source/frame/observer, shared action-monitor and explicit
Blueprint codec suite passes 48 tests. Candidate tests cover one-shot dispatch,
final dependency revalidation, unknown outcome, terminal world change, own-only
cleanup and phase diagnostic failure without battle interruption. Live visual
acceptance remains the root agent's separate test responsibility.
