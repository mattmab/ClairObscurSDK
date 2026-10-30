# Private authored sequence copies

The shipping executable exposes
`/Script/MovieRenderPipelineCore.MoviePipelineBlueprintLibrary:DuplicateSequence`.
Its observed native function entry is RVA `0x50e77a0`, with object inputs Outer
at 0 and InSequence at 8, and a MovieSceneSequence object return at 16. The
parameter frame is 24 bytes. The standard retained invocation path independently
validates the current reflection schema and native dispatch.

`cinematics.authored_copy.duplicate` uses this engine function and requires a
distinct LevelSequence under the supplied retained private outer, with its own
reciprocal MovieScene root. This construction does not grant arbitrary source
playback or edit authority. The caller retains the outer and copy through use.

## QA evidence

In the isolated Map_BattleTesting process, SimonIntro duplicated into a private
Object outer. Inspection found 583 nodes and two LevelSequences, with no pending
nodes. All inspected nodes, including the nested sequence, belonged beneath that
private outer. Authored signatures matched the source, permitting copied section
selection without persisting runtime addresses.

The saved cinematic-shot section start was changed from native tick 74400 to
75200, with end 1739200. The engine's
`MovieSceneSectionExtensions:SetRange` setter updated the copied section, and
readback confirmed the exact requested range. The source section's signature
and range were checked before application; its range remained unchanged after.

The setter interprets integer inputs in display frames, not native ticks. The
implementation converts with exact rational arithmetic and rejects off-grid
edits instead of rounding. The current invocation codec only admits
QualifiedFrameTime returns; FrameRate inputs needed for exact off-grid editing
are not yet supported. No seconds-based approximation is used.

The copied, edited asset was passed directly to OwnedLevelSequence's retained
asset build path. Owned playback started, readback confirmed the player used the
copy, and a seek to frame 600 visibly rendered Simon. Sequence cleanup and then
private-copy scope release both acknowledged normally.

Revision 40 passed 2549 tests with six skips and was installed locally through
explicit candidate inputs. The 180 original save/config baseline files remained
unchanged. No GitHub publication occurred.

## Outstanding integration

This qualifies the engine copy, frame-aligned section-edit application, retained
asset factory path and one visible copied-source playback. It does not prove a
large visible retiming change, natural completion of the edited copy, all scene
families, or all editor controls. The editor toolbar still previews the original
source. Applying complete curve-key edits, exposing edited playback, arbitrary
native-tick ranges, character binding replacements, and Encounter Blueprint NPC
integration remain unfinished.

## v218 exact native ticks and edited preview

The local v218 runtime adds separately negotiated
`sequencer_frame_values_protocol=1`. POD wire kinds 23, 24 and 25 represent scalar
FrameNumber, FrameTime and FrameRate values, using the existing qualified native
struct schema walker. FrameRate inputs require positive numerator/denominator;
FrameTime requires a canonical subframe. The native path rejects these kinds
for Blueprint invocation. Existing copied QualifiedFrameTime observations retain
their prior representation contract, including values consumers must reject.

Off-grid section edits temporarily change the private owning sequence's display
rate to its tick resolution, apply SetRange in exact ticks, and restore the old
display rate. The live QA test read back start tick **75201** exactly, preserved
end tick 1739200, confirmed display-rate restoration, and confirmed the original
source range remained unchanged. The edited copy then played and rendered Simon
at frame 600. The actual loaded v218 DLL was verified in the process module list.

Scene Editor now exposes **Preview edited timeline** for reviewed source profiles
with section edits. It creates the private copy under the owned preview tree,
applies section edits, and uses the retained asset factory path. Timelines with
curve-key edits are explicitly disabled/refused; those edits are never silently
discarded. The original-source preview remains available separately.

The actual UI path was exercised with a disposable saved document containing the
75201-tick edit: load saved document, open edited preview, seek to frame 600,
observe Simon, and Play to later camera shots and party actors. This does not
yet qualify all scene families, curve-key application, character replacement or
Blueprint NPC spawning.

Back returned to the authored timeline and Close restored exploration. The
tested revision 42 editor package was installed locally, with all 180 original
save/config baseline files unchanged. A cosmetic rough edge remains: the reused
editor may display its prior preparation message after preview closes.

Both enabled/disabled native frame-protocol fixtures and the native frame-schema
fixture compiled with /W4 /WX and passed. Revision 42's full Python suite passed
2552 tests with six skips. Remaining work includes channel/key object-array
access, applying curve edits, binding replacements, Blueprint NPC ownership,
dispatch performance and broader lifecycle/completion coverage.

## v220 retained scripting-array qualification

The separate `sequencer_object_array_protocol=1` capability uses a bounded native
operation for GetAllChannels and one selected GetKeys ordinal. Returned objects
are stabilized and retained in the session lease pool before native array storage
is freed. Python adopts every output token before reading its descriptor. Unknown
dispatch/free outcomes quarantine the durable frame and preserve its roots;
known pre-dispatch rejection remains distinct. Input descriptors use the existing
atomic stable-lease operation, including previously unassigned serials.

The live v220 QA test successfully dispatched GetAllChannels on a private copied
Simon transform section, but returned **zero channels**, despite the imported
stored transform curves containing keys. This is not successful key-edit
application. Inspection of the shipping thunk at RVA `0x4ae93a0` shows channel-type
lookups followed by clearing the result array; the tested path supplies no usable
scripting-channel wrappers. GetKeys and the key setters therefore remain
unqualified in-engine. Curve-edited preview remains explicitly refused.

The test also found duplicate private sections with equal signatures under one
copy owner. Section selection now resolves ambiguity through references reachable
from the playable root, rather than selecting an arbitrary copy. Incomplete or
still ambiguous graphs reject the edit. This fallback currently reads the full
graph and needs a narrower sequence/track-reference traversal for performance.

The native array/schema fixtures compile with /W4 /WX and pass. The Python suite
passes 2560 tests with six skips, including adoption-before-reader-failure,
known/unknown outcomes, and duplicate-section selection. Full Simon source preview
and frame-600 scrubbing also work under v220 in the QA battle-testing map.
Character replacement, Encounter Blueprint NPC integration and actual curve-key
application remain unfinished.

## Reference traversal and interactive preparation performance

The duplicate-section selector now follows projected MovieScene/track/subsequence
references, including CameraAnimationSequence subclasses, instead of reading the
entire graph and every curve. Track section and subsequence reads are batched.
It still validates reciprocal ownership, complete reference containers, declared
field completeness, graph bounds, and unique selection. The live SDK resolved two
equal-signature private Simon candidates in **301.5 ms**. A separate same-candidate
comparison measured **929.2 ms** without batching and **279.6 ms** with batching.

This exposed a shared reader defect: empty struct arrays have no nested value
from which to discover their element type. Reference capture now also follows
exact identities declared in property metadata, then decodes the same response;
it does not repeat the original value query or enumerate all objects.

Interactive authored preview now uses `prepare_scrubbing`, refreshing its playback
metadata without preparing natural-endpoint tracking that its first seek would
immediately invalidate. Natural completion remains a separate opt-in path for
ordinary cinematic playback. In one same-session QA comparison, preparation of
those queries fell from **2235.5 ms** to **440.6 ms**; total preview preparation
fell from **10500.9 ms** to **8831.9 ms**. These are individual observations, not a
latency guarantee. Overall dispatch remains too slow and needs further work.

The optimized preview rendered Simon and scrubbed to frames 600 and 1200; normal
close acknowledged cleanup. Revision 50 passes **2570 tests**, with six skips.
The tested Python/editor changes are installed locally; original save/config
baseline hashes remain unchanged.

## Shared name-resolution IO

Read-only worker version 3 adds bounded asset/export name-resolution requests
under its existing pinned process and executable-image gate. Asset and Blueprint
class loaders borrow this worker when supported; older workers retain the prior
separate-probe path. Failed qualified requests do not fall back or replay. Name
receipts validate the exact path, process, boundary shape and bounded integer IDs.
The actual blocking engine loaders and retained invocation contracts are unchanged.

Live QA lookups returned identical results: sequence lookup **20.1 ms** versus
**425.9 ms** in a separate probe, and widget-routing class lookup **23.8 ms** versus
**414.4 ms**. Exploration snapshot and subsequent preparation now share one reader
operation, retaining the same reciprocal pawn/controller/world checks.

One profiled authored preview prepared in **8014.9 ms**, compared with the preceding
**8721.0 ms** observation. Snapshot observation fell from **764.5 ms** to **405.1 ms**;
sequence creation measured **1586.7 ms** and service arming **1268.7 ms**. Timing
variation remains material; these observations do not establish a latency bound.
Native reader command-policy fixtures compile with /W4 /WX and pass. The final
candidate passes **2574 Python tests**, with six skips.

The reviewed full LuneArrives adapter also played in the QA map with actor
animation observed. Its initial endpoint observation reported playing, and a
later observation positively reported `endpoint_observed`; ownership then closed
normally and QA lighting was restored. Foreground activation preceded the final
observation, so this run does not establish a background-playback latency bound.
The full-scene dispatch measured **8556.7 ms**, including **6400.5 ms** after input
acquisition. Broader dispatch improvements and the remaining editing integrations
are still unfinished. The verified revision 53 inputs are installed locally.

## Cast hierarchy and inherited track import

The authored timeline now includes a cast browser showing each shot's binding
GUID, spawnable template, parent/child component bindings and associated tracks.
GUIDs remain scoped to their sequence, so identical GUIDs in separate shots are
distinct. The projection requires complete identity and membership fields while
preserving unrelated unsupported spawnable fields as unsupported. It does not
turn copied declarations into callable actor handles or mutate source templates.
Unimported track references remain explicitly listed rather than silently omitted.
Character replacement and Blueprint NPC playback are not yet implemented.

Source import now follows MovieScene track/section and sequence ancestry instead
of requiring all track classes to begin with `MovieScene`. A live read in the
isolated QA session imported **657 Simon source objects**, with no pending nodes,
**110 cast bindings**, **51 child-component links**, and **zero unread cast-track
references**. The preceding importer omitted thirty referenced tracks from the
captured source. The read took **21.11 seconds**; this is import cost, not playback
dispatch latency. The temporary private copy closed normally after inspection.

The cast presenter was checked against that live imported graph, including Lune's
template detail. No full in-game interaction with the new cast page is claimed.
The complete suite passes **2581 tests**, with six skips; a subsequent 21-test
focused run also passes after additional malformed-input checks.

## Owned cinematic Blueprint staging

Native candidate v221 adds `timeline_blueprint_protocol=1`. The initial SDK API
constructs the reviewed Lune, Sciel and Verso cinematic Blueprints in the QA map,
using the Encounter Editor's existing deferred-allocation, strong-retention,
construction and retirement journal. Blueprint construction supplies the original
character components; this route does not assemble independent mesh actors.
It does not initialize enemies, bind battle arenas, activate overlaps or enter
combat. Timeline-owned actors are restricted to construction, reveal and removal.

Construction stays hidden with collision disabled; an independently journaled
once-only reveal enables actor ticking and visibility while keeping collision
disabled. Unknown/partial reveal is not replayed. Native fault fixtures cover
rejection, failure at every reveal step and once-only success. The exact native
class profiles and unit-scale transform bounds remain independently enforced.

All three original Blueprints constructed and visibly rendered in the lit QA
map, with acknowledged removal between profiles. A fresh retained observation
confirmed Lune's actual Blueprint ancestry and root position. The explicit test
transform placed the actors above the floor; automatic grounding and animation
track compatibility are not qualified by this test. A preliminary dark view was
caused by the default QA pawn falling below the arena; the existing QA mod's
verified arrival bookmark restored the test view without changing a save.

The existing authored preview also created, sought to frame 600, rendered Simon
and closed normally on v221. That dispatch measured **6436.3 ms** in one run;
this is an observation, not a latency guarantee or a new performance claim.
The complete Python suite passes **2589 tests**, with six skips. Native candidate
and reveal fixture builds pass `/W4 /WX`.

This is a single-actor QA construction backend. Simultaneous cast ownership,
editor binding overrides, character substitution, curve playback edits and
broader NPC profiles remain unfinished. It does not yet add a Blueprint-spawn
control to the editor UI. The tested v221 backend is installed locally.

## Nested actor binding backend

Candidate v222 adds two separate capabilities: exact scalar
`MovieSceneObjectBindingID` values for retained native calls, and a retained
`GetPortableBindingID` query. The query owns its input leases and argument/result
frame through dispatch and validation. It does not admit pointer-bearing binding
proxies into generic POD calls. Uncertain outcomes quarantine the frame; they
are not replayed. Schema, envelope and POD fixtures build with `/W4 /WX`.

The live engine returned sequence ID **155498434** for Lune's binding below
`MCS_SimonIntro`, and **0** for the same GUID within `CS_SimonIntro` itself.
Both used parent index zero. Nested IDs therefore come from the engine's
hierarchy resolver rather than assuming a root-local GUID is sufficient.

The initial `cinematics.binding_overrides.bind_actor` API accepts an SDK-owned
sequence before its first evaluation and a revealed Blueprint actor constructed
under that sequence's scope. It requires a fresh, unique source occurrence and
an authored spawnable actor declaration. It invokes `LevelSequenceActor.AddBinding`
on the owned factory actor with original asset binding disabled. It never edits
the authored source template. Reused shot instances, arbitrary actor handles,
post-evaluation changes and duplicate attempts are rejected.

In the isolated lit QA map, an original Sciel cinematic Blueprint replaced
Lune's binding in Simon's intro. Scrubbing evaluated the other authored cameras
and actors. The replacement's root moved from its staging pose to the authored
scene pose; retained reads confirmed Sciel's original body, face and hair mesh
assets, two live Sciel actors, and no live Lune actor. Only source templates
remained after preview cleanup. This demonstrates actor replacement, not full
facial-animation, skeleton-retargeting or arbitrary-component compatibility.
The test preview prepared in **10891.6 ms**, including Blueprint construction,
binding resolution and the override; it is not a dispatch performance improvement.

Bound actors cannot be removed while their consuming sequence remains alive.
Scope cleanup closes that consumer before descendant actors, retaining native
ownership if sequence cleanup is deferred. Tests cover ordering, once-only
dispatch, known rejection, unknown outcomes and stale/ambiguous contexts.
This backend does not yet expose persistent cast edits in the editor UI or
support simultaneous replacement actors. Those remain part of the active goal,
along with curve application, wider NPC coverage and dispatch latency.
The full Python suite passes **2602 tests**, with six skips. The tested v222
backend is installed locally; explicit manifest and curated-mod checks pass,
and the original 180 save/configuration baseline files remain unchanged.

## Saved cast replacements in the editor

Authored documents now store optional `cast_edits` entries containing the source
sequence path, canonical binding GUID and reviewed Blueprint profile. Older
documents normalize to an empty list. Validation rejects component bindings,
unknown profiles, missing/foreign bindings, duplicate entries and runtime-handle
fields. The immutable source digest is preserved. The cast page offers original,
Lune, Sciel and Verso choices, with Save and saved-document reload support.

Edited preview constructs the replacement under its owned sequence scope and
applies the binding before the first evaluation. When DuplicateSequence creates
several products, selection uses actual nested sequence membership and the
imported source MovieScene signature. Matching names or ownership alone are
insufficient; changed original signatures and ambiguous matches are rejected.
The existing source occurrence check also rejects reused shot instances.

In the isolated QA map, a saved Sciel replacement and one section edit previewed
together on a private Simon hierarchy, including the wide cast shot at frame
2100, then closed normally. A second edited preview using Verso also rendered
and closed normally in the same game process. Preparation measured **8463.2 ms**
and **13772.1 ms** respectively; dispatch performance is still unfinished.

The actual in-game cast controls selected Verso and saved it, removed the
replacement without saving, then restored Verso by loading the saved document.
The loaded document reported clean state and the saved sequence-local GUID.
Character actors now sort first, and the binding page shows concise shot,
Blueprint, component and track details instead of a long JSON dump.

This editor path currently admits one replacement per preview in the QA map.
The data format permits additional entries for future simultaneous ownership;
the runtime rejects them before preview construction instead of silently
dropping edits. Full cast ownership, curve playback, additional NPCs and faster
dispatch remain required. The full suite passes **2608 tests**, with six skips.

## Independent timeline actor ownership

Candidate v223 separates cinematic Blueprint actors from the session-wide enemy
owner. A dedicated channel admits construction, reveal and retirement only,
with 32 native token slots. Each slot reuses the original deferred construction,
strong retention, reveal and retirement journal. The native class admission still
requires the reviewed cinematic Blueprints and QA world. Encounter and owned
battle-arena channels keep their existing ownership slots and operations.

Reservations survive construction errors and uncertain results. Capacity
rejection is distinct from a duplicate token, and Python treats it as no native
work only after validating the exact rejection acknowledgement. Unknown results
remain owned. Native unresolved allocation blocks retirement; cleanup cannot
free a slot while its owner reports work. Session shutdown closes sequences
before timeline actors, then retires occupied slots in reverse order.

The SDK adapts the existing actor lifecycle onto this dedicated channel rather
than rebuilding actor components. Saved previews preflight their replacement
count against the actual capability and resolve source sequences before
constructing the first actor. Older runtimes still explicitly permit only one
replacement. The source signature lookup is shared for entries in the same shot.

In the isolated QA map, one edited Simon hierarchy replaced Lune with Verso and
Verso with Lune simultaneously. Both appeared in the wide shot; fresh retained
reads confirmed their actual Blueprint classes and independent scene-driven
root transforms. Preview cleanup succeeded. A second two-actor preview reused
the slots and also closed successfully in the same SDK session. Preparation
measured **11157.9 ms** and **11183.1 ms**; faster dispatch is still required.
The 32-slot capacity is covered by native fixtures; the in-engine test qualifies
two simultaneous replacements, not a 32-character animation compatibility claim.

The full Python suite passes **2612 tests**, with six skips. Native fixtures and
candidate build pass `/W4 /WX`. The known stale title-widget read still stops the
test SDK host when the QA map is opened directly from title without a save;
reattachment recovered the same running game. That transition issue is separate
from actor pool cleanup and remains unresolved.

## Retained selectors with fresh observations

Blueprint staging now retains one LocalPlayer selector under the sequence scope.
Each actor still obtains a fresh projected PlayerController reference and its
current world before and after construction. The retained selector replaces
repeated global LocalPlayer searches; it does not cache controller/world values
or authorize use after scope revocation. Inactive leases, incomplete projections,
wrong property types, foreign scopes and ambiguous players remain errors.

Portable binding queries and actor overrides also retain their fixed function
and POD metadata once per sequence scope. Native portable queries still validate
all identities, input leases and exact schemas before and after dispatch. Actor
override plans still rebuild fresh selected descriptors for each call. Neither
cache stores playback hierarchy membership, binding results or reusable mutation
authority.

Same-session comparisons used the unchanged installed implementation as a
baseline, then reversed the order. The first pair measured **17523.2 ms** versus
**15151.6 ms**; the reverse pair measured **17202.6 ms** versus **15078.1 ms**.
Actor preparation across both replacements fell from about 3.9 to 2.4 seconds,
and binding from about 3.8 to 3.0 seconds. These are matched observations, not a
latency guarantee. Reader-level instrumentation also included background
readiness monitoring, so those aggregate counters are not used as exclusive
preparation cost. A run overlapping the regression suite was excluded.

A further run received a read-only metadata rejection while scanning section
range-edit functions, before replacement construction. The command response
truncated the diagnostic; its exact cause remains unproven. Its partial preview
closed successfully, and a fresh independent optimized preview then prepared in
**15098.1 ms**, rendered both replacements and closed normally. No failed
mutation was replayed. This rejection and the title-transition issue remain
open; dispatch is still too slow overall.

The full suite passes **2617 tests**, with six skips, including selector freshness,
metadata reuse, fresh target-descriptor construction and inactive-lease checks.
