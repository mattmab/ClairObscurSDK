# Native widget ownership investigation — 2026-10-09

Target: Steam23765773, SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
Addresses below use Ghidra image base140000000; they are not portable offsets.

## Confirmed static paths

WidgetBlueprintLibrary.Create (1431361b0) reaches143119950 through the local
controller path14311a080. The latter validates UserWidget ancestry, constructs
an object through1413bf660 and invokes its initializer. This path does not by
itself establish an independently owned SDK reference.

AddToViewport (1431355b0) reaches143049ba0 through the viewport subsystem.
That path stores an index/serial identity, obtains Slate references through
1430f7f70 and passes strong Slate references to viewport virtuals. The subsystem
map contains weak references; membership alone is not evidence of GC retention.

TakeWidget's path1430f7fb0 caches weak Slate references and constructs an
SObjectWidget through1430c3260/1430baaf0 when needed. Constructor1430b4620
registers its embedded GC holder at widget+288 using1412514b0. The holder's
UObject slot is holder+10 (widget+298), assigned by143118cc0. That assignment
uses1412b0e90 when global14934e968 is nonzero; copying a pointer does not reproduce
the engine's complete assignment behavior.

The GCObjectReferencer global149346f60 points to an object whose+28 member owns
locked registration state. Normal and conditional holder arrays are at state+28
and+38. Registration1412514b0 uses holder+8 to select the array and holder+9 to
record registration. Unregistration14125bb10 removes the pointer under the same
critical section and clears the flag. Global149272cea gates registration; its
full meaning is not yet established.

GC traversal1412366f0 invokes holder vtable+8. SObjectWidget's corresponding
callback143117640 passes the address of holder+10 through141067100 to collector
virtual+10. Assembly confirms this forwarding; the complete collector ABI and
concurrency contract remain unverified. Holder vtable+10 (14311f240) constructs
the diagnostic name SObjectWidget(...), including engine-owned string handling.

Shared-control destruction1430cabe0 reaches1431151d0 and143130000. These perform
widget-specific callbacks/reset work as well as unregistering the GC holder.
SObjectWidget is therefore not a generic wrapper to borrow for SDK retention.

## Live read-only corroboration

`scripts/inspect_gc_owners.py` validated the exact executable and enumerated
referencer5643, GCObjectReferencer_2147482645, in game PID34604. It observed:

- Normal array:2,908 registered holders, including1,124 SObjectWidget holders.
- Conditional array:5 holders, no SObjectWidget holders.
- Matching widget identities included settings mapping entries, wrapping text,
  buttons, sliders and input-action widgets.

The probe checks registry index/address/serial, holder flags, repeated headers
and membership arrays. It does not acquire engine locks, pin values, or claim an
atomic GC snapshot. Evidence is `evidence/gc-owners-live.json`. No engine command,
GC operation, widget creation or ownership mutation was performed.

Static evidence: `evidence/widget-ownership-body.json`, `widget-gc-owners.json`,
`slate-holder-constructor.json`, `gc-register-body.json`,
`gc-holder-lifecycle-defined.json`, `gc-release-callback.json`,
`gc-unregister-helper.json`, `widget-gc-vtables.json` and
`gc-abi-143117640.json`/`gc-abi-141067100.json`. Ghidra was saved after defining
the verified callback/destructor functions (`save-widget-ownership.json`).

## SDK implementation boundary and next steps

SDK retention is **not implemented**. These findings support investigating a
separate SDK-owned holder that uses the target registration mechanism without
changing an object's shared root flag. Before implementation:

1. Verify the holder virtual contract, collector ABI, diagnostic string ownership,
   registration/GC synchronization and engine shutdown ordering.
2. Register ownership in the same game-thread operation that creates a widget,
   before returning it to Python. A later Python retain request leaves a GC gap.
3. Use bounded, session-generation lease identities and scoped release; validate
   controller disconnect, mod unload and game exit without stale registrations.
4. Validate Create/add/remove/release as a bounded specimen before connecting
   the shared management registry. Separately verify input/focus restoration.

This mechanism concerns UObject lifetime. It does not solve owned FKey values,
native strings, containers, input dispatch or full Introspection Harness parity.
The console fallback and persistent Python host remain independent of UMG.

## Generic strong-holder candidate — subsequent investigation

The generic engine holder is a better candidate than a custom GC subclass.
Diagnostic141e733d0 names it
`UEStrongObjectPtr_Private::TInternalReferenceCollector`. Disk pointer search
locates its four-entry vtable at146eddd50:

| Slot | Address | Verified behavior |
| --- | --- | --- |
| 0 | 141e6c4f0 | Resets base vtable, unregisters via14125bb10, frees24-byte storage when flags bit0 is set. |
| 8 | 141e6c930 | Calls collector virtual+88 with `(collector, holder+10, 0, 0)`; explicit assembly confirms all four register arguments. |
| 10 | 141e733d0 | Constructs an engine-owned diagnostic FString through141027600 and returns the output pointer. |
| 18 | 1410044f0 | Returns false. |

Unlike SObjectWidget's collector+10 forwarding, this generic callback explicitly
uses+88 and zeroes its additional arguments. The SDK candidate uses the existing
engine vtable, not a guessed collector ABI or a custom diagnostic string callback.

Correction to the exploratory six-pointer vtable dump: the apparent entries at
GC base+20 and SObjectWidget holder+20 begin separate adjacent vtables. Direct
constructor xrefs to146de2658/14739f488 establish those boundaries. They must not
be copied as additional GC-holder methods. The raw exploratory dump remains
unchanged as evidence, with this interpretation recorded separately.

Creation sites141ea77c0,141e72e20 and143150220 independently show allocation
through144a98010(24), zeroed holder flags, base vtable, registration1412514b0,
generic vtable assignment, object slot assignment and the conditional1412b0e90
barrier. Destruction is through the holder's deleting destructor with flags1.
The barrier marks registry/cluster state and queues references; the candidate
calls this target helper instead of reproducing its internals.

Global149272cea is now supported as an exit-request indicator by callers with
`Win RequestExit` and `ConsoleCtrl RequestExit` diagnostic strings. Registration
is disabled once it is set. This is separate from the existing9272cfc guard.

The extended read-only probe observed three generic holders, retaining objects
of classes AudioSubsystemCollectionRoot, TypedElementRegistry and
InterchangeManager. All matched the live registry identity checks. No scope-guard
holder was found in this snapshot; absence is not proof of unavailability.

Evidence: `strong-holder-pointer-search.json`, `strong-holder-creation-body.json`,
`strong-holder-paths.json`, `strong-holder-callback-abi.json`,
`strong-holder-name-bodies.json`, `gc-contract-xrefs.json` and updated
`gc-owners-live.json`. The database save succeeded (`strong-holder-save.json`).

### Implemented candidate, not yet a live SDK capability

`native/strong_reference.h` implements explicit creation/release with persistent
tracking and registration/destruction uncertainty. `target_strong_reference.h`
binds the verified target operations and identity/thread/GC/exit guards. It is
not included in the running transport and has not created an SDK-owned holder.
There is no public Python retain API yet.

`scripts/test-strong-reference.cmd` passes /W4 /WX compilation of both the fixture
and target adapter. The fixture checks creation order, conditional barrier,
post-allocation revalidation, allocation/registration rejection, duplicate
acquisition, deferred release, foreign-vtable rejection, idempotent empty release
and quarantine after ambiguous registration or destruction. These are lifecycle
logic tests, not proof that target engine calls work live.

Remaining integration gates: bounded generation-scoped lease storage, SEH fault
containment and membership reconciliation, controller-death cleanup and a live
register/release specimen. Quarantine alone is not a complete recovery strategy:
an interrupted registration can leave a base-vtable holder in the engine list.
Do not enable this candidate until that state can be reconciled safely. Creation
must retain returned objects before the invocation response reaches Python.
