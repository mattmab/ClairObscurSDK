# Target-derived UMG layout values

2026-10-09; Steam build23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
The opt-in v11 backend implements this value contract with native schema checks.
It does not establish a rendered Mods Menu. Live results are recorded below when
available; offline tests alone do not prove engine behavior.

`scripts/inspect_widget_layout.py` reads live function descriptors and recursively
expands their struct references. On game PID 25560 it found all 27 requested functions,
with no missing names. Identity-selected descriptors corroborate these profiles:

| Struct path | Bytes | Exact reflected fields |
| --- | ---: | --- |
| /Script/CoreUObject.Vector2D | 16 | X:double+0, Y:double+8 |
| /Script/CoreUObject.LinearColor | 16 | R/G/B/A:float+0/+4/+8/+12 |
| /Script/SlateCore.Margin | 16 | Left/Top/Right/Bottom:float+0/+4/+8/+12 |
| /Script/Slate.Anchors | 32 | Minimum:Vector2D+0, Maximum:Vector2D+16 |

Each has no reflected superclass and no additional reflected fields. The schema
validator checks full package/type path, ScriptStruct class, extent, field count,
ownership, names, types, offsets, dimensions and nested identities. Reflection
does not itself prove arbitrary structs are trivial or callable. Only these four
profiles are candidates, supported by the target thunk evidence below.

## Executable evidence

Ghidra thunks `1430976a0` and `143097cf0` decode Vector2D for CanvasPanelSlot
SetPosition/SetSize, then narrow the two doubles into slot float storage.
GetPosition `143093ea0` and GetSize `1430940c0` widen the corresponding floats
back into a 16-byte double pair. The optional Slate update path operates separately
from that parameter storage. Consequently, the candidate codec rejects nonfinite
components and finite doubles beyond float range; it does not assume all finite
double values are safe inputs for UI setters.

Button.SetBackgroundColor `143095eb0` copies a 16-byte LinearColor into the button,
then updates its Slate representation when present. CanvasPanelSlot.SetOffsets
`143097160` copies the 16-byte Margin. SetAnchors `143095c60` copies 32 bytes for the
two Vector2D members. Their parameter paths show numeric copying without owned
string/object-pointer parameter state. Raw property mutation is not used.

The read-only dump also identifies boundaries requiring separate work:

- TextBlock.SetText accepts 16-byte TextProperty; this is not a Python string or
  a trivially copied text value.
- SlateFontInfo is 96 bytes and includes object references, FName and nested
  outline settings. It is deliberately outside the numeric profiles.
- SlateColor is 20 bytes with LinearColor and an enum; it is not interchangeable
  with LinearColor.
- UIOnlyEx/GameAndUIEx input-mode calls include an EnumProperty mouse-lock mode.
  Names/descriptors alone do not verify focus restoration or enum invocation.

## Implementation and next integration

Internal `_pod_values.py` validates observed profiles, packs exact named numeric
fields and decodes immutable copied results. `native/pod_value_codec.h` provides
the matching width/numeric validator; its standalone /W4 /WX fixture passes four
profiles and seven invalid-value/boundary cases. Python tests cover double versus
float encoding, nested values, immutable results, changed/owned/extra fields,
wrong nested identities, nonfinite values and narrowing overflow.
The complete source Python suite passes all 146 tests.

The codecs are connected to v11 invocation. `Session(pod_values=True)` selects
the separately named controller/runtime and requires `pod_value_protocol:1` in
the handshake. Call packet v2 preserves the existing byte layout, adds four
explicit kinds and stores the observed ScriptStruct identity in the constraint
slot. Older sessions reject v2. Both retained and ordinary calls share the same
validator; numeric structs acquire no native-owned storage or lease tokens.
Native schema rejection is not dispatched; invalid numeric results after a call
leave its outcome unknown and must not be retried. Existing object-output
retention and pointer scrubbing remain in place.

Python accepts exact named dictionaries or same-type NumericStructValue copies,
validates live descriptors, and returns immutable typed mappings. For example,
with observed slot/function identities:

```python
sdk.invoke(slot, set_position, InPosition={'X': 160.25, 'Y': 32.5})
position = sdk.invoke(slot, get_position).return_value
```

`launch.cmd management --pod-values` exposes this opt-in backend. The original
Harness's typed `$struct` adapter is now implemented; see INTROSPECTION_PORT.md
for its separate validation. Its core is unchanged. Arbitrary structs, FText/font/FKey ownership,
EnumProperty input modes and visible/focused menu behavior remain unsupported.

Native gate follow-up: `pod_schema.h` now implements the exact four-profile
walker; `target_pod_schema.h` supplies the real game-thread, GC/shutdown, registry,
name and local-memory operations. It verifies package/type identity, no inherited
or extra fields, field ownership, exact vtables/flags/types/dimensions/offsets,
and recursively checks Anchors' two references to the same Vector2D structure.
The parameter gate binds an FStructProperty's reference and width to that profile.
The enclosing invocation must still validate parameter ownership/layout and
contain access faults. No native constructor, setter or dispatcher is called.

`verify-pod-values.cmd` compiles the real adapter/template combination with
/W4 /WX and runs a synthetic-memory fixture through the actual schema walker.
Four valid profiles and parameter binding pass; 24 altered-schema, identity and
context cases are rejected. This is offline validation, not a claim that the
gate has run on the game's thread. Native packet tests cover explicit version
gating, zeroed outputs, identity/width checks and invalid numeric values. The
151-test Python suite includes cross-language packets for all four profiles,
return decoding, altered descriptors and pre-write capability rejection.

`scripts/verify_live_widget_layout.py` runs through the existing retained-child
lifecycle probe on the persistent owner thread, with no viewport or input change.
It checks position/size readback and margin effects, submits anchors/color, then
removes the child and compares the holder baseline. Dispatch-only color/anchor
results are explicitly distinguished from readback and rendered behavior.

## Live v11 result

2026-10-09 03:38:37 local, game PID 25560, persistent Python PID 8316 and native
controller PID 4152: the complete scoped probe passed. SetPosition/GetPosition
round-tripped `{X:160.25,Y:32.5}` and SetSize/GetSize round-tripped
`{X:640,Y:360}`. SetOffsets with `{Left:120,Top:80,Right:500,Bottom:300}` was
independently checked by subsequent position/size calls. SetAnchors and
Button.SetBackgroundColor returned from native dispatch; no rendered effect or
independent color/anchor readback is claimed. The child was removed, its count
returned to zero, and the exact native holder baseline was restored.

The v10 controller shut down cooperatively before v11 started; no second
persistent controller was attached. Native console Python dispatch and the
integrated mod host remained operational. Live evidence is
`evidence/widget-layout-live.json` and `logs/management-v11.stderr.log`.
The new pair is included by the packaging script. The later candidate20261009T075928Z
passed fresh-package startup after normal game exit/relaunch and the original
Harness's typed-value/lifetime specimen; see DEVELOPMENT.md for current evidence.

Clean-source package check: candidate `20261009T074043Z`, source `9b5ee40`,
contains 226 manifest-hashed files including both v11 binaries. Directory and ZIP
hashes all match; logs, settings and raw evidence are excluded. ZIP SHA256:
`e6da3c689328b43f1f96922df5f4fa01c5179ee86440c05d074bc14311d8ff2c`.
Isolated CPython 3.13.15 loaded the bundled SDK and ran 151 tests successfully
(two native-fixture tests skipped because fixture executables are not bundled).
This is packaging/integrity validation, not live startup from that bundle.
Evidence: `evidence/pod-v11-package*.json` and `pod-v11-package-tests.log`.

Local raw evidence: `evidence/widget-layout-schema.json`,
`evidence/widget-layout-schema.log`, `evidence/widget-layout-thunks.json` and its
argument/tool files. No functions discovered during this inventory were executed.

## Visible native control specimen

At 03:57–03:58 local on 2026-10-09, game PID25560 and the existing persistent
v11 host PID28004/controller39856 ran `verify_live_widget_visible.py` through
native-console Python. It created a UserWidget, its owned tree, a CanvasPanel,
a disabled Button and a retained CanvasPanelSlot. It assigned RootWidget through
the verified engine setter and added the UserWidget at viewport ZOrder1000.

The slot read back position80,80 and size420,160 with zero anchors. Computer-use
screenshots showed a blue-gray rounded rectangle at approximately85,85 through
533,255 in the2048x1152 game window, consistent with the viewport's UI scaling.
The control was absent before the probe and after automatic removal. This is
visual rendering evidence; exact pixel color, hit testing and focus were not
measured. The button was disabled before attachment, no action was registered,
and no input-mode or focus-setting call was made.

The30-second observation delay ran only in external Python. On completion,
IsInViewport returned false, RootWidget read back None, canvas child count returned
to zero, and the native strong-holder map exactly matched the initial baseline.
All mutations returned known outcomes. Game/controller/host remained running.
Raw evidence: `evidence/widget-visible-live.json`, the separate visual observation
record `evidence/widget-visible-observation.json`, and
`logs/management-v11-harness.stderr.log` at03:58:15. Screenshots were inspected
directly in the tool output. No new menu or persistent viewport element remains.

This establishes rendered native widget composition using the reusable SDK
primitives, not a usable Mods Menu. Text/font ownership, actions, enum input modes,
focus restoration and key dispatch remain open.

Additional static evidence in `evidence/widget-text-enabled-thunks.json`:
SetIsEnabled thunk1431064d0 decodes the reflected bool and calls widget virtual
slot2c0. TextBlock.SetText thunk14310b570 initializes a local value through
1410a2cc0, decodes TextProperty and calls widget virtual360; its non-null text data
is passed through virtual calls at+8 and+10 around that operation. These lifetime
operations reinforce the ownership boundary: a16-byte FText is not a numeric POD
or raw Python string. Constructor, copy and destructor semantics still require
independent verification before a reusable owned text API can be implemented.

## Owned text API investigation

Read-only `inspect_widget_text.py` found four exact descriptors on fresh game
PID12912; none was executed. `widget-text-schema.json` records their identities,
parameter flags, offsets and types:

| Function | Entry VA | Parameters |
| --- | --- | --- |
| TextBlock.GetText |1430ff930| TextProperty return at0,16bytes |
| TextBlock.SetText |14310b570| TextProperty input at0,16bytes |
| KismetTextLibrary.Conv_StringToText |143289f40| StrProperty input at0; TextProperty return at16;32bytes total |
| KismetTextLibrary.Conv_TextToString |14328a000| TextProperty input at0; StrProperty return at16;32bytes total |

The correlated target code in `widget-text-conversion.json`,
`widget-text-constructor.json` and `widget-text-value-paths.json` establishes these
static observations, not a validated callable SDK ABI:

- Default text initializer1410a2cc0 obtains a shared value from1410baed0,
  invokes its virtual+8 when non-null and sets the value's flag word to zero.
  The shared getter has guarded initialization and exit cleanup registration.
- Getter1430ff930 obtains the text from the widget or its Slate representation,
  invokes virtual+8, transfers it through1410a65f0 and invokes virtual+10 on
  the remaining local value. A read is therefore not just a16-byte copy.
- Transfer1410a65f0 moves the data pointer, invokes virtual+10 on the destination's
  former value, copies flags and restores the source to the default shared value.
- String-to-text goes through1438074a0 to1410add50; its thunk releases its local
  text value and frees its local string through14107c7d0.
- Text-to-string calls1410bab10 then string-copy helper141027170. Its thunk moves
  the resulting string allocation into the result, clearing the source fields,
  and releases temporary text/string state.

Next verify1410add50/1410bab10/141027170, allocator/free contracts and property
initialization/destruction paths. A reusable implementation must materialize and
destroy native parameters on the game thread, copy only bounded textual results
back to Python, and explicitly own any retained native text. It must preserve
unknown-outcome handling and avoid retrying calls after ambiguous dispatch.
No text/font support, string conversion or label rendering is claimed yet.

## Candidate owned-text lifecycle helper

Further target inspection resolved the ownership operations. Assembly1410add50
takes the result inRCX and a borrowed FString view inRDX, copies all UTF-16 units
through engine string allocation, publishes one owned text reference and sets
flag bit2. It does not retain/free the input view. String-copy141027170 also uses
the engine allocator; free14107c7d0 calls the active allocator's virtual48.

The text-data vtable146da8c78 has add-reference1410acdb0 at+8 and release1410cbce0
at+10. The former atomically increments data+8; the latter atomically decrements
and calls deleting destructor1410abe30 when the former count was1. That destructor
cleans its display/source string allocations through engine free and then frees
the data allocation when requested. Virtual+28,1410baa50, returns a borrowed
display-string header;1410bab10 performs the engine refresh before that access.
`owned-text-core.json`, `owned-text-vtable.json`, `owned-text-abi.json` and
`owned-text-lifetime.json` preserve the correlated code and assembly.

`native/owned_text_value.h` now supplies a reusable candidate storage/lifecycle
helper. It is non-copyable, has no native-calling C++ destructor and requires
explicit game-thread release. The constructor accepts at most4096 UTF-16 units
including NUL; it rejects embedded NUL, unpaired surrogates and oversized input.
Reads return bounded copies and never a target pointer. Empty engine strings are
normalized to a single terminator; malformed headers, unreadable content and
insufficient output capacity fail without publishing a partial result.

Construction, display refresh and destruction each mark storage uncertain before
calling the engine. A fault leaves it quarantined: create/read/release cannot
silently retry. A wrong-context release defers while preserving ownership.
The containing native session must own this storage before calling the helper,
keep it alive after faults, verify the fingerprint and supply its SEH boundary.
`target_owned_text.h` checks thread/GC/shutdown state and the exact target vtable
and known lifetime methods. It accepts only the verified base text-data type
with default flags0 or FromString flags2; creation separately requires flags2.
Arbitrary localized/history implementations remain unsupported.

`verify-owned-text.cmd` passes43 input/copy/context/lifetime/fault checks and
compiles the actual target adapter/templates with MSVC/W4/WX. The fixture injects
faults after allocation and after release to check the no-retry boundary, and
tests unexpected constructed types and copied input independence. Evidence is
`evidence/owned-text-native-tests.log`. These are offline tests; no text value
was constructed in the game and the running v11 DLL was not rebuilt or changed.

Next integrate durable text storage and bounded wire strings with reflected-call
parameter construction, result copying and cleanup. Gate it behind a new native
capability, retain v11 compatibility, and validate a live Unicode/empty/invalid
input round trip before TextBlock labels. Generic TextProperty output adoption
still needs its own lifetime/type validation; this helper alone does not provide
Harness text invocation, text retention or a functioning Mods Menu.

## Candidate text invocation envelope

`native/text_call_protocol.h` and private Python `_text_wire.py` now define a
separate91800-byte envelope around the unchanged retained-call packet. Inner
call version3 identifies TextProperty kind13; v11's validator rejects it.
Each of at most eight scalar TextProperty fields has its field index, unit count
and4096-unit UTF-16 buffer. Native16-byte parameter slots remain zero on the wire.
Input fields require a valid terminated copy; output fields start empty. Unused
slots/padding must be zero, field order must match, and pointer-shaped native
values are rejected. There is no arbitrary struct/string pointer serialization.

The pure native validator normalizes text to zero integer storage only to reuse
existing overlap/scalar/object/POD checks, separately checking text return offset
and count. That normalized copy is never an executable plan. Integration must
validate the real TextProperty metadata/vtable on the game thread and construct
owned native parameters in durable session storage before dispatch.

Python reply decoding correlates the exact call and text-field records, rejects
raw native text bytes, validates UTF-16/termination/padding and preserves the
existing object-output lease checks. Error/unknown outcomes expose no copied text
or raw result bytes. Input-only text cannot silently change. Text results are
Python string copies, not retained localized native FText handles.

The native fixture passes22 envelope checks plus the explicit v11 rejection;
the existing43 ownership checks and target-adapter/W4/WX compile still pass.
All163 Python tests pass, including actual Python-generated packet validation
by the native executable, supplementary Unicode, empty/maximum values, corrupt
responses, eight-field bounds and coexistence with required object-return leases.
Evidence: `evidence/text-call-native-tests.log` and
`evidence/text-wire-python-tests.log`. The test fixture was adjusted to avoid
repeated large stack temporaries; the eventual runtime must keep its envelope
and ownership records in durable session storage.

This remains a transport prerequisite, not an enabled capability. The public
planner/session still reject text invocation; no new session handshake, controller
command or game-thread text dispatcher is installed. The current v11 game and
packaged console host remain running unchanged. Next connect the envelope to a
new explicit capability, ownership-aware dispatch and cleanup, then validate live
round trips and native TextBlock labels against this build.

## Durable text call frame and dispatcher integration

The candidate now has a session-owned `TextCallFrame` and an optional explicit
`CallTextHandling` path in the actual reflected dispatcher. Before construction,
the dispatcher validates the complete live function/property schema, including
the exact TextProperty vtable at RVA6e1ba00, scalar dimension and16-byte width.
After construction it rechecks target/function/object identities and the
game-thread/GC/shutdown context before dispatch. Existing callers supply no text
table and continue to reject the version3 envelope.

Input and output text slots are initialized with owned values. Ownership moves
into the durable argument buffer before dispatch and is adopted back only after
a normal engine return. Native text bytes are scrubbed before publication. Text
display values are copied into bounded staging buffers and become publishable
only after all native text references were released. A dispatch fault preserves
the uncertain argument frame; construction/read/release faults preserve their
individual ownership state and forbid retry or reuse. Invalid cleanup context
defers release. No destructor calls the engine implicitly.

`TargetTextCall` supplies the target callbacks but is not yet instantiated by
the runtime. Integration must keep it alive in native session storage, attempt
cleanup on every normal early failure, contain SEH faults, and prevent reuse or
unload while ownership is deferred/uncertain. No controller command, handshake,
public planner support or live text call is claimed by this checkpoint.

Offline validation passes43 primitive checks,22 envelope checks,34 frame
ownership/fault checks,7 actual dispatcher capability/quarantine gates, and13
checks of the actual target type predicate against synthetic memory. The target
adapter and v5/v11 runtimes plus v11 controller compile with MSVC/W4/WX; compile
outputs are isolated and do not replace the running package. All163 Python tests
pass, including the native cross-language envelope fixture. Evidence:
`evidence/text-frame-native-tests.log`, `evidence/text-frame-compatibility.log`,
and `evidence/text-frame-python-tests.log`.

Next wire the durable context into a separate session capability and the existing
Python planner/transport, validate Unicode and empty text round trips live, then
render native TextBlock labels. These fixtures prove ownership bookkeeping and
rejection behavior; they do not prove live FText output lifetime or menu behavior.

## Candidate v12 native session and controller

`E33_TEXT_SESSION` now requires the complete v11 capability chain, adds
SessionTextInvoke106 and advertises text_value_protocol1. It uses its own
E33SDK.Session.v12 message, E33Session12 mapping name and isolated DLL/controller
paths. `build-text-candidate.cmd` builds these artifacts without replacing v11.
The appended text envelope uses the old struct's four bytes of tail padding;
compiled layout fixtures verify existing field offsets, envelope size and final
alignment rather than assuming an append offset from the old total size.

The backend copies the wire envelope into module-owned storage before invoking
the guarded dispatcher. The native argument frame never lives in shared mapping
memory. Every normal/error/SEH result attempts explicit guarded cleanup. An empty
or fully cleaned frame can reset; deferred ownership prevents another text call
and close retries on the game thread. Uncertain ownership remains bounded in the
pinned module and rejects later text calls and session reopen. Terminal shutdown
does not guess a destructor or reuse those records. Existing lease and console
cleanup still run after text cleanup, except while a valid release is deferred.

The controller encodes/decodes the full bounded envelope. Python's internal
transport requires the full advertised capability chain and exact version/size
before sending a text command; malformed or mismatched acknowledgements retain
the existing abort/owner-watcher behavior. Public Session and invocation planning
have not opted in yet. No candidate DLL has been loaded into the game.

Both candidate artifacts build with/W4/WX. v5/v11 compile compatibility passes.
All167 Python tests pass, including the compiled v11/v12 layout comparison,
missing-capability rejection, payload version/size rejection and acknowledgement
mismatch handling. Evidence: `evidence/text-session-build.log`,
`evidence/text-session-compatibility.log`, `evidence/text-session-python-tests.log`.
These checks do not constitute live session/cleanup validation. Next connect
public planning/result decoding and the persistent management host, then perform
a cooperative handover and bounded live text round trips before native labels.

## Public text API and live original Harness validation

2026-10-09 08:52:18 local: `Session(text_values=True)` and the scoped
`invoke_retained` path passed against game12912, Python37296 and native
controller36608. The launcher accepts `management --text-values`; plain
`invoke` keeps its earlier boundary. Plans store immutable copied string inputs
separately from zeroed native slots, and result decoding requires exact text-field
correlation. Native text arrays remain unsupported. All173 Python tests pass,
including public planning, result correlation, capability handshake, scope usage,
unknown-outcome abort and original-core provenance.

The previous packaged v11 controller shut down through `mods action shutdown`
at08:48:58; its processes exited before v12 started at08:49:20. The bounded probe
ran through the existing native console and persistent Python session. It created
an SDK-owned TextBlock and round-tripped `SDK text`, `Expedition 33 — café 🚀`
and the empty string via TextBlock.SetText/GetText. Embedded NUL, an unpaired
surrogate and overlength input were rejected in Python before dispatch.

The original Harness then set/read text, retained the copied result by name,
changed the widget value, restored it through `$value`, and released the retained
name. Reuse after release raised KeyError. Its original core is unchanged.
The shared widget probe removed its child and released the scope; the exact
holder baseline was restored. No viewport attachment, focus/input change or
forced GC occurred. The game and persistent v12 host remained running afterward.

Raw evidence: `evidence/widget-text-progress.json`, `evidence/widget-text-live.json`,
`logs/text-v12-source.stderr.log`, and `evidence/text-public-python-tests.log`.
The initial nested layout record's passed=false was copied before outer cleanup;
the outer passed=true and holder_baseline_restored=true are the completion
results. The probe now omits that ambiguous nested completion field.

This proves the verified base-text ownership path on SDK-created objects, not
arbitrary localized/history implementations, TextProperty assignment, native
text-handle retention or a visible menu. Next render a TextBlock label, validate
v12 packaging/relaunch/cleanup, and continue input/focus and menu actions.

## Visible native text specimen

2026-10-09 08:58:56 local: the persistent v12 host completed the extended visible
widget specimen. An SDK-created TextBlock rendered two readable lines,
`Expedition 33 SDK` and `Python to native UMG`, inside the disabled blue-gray
panel. Both controls used their engine-provided defaults except the previously
verified layout/background values and copied text. No font/style ownership API
was assumed. Screenshot observation at2048x1152 placed the panel approximately
at(85,85)-(533,255), with both text lines fully visible. The native console was
closed during the observation.

GetText returned the exact two-line string after AddToViewport had created the
Slate representation, exercising that getter branch as well as the earlier
unrendered case. The45-second observation delay ran in external Python. Cleanup
then removed the viewport entry, restored RootWidget toNone, removed the label
and button, verified zero children and restored the exact holder baseline. A
second screenshot confirmed the panel and label were gone. Input mode and focus
were not changed; click handling and general keybinds were not tested.

Evidence: `evidence/widget-visible-text-live.json`,
`evidence/widget-visible-text-observation.json`, and the08:58:56 entry in
`logs/text-v12-source.stderr.log`. `verify_live_widget_visible.py` preserves the
older no-label specimen and accepts an optional label_text for this v12 path.
The package manifest now includes the v12 controller and DLL; isolated package
and relaunch validation remain separate gates.

Fresh-game package follow-up: at09:08:06 local the isolated v12 candidate passed
the original Harness copied-text specimen after a normal source-game exit and
Steam relaunch. The loaded DLL and Python import both came from the candidate.
Unicode/empty round trips, invalid-input rejection, retained text reuse/release
and exact holder cleanup passed. See DEVELOPMENT.md and
`evidence/text-v12-package-relaunch.json`. This run did not display widgets or
change focus/input mode; the visible-label proof above is from the source run.

## Input-mode prerequisite investigation

Read-only Ghidra follow-up (`evidence/input-mode-enum.json`) corroborates the
archived reflected schemas for GameAndUIEx (RVA31401e0), UIOnlyEx (31405c0) and
GameOnly (31404c0). Both widget-bearing thunks read a one-byte mouse-lock argument
and obtain a Slate shared reference through RVA30f7f70 when the widget is nonnull.
They construct different input-mode objects (vtables73c0e88/73c0e70 respectively)
and invoke the player controller's virtual slot+d48. Their flush flag separately
controls virtual slot+d90. GameOnly uses vtable73c0ea0. These are static target
observations, not live invocation or a reversible input-state contract.

The enum type-formatting path at RVA12aa430 independently reads the referenced
UEnum from EnumProperty+78, corroborating the external descriptor reader. Live
schema previously identified EMouseLockMode and a one-byte ByteProperty child.
Member/value decoding subsequently passed live through the read-only API recorded
in REFLECTION.md: DoNotLock0, LockOnCapture1, LockAlways2, LockInFullscreen3 and
the generated MAX4 entry. Game-thread enum identity validation and the call codec
remain missing. Do not pass an untyped zero or bypass the EnumProperty gate.
Before changing focus, identify the active CommonUI ownership/context and how to
restore that context without forcing GameOnly over an existing game menu. The
console dump's registered CommonUI diagnostics remain unexecuted candidates.

The original Harness now exposes these members through its existing schema
request; its read-only live input-mode schema test passed (INTROSPECTION_PORT.md).
A candidate `native/enum_schema.h` checks scalar byte-backed EnumProperty,
underlying field ownership/type/width, exact native UEnum identity/type, member
bounds and numeric membership, with game-thread/GC/shutdown context checks.
It shares the existing target read adapter and performs no engine calls or writes.
Its actual template passed24 hostile-memory/context/identity fixture cases and
compiled with/W4/WX (`scripts/verify-enum-schema.cmd`). It is not yet connected
to a call packet, session capability or live dispatch. Membership includes
sentinels and is not sufficient caller policy; the eventual Python/wire layer
must preserve explicit enum identity and reject unsupported argument semantics.

Candidate enum planning/wire follow-up: `prepare_call(..., enum_values=True)`
now produces version4 only for scalar byte-backed EnumProperty parameters. Inputs
require a copied `EnumValue` from the exact enum identity and a current member
name/value match; raw integers, stale identities, out-of-range values and `_MAX`
sentinels (including numeric aliases of sentinels) are rejected. Output decoding
returns typed copies and rejects values outside the observed member set. Names
are not assumed unique by numeric value; output aliases use the first observed
name. A decoded sentinel cannot subsequently be supplied as an input.

`_enum_wire` retains the existing26,192-byte ownership envelope, with inner
version4/kind14 and enum identity in the constraint slot. The pure native
`enum_call_protocol.h` validator checks the new shape using a validation-only
copy; that normalized copy must never be dispatched. Existing sessions/codecs
reject version4. Mixed text/enum calls remain gated pending transport integration.
No Session capability or actual enum dispatcher has been enabled yet.

All182 Python tests pass. Native schema checks still pass24 adversarial cases;
six malformed packet cases and rejection by the legacy validator also pass.
`verify_live_enum_plan.py` read GameAndUIEx's actual19-byte parameter schema from
game21804, created a typed DoNotLock plan, and sent the exact Python packet to
the compiled pure native validator. It accepted the packet without game dispatch.
Evidence: `enum-live-plan.json/.bin`, `enum-invocation-python-tests.log` and
`enum-schema-fixture.log`. This is live-metadata planning plus offline wire proof,
not proof that input mode or focus changed. Next connect an isolated session and
the game-thread validator, then validate bounded calls and context restoration.
