# Authored component binding query research

The Scene Editor's actor replacement currently binds the root spawnable through
`LevelSequenceActor.AddBinding`. It does not verify that child component bindings
resolve, nor that source skeletal animation is compatible with the replacement.
An actor-dispatch acknowledgement is therefore not proof of component animation.

The Alicia Night Poem shot contains separately authored Renoir, Maelle and Alicia
spawnables. Replacing Renoir with Maelle leaves the original Maelle binding in
place; two Maelle characters in the shot are possible without a duplicate spawn.
Renoir and Maelle each declare `Face` and `Body` child bindings with skeletal
animation tracks. Monoco has a different `Body`/`Weapons_Base` hierarchy. Their
Universal Object Locator fragments are opaque to the current copied graph, so
component-name equality cannot prove that the engine resolved a child to the
replacement or that the active animation matches its skeletal mesh.

The existing `TargetBoundObjectQuery` is intentionally limited to reviewed root
camera GUIDs with empty factory overrides. It cannot answer this question for a
nested authored character or after `AddBinding` has changed the override object.

## Isolated research foundation

`target_authored_binding_query.h` reuses the same exact-build GetBoundObjects
function/parameter schema and `BoundObjectFrame` ownership model. It accepts an
active, factory-owned binding override and a nested binding value only when the
native owner supplies current player/actor/asset ownership and an authenticated
exact binding. The returned array is bounded to eight identities, retained in a
dedicated native output pool before its allocation is released, and never sent
as an engine pointer allocation to Python. Ambiguous or partial dispatch stays
quarantined. The adapter has not been connected to any runtime command.

`authored_binding_query_authority.h` supplies a research journal for acquiring
that exact binding from a native `GetPortableBindingID` resolver, rather than
trusting a caller-supplied sequence ID. It requires a uniquely reachable source,
an independently attested authored GUID in that source,
matches the entire returned GUID/sequence/parent tuple, rechecks current owned
identities, and forbids retry after an uncertain resolver outcome. Resolver and
ownership callbacks still need their real native implementations; the current
fixture exercises only a fake engine.

`authored_portable_resolver.h` connects native-owned inputs to the existing
durable `GetPortableBindingID` frame and exact target schema/lease adapter. It
always resolves into root space and quarantines an uncertain result or loss of
ownership; it does not itself prove occurrence or authored GUID membership.
Its isolated fixture checks clean, unavailable, rejected, mismatched and
ownership-lost cases, and compiles the concrete adapter with `/W4 /WX`. Neither
the bridge nor the native membership implementation is connected to the session.

`authored_guid_membership.h` separately checks exact `LevelSequence.MovieScene`,
`MovieScene.Spawnables` and `MovieScene.Possessables` layouts and verifies the
GUID occurs once across both arrays. The observed shipping metadata reports
spawnable GUID offset 160 in 240-byte entries and possessable GUID offset 56 in
128-byte entries. All GUID rows and both array headers are reread so changing
or duplicate declarations reject. Its bounded scan fixture tests duplicates,
changed rows/headers, lost context and invalid lengths; the native adapter is
compiled, but has not been invoked in the game. This check alone does not prove
that the source occurs under the playback root or that a component is animated.

`authored_sequence_occurrence.h` and
`target_authored_sequence_occurrence.h` implement an isolated bounded native
graph proof. The exact reader traverses `MovieScene.Tracks`, binding tracks,
and the camera-cut track; deduplicates the same track or section object; and
counts distinct `MovieSceneSubSection.SubSequence` edges, including repeated
references to the same sequence. It reads the graph twice, rejects cycles or
changes, and requires exactly one path to the selected source. Live read-only
metadata confirmed the class hierarchy and offsets used by this adapter;
the concrete adapter compiles and its graph fixture checks repeated shots,
cycles, mutation, missing sources and limits. It has not yet been invoked in
the engine or attached to an owner: its captures are borrowed identities and
its caller must retain and revalidate the root/source and current world epoch.

`authored_binding_query_fixture.cpp` covers nested IDs, active overrides, forged
root IDs, changed ownership, retained output cleanup and uncertain resolver
outcomes. `authored_binding_adapter_compile_fixture.cpp` instantiates the actual
target adapter. Both compile with MSVC `/W4 /WX` and run; neither is an in-game
test or proof of component resolution.

`target_authored_binding_authority.h` now composes the exact-build GUID and
occurrence readers with the native portable resolver and retained input checks.
It requires a native owner's separate factory/epoch callback, never accepts a
wire-supplied binding ID, and keeps occurrence snapshots in owner storage. A
concrete adapter compile fixture and an owner-association fixture compile and
run under `/W4 /WX`; the latter rejects stale identities, leases, epoch, and
player/actor/asset associations. The feature-gated integration below has not
been invoked against the game.

## Feature-gated owner diagnostic, not yet qualified

`TargetAuthoredBindingOperation` now composes that authority with the existing
`TargetAuthoredBindingQuery` and a dedicated eight-slot output pool. A
feature-gated `SequenceOwner` operation 16 accepts retained identities and
tokens for the query function, portable resolver target/function, playback
root and selected source, plus the authored GUID. It derives the native binding
ID itself; it does not accept that ID on the wire. The owning sequence verifies
its factory player/actor/root and world epoch, authenticates the supplied source
through unique occurrence and GUID membership, and protects all input tokens
while the operation exists. A successful response returns up to eight retained
identities; operation 17 releases the private output pool. Empty results remain
distinct from rejection. Sequence close and retired-world cleanup release this
operation before destroying the player; uncertain dispatch or SEH quarantines
the actual sequence owner and forbids replay.

This path is enabled only by `E33_SEQUENCE_AUTHORED_BINDING_SESSION`. It is
advertised as `sequence_authored_binding_diagnostic_protocol` and is intentionally
absent from the current installed runtime. `_authored_binding_diagnostic.py`
validates the fixed 288-byte request and response; `_sequence_owner.py` and
`_session.py` gate the two new operations. There is no end-user API or caller
yet. Before writing a caller, preserve the proof input leases until operation 17
acknowledges or sequence retirement closes them, inspect result identities only
while that output pool remains retained, correlate the entire response, and
abort ownership on an unknown outcome. A pre-dispatch rejection may still have
created an empty operation and must be closed before another diagnostic query.

The isolated `build-authored-runtime237.cmd` uses the existing local MSVC
toolchain and creates `build/release/runtime-session-cinematic-v237/` and
`build/release/research-probe-cinematic-v237-retirement/`; both compile with
`/W4 /WX`. The concrete operation's missing-session fixture, earlier retained
owner/authority fixtures, seven wire/lifecycle tests and 117 sequence tests pass. This is
compile and bounded negative evidence only: the feature has not been staged,
attached to a live game, checked with a real source or output object, or tested
across world retirement. In particular it does not establish component
resolution, skeleton compatibility, retargeting, or animated replacement poses.

The bounded private caller is `build/encounter-live-20261024/private/authored237_live.py`.
Its offline tests pass and a saved Alicia graph selects `BP Cine Renoir`,
`Body`, and `Face` exactly. Do not run it against the installed v236 runtime.
After a separately reviewed v237 candidate and matching Python source are
staged, the standard `coverage224.py` bridge can load Alicia's Night Poem.
With that bridge's `e198` and `server125` in the owner-thread console globals,
load the helper and invoke `install(e198,server125)`. Use `test237.original`
or `test237.replacement` to queue the respective preview. Seek to a chosen
evaluated frame and pause; `test237.observe` synchronously queries root, Body,
and Face, takes bounded class/outer/index/serial snapshots while each output
pool is retained, releases each pool, then closes the preview. It never yields
to UI callbacks or calls the player between an acquired result and release.
Repeat from a freshly opened preview for the other mode at the same frame.
Returned identities do not prove skeletal or facial animation compatibility.

If query admission is rejected, the wrapper still demands operation 17 to
release a possibly emplaced empty pool. If release is deferred, retain the
preview and all proof leases, allow the existing cleanup poll to retry, and do
not start another query. If dispatch or acknowledgement is unknown, the
wrapper marks ownership unknown and aborts the SDK session; do not issue op17,
close or replay the query. Preserve the process and diagnostic evidence for
manual recovery rather than guessing whether dispatch occurred. Never copy the
private helper, test data, logs or saved settings to a release bundle.

## Required integration and proof

1. Add an isolated native sequence-owner operation with a dedicated output lease
   pool and a non-replayable resolver frame. Native code, not the wire packet,
   must attest the selected root/source/GUID and exact resolved binding ID.
2. Restrict the operation to the current retained player/actor/root association;
   revalidate world and session identities before and after dispatch. Release
   all returned leases before allowing the owned preview or output pool to close.
3. In a disposable candidate, resolve the actor GUID and each `Face`/`Body` child
   GUID at a fixed evaluated frame, first without an override, then with a known
   replacement. Observe classes, outer ownership and exact identities. An empty
   result is a valid observation, not evidence that an override was applied.
4. Separately inspect the bound skeletal components' mesh skeletons and animation
   evaluation, and compare on-screen poses across representative shots. Bound
   object identity alone cannot establish animation or facial compatibility.
5. Qualify cleanup, world transitions, bounded failures and multiple nested shot
   occurrences before exposing any diagnostic or automated remapping in the SDK.

No fallback component binding, replacement retargeting, or generalized ability to
query arbitrary game objects is provided by this research foundation.


## Matched-frame animation observations (2026-10-27)

An isolated v243 player at frame 821 of Alicia's Night Poem resolved the
original Renoir root, Body and Face, then a separately prepared Sciel override
resolved Sciel's own Body and Face. Both body meshes reference
`/Game/Characters/Mannequins/Meshes/SK_UE5_Mannequin.SK_UE5_Mannequin`; both
faces reference `Face_Archetype_Skeleton`. Each body reported AnimationMode 2
and an `AnimSequencerInstance`. Faces remained in Blueprint mode with their
respective Renoir/Sciel facial Blueprint classes. This establishes matching
skeleton asset identities for this pair, not evaluated bone/curve correctness
or general retargeting. LeaderPoseComponent remains an unsupported weak
reference in these observations.

The original Renoir facial descendant binding
`ABP_Facial_Cine_Renoir_C_0` independently resolved the original face's
`ABP_Facial_Cine_Renoir_C` instance at that frame. With the Sciel override,
that same authored descendant resolved Sciel's own `ABP_Facial_Cine_Sciel_C`
instance. Read-only reflected facial controls matched at frame 821, including
Expression_1 5, strength 0.5, ExpressionsBlendTime 0.75 and
ManualFacialAnimAlpha approximately 0.8. This supports descendant resolution
and property application for this pair; it does not prove evaluated facial
curves, final bone poses or every scene's compatibility. Query outputs were copied while their
dedicated native result pool remained retained; each pool was released before
the preview closed. The diagnostic is not installed in the production v236
runtime. No private snapshots, settings or helper scripts belong in releases.
