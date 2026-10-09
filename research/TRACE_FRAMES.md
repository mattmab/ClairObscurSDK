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
