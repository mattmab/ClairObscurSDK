# Cinematics testing candidate

## Active integration target

The requested end state is game-authored sequences editable in Scene Editor's
timeline, including replacing authored characters and adding NPCs through the
Encounter Editor's proven Blueprint construction. Playback-only catalog support
does not satisfy this target. QA battle testing is the visual test environment.

Required acceptance evidence:

- Select a game-authored LevelSequence in Scene Editor, inspect its complete
  nested shots, actor bindings, animation, camera and audio tracks, and load it
  as an editable scene with authored timing preserved.
- Edit and scrub the imported timeline, save the edits, reload, and replay the
  changed result. Persist asset paths, binding IDs and edits; never transient
  UObject addresses. Original game assets must remain reusable unchanged.
- Replace an existing character binding with a different character, preserving
  the other authored bindings. Demonstrate compatible animation and cleanup;
  report unsupported skeleton/track combinations explicitly.
- Spawn scene NPCs through the same inspected Blueprint construction mechanisms
  as the encounter implementation, without starting battle or dispatching its
  campaign callbacks. Demonstrate transforms, timeline control and removal.
- Verify Stop, natural completion, failure and map replacement restore input,
  camera and music and release owned actors in the correct world.
- Install the verified SDK and consuming mod packages locally.

Current audit: Scene Editor's original playback uses a six-actor assembly schema
and a fixed native timeline plan. Authored source import and edit documents are
separate from that playback backend. Encounter spawning
has authored instance routes, but currently owns battle preparation and permits
only one active native enemy owner. The current bound-object query explicitly
requires empty binding overrides. Character replacement therefore needs a new
owned override contract rather than bypassing the existing query restrictions.

Scene Editor 0.13.0 adds a separate retained source workspace under **Game
sequences**: 155 cataloged sequence assets, search, explicit Load source,
nested track/object inspection and Unload source. Loading does not Play or
dispatch the story action. A child scope retains source assets; failed world
checks reject the read, and deferred lease release remains reachable during
retirement. This is source import, not editable timeline conversion.

The read-only worker now decodes ordinary ObjectProperty/ClassProperty arrays
inside reflected structs. This exposes MovieSceneBinding.Tracks, which normal
root-track inspection omitted. It checks allocation bounds, repeated contents,
descriptor stability and each returned object identity, and labels copied
prefixes as partial. Native stability/bounds tests and Python identity/schema
tests cover this addition. No target-side mutation capability was added.

Live QA source-browser qualification: SimonIntro loaded 583 objects across its
root and nested sequence, 110 declared bindings and 16 skeletal animation
sections, with zero pending graph nodes. Search, selection, loading and Unload
source worked through the in-game UI. This does not mean all channel data was
decoded: frame ranges contain opaque native state, and channel arrays, several
enum fields, text and delegates still have explicit unsupported observations.
The updated read-only worker and Scene Editor are installed locally. Regression
suite: 2,514 tests, six skipped. A subsequent status-text change removes a
duplicated summary without changing the qualified import path.

Version 0.14.0 adds authored timeline documents and section-range controls.
Documents preserve a hashed copied source and store edits separately by section
path or channel field/source-key ordinal. Numeric/Boolean key edits reject
incomplete arrays, nonfinite values, invalid types, duplicate key edits and keys
crossing their neighbors. Tangents and interpolation remain in the untouched
source. Save/reload uses a separate `.authored.json` store and atomic replacement.
These documents do not yet execute edits against a native sequence instance.

The read-only worker also decodes scalar and structured arrays within channels,
including native Boolean arrays, with extent/type checks and repeat observations.
The qualified MovieSceneFrameRange codec preserves inclusive/exclusive/open
endpoints and each nested sequence's own ticks. Its binary/reflection evidence
is in [authored-frame-range-20261024.md](research/authored-frame-range-20261024.md).
JSON wrapper depth is bounded separately from the four typed struct levels.

Live Simon source qualification now includes 928 channels with no channel
decoding errors or partial arrays in this source. Other enum/delegate/text and
non-channel fields still have explicit unsupported observations. In the QA GUI,
the original root shot start 74400 was edited to 75200, saved, and reloaded with
75200 displayed; the saved source still contains 74400. A separate test also
changed a real translation key and round-tripped the 6.9 MB document unchanged.
Regression suite: 2,522 tests with six skipped. Updated SDK/read-only worker and
Scene Editor 0.14.0 are installed locally; native runtime 216 is unchanged.

Remaining acceptance work includes a graphical authored timeline/key editor,
owned edited-sequence playback and scrubbing, runtime character overrides and
scene-only Blueprint NPC spawning/control. Existing native camera binding gates
are unchanged. Editing JSON documents alone does not satisfy these requirements.

## Portable full scenes, version 0.2.3

Dispatch work for 0.2.4 reuses one explicitly owned read-only worker throughout
portable preparation. Endpoint context observations borrow that worker rather
than creating nested owners. Native music/sequence ownership still requires an
attached input context; panel construction happens before acquisition, while
gameplay audio remains running until endpoint/context checks finish.

Factory output discovery can now request a fresh selected closure containing
the returned objects and every parameter constraint. Native output leases are
adopted before discovery, and ordinary typed-result validation remains intact.
Completion also rebuilds fresh descriptor planning data after nested cast
initialization rather than merging it with pre-initialization observations.
Music preparation reads the exact GI descriptor closure and its two detached
container fields, preserving complete empty-container and scoped-assignment
validation. Timing details go to the SDK log, not normal console output.

Measured QA Lune run before the final music-closure change: request to Play
13.90 s, sequence build 1.33 s, hidden panel 1.24 s, music setup 4.74 s.
The final music-closure candidate's Simon intro measured 0.96 s music setup,
1.31 s sequence build, 2.26 s endpoint preparation, 6.02 s locked preparation,
and about 8.3 s backend start. These are individual runs, not a cold-load
benchmark or a guarantee for every asset. The previous Camp run measured
21.20 s request to Play; scene/map/cache differences limit direct comparison.

The authored_source module is the first import-stage reader. It copies root
timing/cast/track declarations and labels unsupported/truncated values explicitly.
The graph inspector also follows stored nested sequence, track and section
references with cycle and size bounds. Gameplay actor references are copied but
not traversed. Unsupported fields remain errors, and incomplete graphs list
pending nodes. It does not yet provide editable timeline import, native channel
conversion, character substitution or Blueprint NPC timeline control.

QA Lune and Simon intro completed naturally with original music restoration.
The first QA outro returned and restored music but was classified interrupted.
Completion sampling now reads IsPlaying before the cursor, avoiding a running
cursor sampled immediately before a natural stop being paired with the later
stopped state. The exact endpoint byte comparison and context checks remain;
this does not turn idle into completion. Revision 25 passes 2,503 tests with
six skipped, and is installed locally as 0.2.4-dispatch. The final QA outro
rerun reached endpoint_observed with acknowledged cleanup and restoration of
the original music reference.

The browser adds a separate **Play full scene here** route for exact reviewed
definitions. It reuses the encounter-owned sequence player, private translation,
camera restoration and finite endpoint journal. Playback runs the LevelSequence,
not its campaign GameAction. Current-save unlocks and fresh world admission still
apply. Original-map story playback remains a separate action.

Private cinematic music and widget services now share the title adapter's
native ownership machinery. The routing class is explicitly retained when a
full scene does not load a title-card track itself. Sequence creation takes a
fresh post-factory catalog rather than merging output identities into metadata
observed before the nested cast loaded.

LuneArrives was played in Camp with both actors, changing camera shots and
subtitles visible. Its authored dialogue backing, music and SFX components were
active. Natural completion returned to exploration, released playback ownership,
and left none of that scene's observed audio tracks active. Scenery obstruction
and placement polish are deferred at the user's request; original scenery and
lighting are not reconstructed. Active components do not prove audible mix or
lip synchronization. Wider catalog portability is not implied.

Frozen revision 16 passes 2,494 automated tests, with six skipped.

SimonIntro and SimonOutro also completed consecutively in Camp using the same
SDK session. Actors rendered and authored dialogue, music and effects components
were active. Both finite endpoints were observed, cleanup acknowledged, and the
original music reference restored. These two backend checks used an explicit
diagnostic unlock override in the isolated test copy; the installed browser still
requires current-save unlocks. No save-history flags were changed by that override.

Revision 16 is installed locally as Cinematics 0.2.3-portable-scenes with native
runtime 216. The installed release manifest and 13 curated mod archives verify.
All 180 original save/config baseline files remain unchanged. Cold scene setup
still takes tens of seconds; this build does not claim instant scene startup or
portability for the rest of the catalog.

## Original in-engine scenes, version 0.2.2

Original-map playback now uses the encounter action observer: it brackets every
snapshot with the current world/controller identity, validates the executor and
cinematic services' exact classes and common owner, and records exact selected
action identities through nested action instances. The expected LevelSequence
is observed separately from action execution. Retirement is not presented as
proof of actors rendering or audio reaching the speakers.

The original action and its exact sequence are retained before playback, then a
fresh idle/context check runs immediately before dispatch. Known readiness
rejection does not become an uncertain invocation. The full-scene browser filter
offers the original story route rather than a movie segment for overlapping
definitions. Original map and explicit story-effects setting remain required.

Isolated live checks added for LuneArrives and FirstLancelierOutro: authored
actors/cameras visibly played, both ended naturally, and exact action/sequence
tracking released ownership before another scene could start. LuneArrives'
authored SFX track was observed active. Original story actions can change the
scene's lighting and player location through their own campaign behavior.

LuneAndSciel camp playback also showed its actors and subtitles, with its exact
authored VO backing, music and SFX assets observed on active audio components.
It ended naturally, returned to exploration, and the full-scene browser reopened
with the controller idle and no retained playback ownership.
An active engine component is not a listening or synchronization acceptance test.
The broad first audio inspection was a private diagnostic and was replaced with
a bounded batched observation; that inspection code is not distributed.

The full automated suite passes 2,484 tests, with six skipped. This validates
implemented contracts, not all 83 original-map routes or all 155 definitions.

Cinematics now separates the local catalog, browser, playback controller and
native replay adapters. Menu rendering uses copied state. Clicking Play queues
an intent; the session thread rechecks the selected save, world, controller,
definition and route before allocating a backend.

The revision 6 candidate passed 2,467 automated tests with six skipped. This
checks the implemented contracts; integrated live acceptance is still ongoing.
The measured main Mods open was 119 ms, while the first Cinematics open was
604 ms. Cinematics has not met the 200 ms menu target on that measured first
open, and these measurements do not establish cold-start or repeat-open bounds.

Integrated disposable-save checks confirmed enabled-mod restoration, Map Travel
from the Continent to Ancient Sanctuary, Scene Editor opening, and visible movie
frame progression with Stop returning to the browser. Audio synchronization,
natural completion, repeat playback and interruption during world replacement
still require broader live acceptance. A transient history read leaves unlocks
unavailable until a fresh observation succeeds; the browser now repaints after
that queued observation completes instead of retaining its earlier error.

Only one replay runs at a time. Cleanup that has not been acknowledged retains
its owner. A changed world revokes continuation and uses an explicit native
retirement path rather than restoring an old camera, audio component or widget.

## Testing

Enable Cinematics in Mods, then use its Open Cinematics action or enter
`cinematics open` in the console. No default keyboard binding is assigned.
`cinematics status`, `cinematics refresh`, and `cinematics stop` are also available.
The browser supports filtering, paging and `cinematics search TEXT`.

Check these transitions:

1. Open the library, change filters, select a scene, and return to Mods.
2. Start an available title or movie, stop it, and reopen the library.
3. Let an available replay finish naturally; verify camera, audio and controls.
4. Return to title, load a save again, and reopen Mods and Cinematics.
5. Check Scene Editor, Map Travel, WorldBuilder Map Loader, Flight and the Enemy
   Spawner independently; Enemy Spawner's default menu key is `-`.

Availability is specific to a reviewed playback route, current save history,
map and runtime capabilities. An entry in the catalog does not mean portable
playback has been validated. Unsupported controls are not offered.

Movies replay only their reviewed prerendered segments, sometimes with a
separate authored audio timeline. They do not replay the complete surrounding
in-engine scene. Title and movie availability reflects the reviewed route and
current prerequisites; earlier mechanism checks do not establish natural-end,
Stop, synchronization, repeat or world-transition acceptance for this rebuild.

Original story actions require the explicit **Allow original-map story actions**
setting and their original map. They may change save/progression state. They
remain game-owned, so Cinematics does not offer Stop for them. Use Map Travel
separately; the browser no longer performs implicit travel.

The three Simon scene previews are experimental Continent-only routes. Full
portable Simon completed both battles and all three scene endpoints in an
earlier dedicated coordinator test. That is separate from acceptance of the
rebuilt library. Camera clearance, HUD presentation, defeat/interruption and
handoff latency still need qualification. This does not constitute acceptance
of every cinematic, map or encounter. Full encounter coordinators are separate
from the cinematic library and are not substituted for individual battle entries.

This candidate is for local testing. It does not replace a published release
until the remaining encounter and presentation checks pass.

## Inspection against encounter foundations (2026-10-24)

The catalog contains 155 definitions. Current adapters cover 2 titles, 2 movie
segments, 3 Simon previews and 83 original-map action mappings across 26 maps.
MyFlower P1 and SimonOutro overlap categories, leaving 88 distinct mapped
definitions and 67 without an adapter. Only 7 definitions have one of the current
portable title/movie/preview profiles; a mapped original action requires its map.

Of 155 definitions, 118 have no explicit saved-history ID. This is unknown unlock
mapping, not proof that those scenes are locked. Original-map story playback is
admitted independently from the portable routes' unlock predicate. Seventy-nine
original-map records retain decoder limitations, and only one records full-route
live verification. A map association is not complete scene-dependency validation.

Two integration regressions found during inspection are corrected in source:

- The discovery producer omitted `definition_catalog_complete`, which the real
  title player requires. Validated catalog success now supplies it; a failed
  catalog observation cannot inherit a previous successful flag. Tests exercise
  actual discovery and title admission together for both title profiles.
- A movie profile hid the same definition's original-map action route. The
  original story choice is now separate, with its own explicit save-effects
  label, map/setting admission and engine-owned lifecycle. It does not inherit
  the movie route's unlock or media-player requirement.

Reusable encounter foundations include retained asset preloading, a minimal
reusable context panel, camera ownership, arena-relative placement, finite
sequence endpoint evidence, typed lifecycle outcomes and retired-world cleanup.
Portable Simon already combines them. Cinematics previews currently reuse only
the lower-level sequence/context mechanisms: they import Simon's private context
reader, use a fixed player-relative target/source anchor, construct a context tree
per preview, and have no equivalent preloader. These should become shared
services rather than separate scene-specific orchestration.

The sequence origin changes private instance translation. It does not recreate
map possessables, relative tracks, director events, lighting or streamed scenery.
The native binding query also retains two specific diagnostic profiles. General
binding/dependency support is therefore unfinished; removing catalog gates alone
would not reproduce every scene correctly.

Completion and clip expansion (local revision 9):

- Acknowledged original-action dispatches now retire SDK tracking after ten
  seconds of repeatedly observed idle if the selected action was never seen.
  This is an unverified/failed playback outcome, not successful cinematic
  completion. It never stops a game action, synthesizes its callback, or advances
  an encounter. Read failures reset the idle window; uncertain dispatch remains
  retained. Read-only status observation now recovers from transient poll errors.
- Fifteen installed CS_ movie assets appear as separate movie-clip entries,
  with a dedicated filter, owned fullscreen playback and Stop. Manifest identity
  is rechecked at admission. They do not claim a save unlock or a full story
  scene; only embedded movie audio is available on this route. Existing reviewed
  Alicia composition remains separate.
- Isolated live checks: ArrivingInTheBattleFieldStart visibly played, completed
  naturally, returned to a working browser, replayed, and stopped through the
  visible control. ArrivingInAncientSanctuary original-map action showed its
  actors/subtitles/camera, returned to exploration, and its tracker changed from
  ACTIVE to IDLE with ownership released. The browser reopened in the same SDK
  session. BackAtCamp also showed its title, ended naturally and restored the
  browser. These checks do not qualify all fifteen clips or all original actions.

Remaining concrete review items:

- Exact native completion attribution for every original action is still
  unfinished. The bounded unobserved outcome prevents an indefinite UI tracker
  while preserving the distinction between dispatch, activity and visual success.
- Startup readiness currently covers catalog/session/menu registration, not
  prepared replay assets. Media audio still performs global catalog discovery
  and synchronous sound preparation during Play.
- Playback polls repeatedly discover current controller context. Measure and
  reduce that cost through existing lifecycle admission services while retaining
  current-world identity checks.
- The browser's single Unavailable label conflates missing adapters, unknown
  history, wrong maps and disabled story actions. Historical tested badges also
  need to remain distinct from current integrated acceptance.
- Add live binding, callback, natural-end, repeat and travel-interruption
  qualification by scene family. Passing isolated controller tests does not
  establish whole-catalog playback coverage.


Authored timeline progress (2026-10-24): complete copied curve keys now have editable tick/value controls and separate persistent overrides, verified live with SimonIntro in Map_BattleTesting. Source interpolation/tangents remain unchanged. Rational source-to-player frame conversion and a compiled native seek packet fixture are implemented; runtime seek dispatch, private edited sequence playback, character replacement and Blueprint NPC integration remain unfinished. Revision 30 is installed locally; 2528 tests passed with six skips. No publication was performed.


Native v217 update: owned-player frame scrubbing is implemented and qualified live with SimonIntro in the QA battle map, including forward/reverse/fractional/end-frame seeks, known out-of-range rejection, visible actor/camera changes, and clean return. Warm requests measured about14-24ms after one metadata preparation. Full suite2534passed/sixskips; v217installedlocally. See research/owned-sequence-seek-20261024.md. Scrub controls in the authored UI, private sequence edit application, character replacement, Blueprint NPC integration and cold dispatch optimization remain unfinished.
