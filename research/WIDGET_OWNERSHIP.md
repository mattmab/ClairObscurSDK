# Native widget ownership investigation — 2026-10-09

Current status: v9 stable retained returns passed the complete base UserWidget
create/add/remove/release specimen live. v8 public retained invocation and original
Harness retained values are implemented and live-tested (OBJECT_LEASES.md).
The first v8 viewport specimen exposed lazy registry serial assignment; v9 now
assigns serials through the verified engine allocator before returning ownership.
Earlier investigation stages below preserve their original evidence boundaries.

## Canvas/Button child lifecycle — live proof, 2026-10-09

`scripts/verify_live_widget_children.py` ran through native console `py` in the
existing persistent v9 host, completing at 02:24:08 local. It created a base
UserWidget, read its engine-created WidgetTree, and used reflected
GameplayStatics.SpawnObject to construct a CanvasPanel and Button with that tree
as outer. CanvasPanel.AddChildToCanvas returned a retained CanvasPanelSlot.
GetChildrenCount changed 0 to 1; the Button's reflected Slot reference matched
the returned slot's index and serial. RemoveFromParent changed the count to 0.
All four created return objects had positive stable serials and independent
scoped holders. Scope close restored the exact three original generic holders.

The tree itself had serial0 and was referenced by the retained UserWidget;
this test does not establish a general zero-serial input stabilization API.
No root property was written, nothing was added to the viewport, and input/focus
were unchanged. This is child construction/attachment proof, not menu rendering
or forced-GC survival proof. The persistent host was not replaced.

Static evidence corroborates the live call: SpawnObject thunk143744670 calls
14372aa60, which validates class/outer and constructs through1413bf660.
AddChildToCanvas thunk143092410 calls panel helper1430be620. That helper creates
a slot with the panel as outer, links slot/content/parent references with the
target's conditional reference barrier, adds the slot to the panel, then invokes
the panel callback and invalidation. Reflected frames are respectively24 and16
bytes; no stock UE ABI was substituted.

WidgetTree.RootWidget is reflected at+30; UserWidget.WidgetTree at+278. The live
WidgetTree schema exposes no owned reflected constructor or root setter. A
verified, identity-checked game-thread object-property assignment primitive is
the next gate for a reusable root assignment and the Harness `set` capability.
Do not replace this gate with an external memory write based only on the offset.

Local evidence: widget-tree-schema.json, widget-child-plans.json,
widget-addchild.json, widget-panel-add.json, console-spawn-body.json and
widget-children-live.json. Raw evidence remains outside release packages.

## Base UserWidget specimen and lazy serial assignment — 2026-10-09

The live read-only probe `scripts/inspect_widget_initialization.py` confirmed
UserWidget class696, CDO30457, constructor143112f70 and initializer143120090.
The constructor forwards to143114800. Initializer virtual+318 constructs a
WidgetTree at widget+278 when missing; its native-class callback virtual+320 is
the empty function141004480. Virtual+350 is1431231a0, which includes initialized
event dispatch. Raw class flags30e810a1 were recorded, not interpreted by stock
UE constants. The original BL4 menu's direct UserWidget/tree construction was
used as a reference, not as proof that E33 creation would work.

`scripts/verify_live_widget_lifecycle.py` preflight verified exact reflected
parameters: WidgetBlueprintLibrary.Create32 bytes, UserWidget.AddToViewport4,
Widget.IsInViewport1 and Widget.RemoveFromParent0. The specimen was entered with
`py` through the existing native console and persistent v8 host, without a second
controller. Create returned a new base UserWidget236314, serial0, named
UserWidget_2147464901. Its native generic holder existed before Python received
the result; total generic holders increased3 to4. IsInViewport initially returned
false. No game-specific widget asset, input mode, focus or GC command was used.

AddToViewport dispatched but returned error223/outcome unknown because the strict
post-dispatch target identity check no longer matched. No add retry was made.
Read-only observation found the same index/address/class/name, now serial86451,
with a registered SObjectWidget holder. The SDK test scope released its own holder
and the generic-holder baseline returned to3. Thus creation/retention is proven,
but this run is deliberately recorded as a failed end-to-end lifecycle test.

Explicit recovery used a fresh catalog identity, acquired a temporary SDK lease,
confirmed IsInViewport=true, called RemoveFromParent once, and confirmed false.
Scope cleanup restored the exact three original generic holders. The first
recovery preflight stopped before dispatch because it compared mutable registry
flags too; the corrected preflight compares identity/ownership fields and the
native operation still performs its full validation. Recovery completed at
02:06:52 with the same persistent Python host39652/session still active.

The viewport path143049ba0 calls1413c5c50 to make an index/serial weak identity.
That helper calls1413ab8b0 with the object array and index. The latter reads the
item's serial at+10; if zero, it atomically increments the array counter at+b0
and compare-exchanges the new serial into the item, returning the winning value.
This explains the observed zero-to-assigned transition. Serial0 must not become
a wildcard, nor should the existing identity guard be relaxed. Next: verify the
allocator ABI/assembly and establish an engine-managed serial while retaining a
new return value on the game thread, before publishing its identity to Python.
Use a fresh candidate DLL path; v8 remains loaded in the running game.

Evidence: widget-initialization-live.json, widget-initializer.json,
widget-base-callbacks.json, widget-native-ctor.json, widget-lifecycle-preflight.json,
widget-lifecycle-live.json, widget-weak-assign.json and widget-serial-allocate.json
under local evidence/. Ghidra's verified constructor definition was saved.
Native menu rendering, child construction/property writes, focus recovery and
key dispatch remain unfinished; this blank widget is not a Mods Menu.

### Isolated stable-return candidate (not yet live-tested)

`scripts/build-stable-call-candidate.cmd` builds a separate v9 DLL/controller
under runtime-session-v9/research-probe-v9. The loaded v8 files were not replaced.
Assembly of1413c5c50 confirms RCX=object array, EDX=object index, EAX=serial for
1413ab8b0. The new retained-output callback first acquires the existing strong
lease, then invokes that allocator only for an exactly matching zero serial.
It publishes the recaptured identity only after validating index/address, the
returned positive serial and game-thread/GC/exit guards again. Error413 retains
unknown outcome and leaves any acquired holder in the session cleanup pool.
It neither treats zero as a wildcard nor relaxes the existing target checks.

The wire envelope remains unchanged. v9 has its own message/mapping/DLL names
and advertises stable_identity_protocol=1. Older builds do not allocate serials.
This currently applies only to retained output object identities; it does not
repair arbitrary input/target serial transitions during a call.

Build with /W4 /WX passed. `scripts/verify-stable-identity.cmd` passed the native
fixture covering first assignment, existing serials without reallocation, stale
zero observations, unavailable/lost context, returned-serial mismatch, replaced
identity and invalid identities. v8 and default v5 runtime compatibility objects
also compile with /W4 /WX. These are compile/fixture proofs, not game validation.
Next: expose an explicit experimental v9 session, hand over cooperatively, run
the complete guarded widget specimen, confirm removal/holder cleanup, and restore
the persistent host. No new release or package validation is claimed yet.

### v9 public session and live lifecycle proof

`Session(stable_returns=True)` and `launch.cmd management --stable-returns` select
v9 explicitly, imply retained calls, and require all four native capabilities.
Missing capability closes the opened transport. Session/mod scopes expose
supports_stable_returns. 127 Python tests pass, including the opt-in and failed
handshake cleanup. The package manifest input list now includes the v9 pair;
isolated v9 package execution remains a separate pending check.

The v8 host exited cooperatively through mods action shutdown at02:14:44.
Persistent v9 host27480/controller24140 started02:15:01 in the same game34604,
session4911e4510a1a423a989134bc52647bb6. The specimen was entered through native
console Python. New UserWidget237337/serial86453 was retained before returning;
IsInViewport went false -> true after AddToViewport -> false after RemoveFromParent.
Release acknowledged and the exact three original generic holders were restored.
The run completed02:16:22 without retry or recovery. Evidence:
evidence/widget-lifecycle-stable-live.json and logs/management-host-v9.stderr.log.
The failed v8 evidence remains separate. The v9 DLL is now pinned until game exit;
do not rebuild its loaded path. The persistent management/Harness host remains live.

This specimen has no child content and did not acquire focus, so it does not prove
visible menu rendering or focus restoration. Next gates: child construction/tree
root assignment, native string/text and settings controls, then verified input
routing/focus lifecycle and key dispatch. Full Harness parity is still incomplete.

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

At this initial candidate stage, integration gates included bounded
generation-scoped leases, fault containment, controller-death cleanup and a live
register/release specimen. The subsequent v7 work in OBJECT_LEASES.md completes
those normal-path lease and cleanup gates and initializes a complete collector
before registration to avoid an interrupted base-vtable holder. Arbitrary native
fault repair is still unsupported. Creation must retain returned objects before
the invocation response reaches Python.
