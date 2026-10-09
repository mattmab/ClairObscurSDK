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
