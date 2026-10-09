# General trace frame investigation — 2026-10-09

Target: Steam build23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
Addresses below are Ghidra image addresses, not ASLR runtime pointers.

The original BL4 core requires exact-function POST hooks, optional target filters,
copied arguments and return values, sixteen trace slots, bounded event counts,
expiry, stop and forget. The existing E33 observer cannot satisfy this: it owns
one immutable native entry/slot, filters one Actor identity, and copies one bool.
The Harness correctly excludes trace_start/read/stop from its supported set.

## Assembly-backed layout findings

Fresh read-only Ghidra MCP disassembly was preserved in
evidence/trace-frame-dispatch.json, trace-frame-invoke.json and
trace-getter-thunk.json, with corresponding argument files and logs. These
corroborate earlier decompilation in invoke-dispatch-paths.json. Ghidra returned
296 instructions for dispatcher141393330; no runtime hook was modified.

Dispatcher141393330 constructs its frame at RBP+20 and passes that address in R8
at1413936b0 to helper141280940. RSI holds the UFunction, R15 the object, R12 the
caller parameter buffer and RDI the allocated/reused local parameter buffer.
Relative offsets follow from these actual stores, not a stock Unreal header:

| Relative frame offset | Observed role | Assembly evidence |
| --- | --- | --- |
| 10 | initial function |141393542 stores RSI at RBP+30 |
| 18 | object |141393546 stores R15 at RBP+38 |
| 20 | code pointer |141393529 reads function+60;141393538 stores at RBP+40 |
| 28 | local buffer |14139354d stores RDI at RBP+48 |
| 80 | out-parameter chain head |141393579 zeroes RBP+a0;1413935c2 selects that location for chain construction |
| 88 | property-chain cursor |141393516 reads function+50;141393580 stores it at RBP+a8 |
| 90 | current function during invocation |14128099c saves frame+90;1412809a9 stores function;1412809c3 restores old value |

The role names are interpretations of data flow. Their offsets are established
for this dispatcher and helper, not every potential frame construction path.
Live frame capture and alternate call paths still require corroboration.

Helper141280940 calls function+d8 at1412809b3 with object in RCX, the unchanged
frame pointer in RDX and the supplied return pointer in R8. Its preceding code
can adjust the object context through1413b22d0. Therefore an observer must validate
the actual thunk context rather than assume it always equals frame+18.

The known Actor getter thunk14333be80 reads and conditionally advances frame+20,
then writes its bool through the independent result pointer in R8. It does not
read or write the return slot in frame+28. Dispatcher141393698..1413936ad computes
that result pointer from the caller's buffer plus function ReturnValueOffset+b8
(ffff means absent). This is concrete evidence against decoding all POST results
from frame locals alone.

For out parameters,1413935ed..141393618 constructs records containing property
at+0, caller-buffer address at+8, next at+10. The chain is rooted at frame+80.
Post-call copying must account for those external addresses and property flags;
a single memcpy of local parameters is not a verified general trace codec.

## Implementation consequences and remaining proof

Build a versioned observation backend with immutable per-function forwarding
slots and bounded copied event storage, preserving existing late-fetched-pointer
and compare/exchange removal rules. Multiple trace subscriptions must not mutate
an original entry pointer still reachable by an earlier caller. Controller loss
must detach event storage independently of whether an engine slot remains valid.

Before publication, validate function identity, declaring class, current entry,
parameter metadata and the complete supported copy schema on the game thread.
Capture current-function identity separately from initial frame identity; do not
read unsupported or inconsistent frame paths. Keep original execution outside
the event-storage lock. Do not call Python from a native thunk.

Verify a nontrivial input, separate return storage and an out/ref parameter using
captured live frames before adopting these offsets in a generalized decoder.
Bytecode-originated calls, nested calls, object lifetime during delivery,
non-game-thread calls and owned strings/containers need explicit handling.
Copied object identities must never be presented as GC-pinned handles. Expiry,
event caps, overflow, removal conflicts and reconnect/relaunch need tests before
enabling the original trace operations. No general tracing capability is claimed
by this investigation, and the original core remains unchanged.

## Bounded native copy primitive — 2026-10-09

native/trace_copy.h now provides allocation-free copying from separately acquired
local, result and out-storage views into an owned4096-byte record, with at most
128 fields and130 sources. It validates every field before reading source bytes,
rejects source/destination overflow and overlapping destination ranges, zeroes
padding and clears prior output on failure. It retains no source pointers.
Callers must supply valid readable views that do not alias the output; it does
not dereference FFrame offsets or catch invalid native memory access.

The C++ fixture deliberately places different values in locals, out storage and
result storage and verifies the copied event uses the specified sources. Mutating
all source buffers after capture leaves the event unchanged. Boundary checks cover
null sources, source-count/field-count/extent limits, integer overflow, zero-size
fields, overlaps and failure after an earlier valid field. Compiled with MSVC
/W4 /WX and executed successfully via scripts/test-trace-copy.cmd; raw build/run
output is evidence/trace-copy-fixture.log.

This is byte-copy plumbing, not a reflected value codec. Bit-packed bool fields
sharing bytes must be normalized before this API (overlaps are deliberately
rejected). Engine-owned strings, containers and pointers must not be sent as raw
values; schema-specific copying and object identity conversion are still needed.
No live frame was read, no trace hook was installed, no resident DLL was replaced,
and Harness trace operations remain unavailable. Next work is immutable observer
slots and game-thread schema/frame validation followed by live capture proof.

## Immutable observer-slot lifecycle fixture — 2026-10-09

native/trace_slots.h adds a candidate pool of distinct native thunks with immutable
original function pointers. The default supports16 simultaneous registrations
and128 lifetime slots per module. Published slots are never reassigned, including
after removal; late callers cannot reach a later registration's event context.
Failed publication can also consume a slot. Exhaustion currently returns failure
and must become an explicit transport/API diagnostic rather than silent reuse.

Installation pins the containing module, publishes the original before the thunk,
and uses compare/exchange against the expected function entry. Original execution
runs outside the storage lock. POST delivery checks registration state again under
the lock, so removal during the original call suppresses the pending observation.
The POST collector must do bounded copying only, never engine/Python calls or
registration operations while holding that lock. Normal remove detaches context
regardless of slot conflict and never overwrites a third-party entry. Terminal
storage detach touches no engine address and permanently prevents new installs.

scripts/test-trace-slots.cmd compiles with /W4 /WX and runs a C++ fixture covering
two independent functions, active limits, a retained old callback after replacement,
concurrent in-flight removal with the original blocked on another thread, external
entry conflict, terminal detach with a callback still published, and lifetime
exhaustion. All passed; raw evidence is evidence/trace-slots-fixture.log. This is
an executable fixture, not code installed in the game. No resident DLL changed.

The runtime adapter must still validate target/function identities, entry ownership,
game-thread mutation and slot lifetime before install/remove. The pool does not
establish those facts or decode FFrame. A function-identity/schema layer, bounded
event queue, versioned transport, live frame proof and Harness integration remain
required. Multiple subscriptions to one function also need coordinated ownership;
the current primitive rejects a second active registration at the same address.

## Composed native event delivery — 2026-10-09

native/trace_events.h adds a mutex-protected, fixed-capacity, one-registration
queue. The default retains64 copied records, each with at most4096 payload bytes.
It owns all record bytes, clears payload tails and rejects invalid object identity
shapes, wrong thread IDs, stale session/registration tickets and invalid sizes.
It retains no engine pointers. Runtime identity validity remains an adapter duty.

Stop preserves queued events for the original Harness trace_read-after-stop
behavior. Close clears data and revokes the ticket permanently; a queue cannot
be reopened for a later registration. Expiry is checked on offer and status, with
an upper duration of300seconds and maximum observation count1000. Overflow drops
new arrivals, increments a dropped counter and leaves visible sequence gaps.
The native observation budget counts dropped arrivals too, bounding activity;
the eventual Harness adapter must distinguish observed/dropped/delivered counts.
A capped/expired queue stops accepting data but does not itself restore the thunk;
the owning game-thread adapter must remove that registration.

scripts/test-trace-events.cmd compiled under /W4 /WX and passed an executable
fixture. It covers wraparound, overflow, caps, deadline boundaries, stale tickets,
zeroed payload tails, permanent close and stop retention. A composed test installs
an actual fixture thunk through TraceSlots, copies its separate return value using
trace_copy, offers it to Events, and drains it. A foreign-thread call still forwards
to the original function but contributes no event; a stale thunk after removal
also forwards without adding data. Evidence: evidence/trace-events-fixture.log.

No game-memory frame access or live hook installation is claimed. These candidate
primitives still require reflected schema/value codecs, identity/lifetime checks,
versioned runtime transport and original Harness integration. Lock order is slot
storage then queue; queue operations must not call back into slot registration.
The callback must be detached before destroying its stable queue/context owner.

## Reflected scalar trace planning — 2026-10-09

src/expedition33/tracing.py now prepares immutable observation-only trace plans.
Invocation parameter metadata validation was extracted into a shared helper,
preserving its existing width, overlap, ownership and return-offset checks.
Trace planning routes normal parameters to locals, out/ref parameters to separately
resolved out records, and return parameters to the independent result pointer.
Fixed arrays expand into bounded elements. Packed booleans receive independent
capture destinations with explicit masks, avoiding byte-overlap in trace_copy.

This initial schema supports the existing scalar numeric/bool codecs. Object/class
fields explicitly require a trace-specific identity codec; other owned values
remain rejected by shared schema validation. Native functions are required, with
bounded image RVA, parameter size, normalized fields and capture bytes. A plan
has no native registration authority and does not establish a readable frame.

All352 source tests pass, including existing invocation regression tests and new
trace routing, packed-bool, array, overlap, return metadata, bytecode and pointer
rejection checks. Evidence: evidence/trace-schema-tests.log.

Read-only live verification on game39900 passed via
scripts/verify_live_trace_plans.py. Observed specimens:
- Actor:IsActorBeingDestroyed, index10700, RVA333be80: one return byte.
- Actor:SetActorTickEnabled, index10764, RVA333fe80: one local bool input.
- PlayerController:GetViewportSize, index17940, RVA3b26b70: two separately resolved
  int out records, SizeX and SizeY, normalized into8 bytes.

Raw identities/layout plans are in evidence/trace-plans-live.json and its log.
No functions were executed or hooks installed. These are metadata-backed storage
plans, not proof of observed frame addresses or general tracing functionality.
Native schema revalidation, frame/out-chain resolution, transport, value decoding
and Harness wiring remain pending. The current packaged controller is unchanged.

## Native out-record resolver candidate — 2026-10-09

Fresh disassembly of GetViewportSize (143b26b70) and its native property helper
(141395250) confirms the separate out-record route. The helper tests property
flags at +38 bit8; for an out property it searches frame+80 by exact property
pointer, follows record+10, and writes record+8 to frame+38. For a normal property
it uses frame+28 plus the signed property offset at +44. GetViewportSize selects
the helper's frame+38 address for each int destination. These are executable
observations; no claim is made that arbitrary bytecode frames share the route.
Raw disassembly: evidence/trace-viewport-thunk.json and trace-native-step.json.

native/trace_frame.h is an isolated, build-specific resolver candidate using an
injected bounded reader. It requires the expected current function at frame+90
and a null code pointer, retains separate locals/result addresses, and snapshots
at most128 out records. Cycles, duplicate property records, null record members,
unreadable ranges and address overflow fail closed, clearing the entire output.
Missing out properties return unavailable, with no fallback to locals. A null
result is preserved as unavailable; the future schema-aware collector must reject
it when a return field needs storage. Resolved addresses are ephemeral internal
data, not copied event payloads or proof of readability/lifetime.

scripts/test-trace-frame.cmd passes under MSVC /W4 /WX, exercising separate
sources, identity and bytecode gates, malformed chains, overflow, missing output
storage and the record cap. Evidence: evidence/trace-frame-fixture.log. This is
synthetic fixture validation only. Live frame capture, schema-aware bounded reads,
native registration/transport and Harness integration remain pending. No mapped
DLL was rebuilt and the running controller was unchanged.

## Frame-to-payload capture and Python decoding — 2026-10-09

native/trace_capture.h connects resolved storage to an owned Copy payload using
an injected safe reader. The collector validates all field ranges, destination
overlaps and address arithmetic before reading. Out fields resolve exact property
pointers; missing out/result storage is rejected. No raw pointer is dereferenced
by this component. Failed reads, including readers that partially write before
failure, never publish a prefix. Padding and unused payload bytes remain zero.
The caller must independently validate scalar types, reflected property identity,
thread ownership and lifetime; bounded copying alone is not that authority.

The capture fixture composes resolve_frame, capture_fields and Events: independent
local/out/result values survive erasure of the synthetic source memory. It also
checks missing storage, wraparound, overlap, invalid source selectors, short
source extents and partial-reader failures. scripts/test-trace-capture.cmd passes
MSVC /W4 /WX; evidence/trace-capture-fixture.log records the run.

Python decode_trace now converts the matching registration plan and owned payload
into immutable named POST arguments and a return value, including fixed scalar
arrays and packed booleans. Invalid bool encodings, mutable buffers and wrong
payload extents are rejected. Transport/session matching remains a separate gate;
this function does not authenticate an event. All354 source tests pass, including
the existing invocation/lifecycle suite (evidence/trace-capture-tests.log).

Runtime integration inspection confirms SessionEnable/Disable/Drain still use the
old fixed observer and backend_close only removes that observer. These primitives
are not yet wired into the live runtime or original Harness. The next integration
must introduce a versioned registration/drain path plus close/expiry ownership,
and independently revalidate schemas before publishing any thunk. No live trace
capture, general trace API parity or relaunch proof is claimed by these fixtures.

## Native schema revalidation adapter — 2026-10-09

target_trace_schema.h now reuses reflected_call's validate-only branch. That
branch checks the live function/object identities, owner relationship, dispatcher,
native entry, flags, parameter extent, and ordered property names/types/layouts;
it returns before ProcessEvent or ownership callbacks. Trace preflight rejects
non-scalar kinds, object patches, nonzero argument bytes and the observed GC-state
flag. The guarded wrapper clears the plan on an access exception. This adapter
requires a compatible exemplar object for validation; that exemplar is not
implicitly the optional trace target filter. Registration must retain that choice
separately and verify observed object identity before publishing an event.

After preflight, the target walks the bounded live property list and passes those
property addresses to trace_plan.h. No controller-supplied capture address is
accepted. The pure normalizer derives local/out/result extents and flattened
fields, including separate destinations for shared packed-bool bytes. Duplicate
properties, non-native/invalid entries, non-observation payloads, unsupported
pointer codecs and more than128 normalized fields are rejected.

scripts/test-trace-plan.cmd compiles the actual target adapter with the production
validator and runs the pure normalization fixture under /W4 /WX. It covers scalar
routes, array offsets, packed bools, a structurally valid but unsupported object
schema, and a valid reflected schema exceeding the flattened field limit. Evidence:
evidence/trace-plan-fixture.log. Compilation is not live validation. The adapter
is not yet connected to SessionPacket or hook registration; per-registration
lifetime ownership, transport and live/relaunch checks remain required.

## Registration ownership candidate — 2026-10-09

trace_registration.h composes immutable slots and bounded events under a
nonmovable, one-registration owner. Foreign-thread calls forward without capture.
Game-thread stop restores the entry only when its caller establishes storage
lifetime, and retains queued events for a later drain. Scheduler maintenance
removes expired/capped observers outside the POST callback's slot lock. The
callback never recursively removes its own hook. Collector C++ exceptions are
counted as rejected observations; production target readers still require SEH
guards. Capture failures are separate from queued/overflow counts.

TraceSlots now supports individual callback detachment without reading an engine
entry. A lifetime-loss close uses that path, and destructor fallback also detaches
before releasing the queue/context. This prevents freed callback storage but is
not a successful entry restoration: cleanup explicitly distinguishes restored,
conflict, storage_lost and wrong_thread. A third-party replacement is preserved.
An inert late thunk permanently forwards to its original function, following the
pool's existing no-reuse policy. Explicit close remains the normal lifecycle.

scripts/test-trace-registration.cmd passes /W4 /WX with actual fixture thunks.
It checks foreign-thread rejection, cap/expiry maintenance, stop/drain retention,
conflicts, destructor late calls, collector exceptions, and lifetime-loss cleanup
after the entry page is changed to PAGE_NOACCESS and freed. Existing slot and
event fixtures also pass after the new detach operation. Logs are
evidence/trace-registration-fixture.log, trace-slots-fixture.log and
trace-events-fixture.log. These are native executable fixtures, not live-game
proof. The scheduler, target collector, registration transport and Harness still
need to be wired to this owner; no runtime DLL was changed or rebuilt.

## Target collector composition — 2026-10-09

target_trace_collector.h connects the prepared native capture plan to the
registration's Collector signature. Preparation uses the existing guarded schema
adapter and captures the function's owner class identity. Optional target filters
are validated separately from the exemplar object. Collection requires the current
process/game thread, the observed GC/shutdown gates, live function/owner registry
identities and matching owner pointer, a registered non-destroying observed object,
class compatibility, and an exact filter match when requested. It then resolves
the supported native frame path and copies scalar fields with guarded reads.
Failures clear both event identity and bytes; no raw frame/object pointer is
published and no engine function is invoked by the collector.

scripts/test-trace-collector.cmd passes MSVC /W4 /WX. Its synthetic registry uses
the actual build-specific offsets and production registry helpers. Tests cover
target filters, stale serials/slots, each GC/shutdown gate, destroying objects,
foreign threads, wrong/bytecode frames, PAGE_NOACCESS frame/result reads and a
released registry reservation. A composed test installs a real fixture thunk,
calls its original, collects a scalar result through the target adapter, drains
the event, restores the entry, and checks that a late thunk emits no further event.
Evidence: evidence/trace-collector-fixture.log. The schema adapter compile check
also passes with the collector included (trace-plan-fixture.log).

This is still synthetic validation. Runtime wiring must own the context for the
entire registration, establish the exact executable profile before preparation,
and stop registrations on reflection/identity lifetime changes. The collector
uses the schema established at registration; it does not repeat the complete
property-schema validation on every POST. Session transport, game-thread scheduler
maintenance, live frame observations, Harness routing and relaunch validation
remain outstanding. No deployed DLL or running controller was changed.

## Candidate trace wire contract — 2026-10-09

native/trace_protocol.h and Python _trace_wire.py define a packed57792-byte
request/reply contract with start, stop, drain, status and forget. Start carries
an observation-only reflected schema, optional exact target identity, duration
up to300seconds and budget up to1000 events. Control operations require the owner
and existing registration, with no schema or start-only parameters. Responses
carry bounded counters and at most8 copied scalar events; event records contain
registry identities, sequence/time/thread and owned bytes, with no frame address.
Native request validation rejects response data on input and unsupported codecs.

Python checks request/reply correlation, assigned or retained registration IDs,
event process identity, sequence/counter bounds and zero unused payload/event
tails. Event gaps remain allowed for queue overflow. Cross-drain sequence tracking
and matching payloads to retained registration plans remain session-layer duties.
The contract uses current State values0..5 and Cleanup values0..4. It does not
itself authorize registration or establish that the session supports traces.

The native protocol fixture passes /W4 /WX. scripts/verify_trace_wire.py writes
actual Python packets for unfiltered/filtered start and each control operation;
the compiled native validator accepts all six. All358 Python tests pass, including
ownership/schema corruption, wrong process, event bounds, start registration and
copied-value checks. Evidence: trace-protocol-fixture.log, trace-wire-tests.log and
trace-wire-cross-language.log under evidence/, with raw packets in its
trace-wire-cross-language/ directory. SessionPacket/controller/runtime wiring is
still pending. The deployed v17 ABI and loaded DLL remain unchanged.

## v18 native session integration candidate — 2026-10-09

trace_registry.h now owns up to16 stable native registration/context pairs and
implements the wire operations. Owner plus native-assigned monotonically advancing
registration IDs identify entries; IDs are not reused across session reopening.
Stopped/capped/expired registrations retain events until drain/forget. Duplicate
function hooks are rejected by the immutable pool. Forget closes before destroying
context. GC-sensitive cleanup returns934 for later game-thread retry; lifetime
loss detaches callbacks without reading the lost entry. Terminal close revokes all
contexts. Unexpected entry conflicts are preserved and reported during cleanup.

TargetTraceOps supplies guarded build-specific storage checks. Registry preparation
copies the reflected schema out of IPC before hook ownership begins. The registry
fixture passes actual thunk tests for owner isolation, duplicate rejection,
cap/drain, forgotten IDs, deferred close, wrong-thread close and session reopening.
The existing immutable-slot tests also pass. Production target adapter compilation
passes with the registry included.

E33_TRACE_SESSION adds a distinct v18 message/mapping, packet and DLL path, while
requiring the full v17 capability chain. The controller advertises trace protocol1
and transports trace packets through action110. Backend open begins the registry;
each game-thread message maintains expirations; close removes traces before other
resource cleanup and preserves trace cleanup errors across deferred close passes.
Trace payload parsing bypasses console text decoding. Existing v17 code paths stay
under their previous feature macros.

scripts/build-trace-candidate.cmd builds runtime-session-v18/runtime_session_v18.dll
and research-probe-v18/research_probe.exe successfully under /W4 /WX. Hashes are in
evidence/trace-v18-build-hashes.json; build log is trace-v18-build.log. The v17
runtime translation unit and menu/button fixtures also pass after integration
(test-button-delegate-pool-trace-integration.log). Registry and slot reruns are
test-trace-registry-trace-integration.log and test-trace-slots-trace-integration.log.

The candidate has not been loaded into the game. Python Session methods and scope
cleanup, SDK invocation while a function is traced, original Harness routing and
live/relaunch tests remain pending. In particular, existing reflected invocation
checks still expect the original entry; calls through SDK invocation must account
for our own validated observer entry before using them to trigger a live trace.
No claim of live trace functionality is made by this build. The mapped v17 binary
and running controller were not overwritten.
