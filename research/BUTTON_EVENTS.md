# Target button events and Python action callbacks

Build: Steam23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
Investigation uses the live independent catalog and this executable's Ghidra
database. No button callback hook or delegate binding has been installed.

## Live reflected contract

Button has MulticastInlineDelegateProperty fields OnClicked at0x5a8,
OnPressed0x5b8, OnReleased0x5c8, OnHovered0x5d8 and OnUnhovered0x5e8,
each16 bytes. Their referenced signature UFunctions have zero parameters,
no return, flags0x130000 and shared entry RVA13937a0. That entry is a shared
script-dispatch path, not an independently callable click implementation.
Button's own reflected functions are IsPressed and setters for background/color,
click/press/touch methods and style. IsPressed is a state query, not a click event.

The exact live Button class constructor is RVA303ba80; its CDO vtable is737e700.
The constructor initializes the five delegate fields and the cached Slate shared
reference at5f8/600. IsPressed3095160 reads that cached widget and two state bits;
polling it would not establish delivery of every completed click.

Evidence: `button-events-live.json`, `button-thunks.json`,
`button-construction.json`. The independently verified IsPressed entry was
defined in Ghidra and the program saved (`button-analysis-save.json`).

## Concrete native path

The Button vtable slot300 points to RebuildWidget-like routine307c280. It creates
an SButton and five weak-UObject delegate instances, using the target weak
identity helper13c5c50. Click delegates have vtable7382098 and allocate3 units
of16 bytes. Their weak object identity is at18, member-function pointer at20 and
signed object adjustment at28. This is target-derived storage, not an assumed
portable layout or an exposed SDK ABI.

SButton construction16cc9a0 copies the five delegate arguments at220..260 into
live SButton delegate storage at2d8,2e8,2f8,308,318. Its click delegate execution
routine3059490 resolves the weak object, applies the stored adjustment and calls
the stored method with a result buffer. Click callback3089290 broadcasts the
UButton's OnClicked field through138eb60 and constructs a handled reply. The
press/release/hover/unhover callbacks are3089360/3089390/3089330/30893c0.

Broadcast138eb60 copies16-byte weak-object/name entries, resolves each receiver's
function and invokes its ProcessEvent slot268; stale bindings can be removed.
This is not a call through the signature UFunction's shared entry. A signature
hook or the existing fixed getter observer therefore does not supply this event.

Delegate clone3054a90 copies the weak identity, function pointer and adjustment.
Copy helper1122400 invokes that clone operation before replacing old storage.
Consequently, patching one delegate pointer and later restoring it is not by
itself proof that every copied callback was removed. Callback modules/storage
must outlive all possible calls, and unregistration needs a verified ownership
contract. The button releases its cached Slate shared reference in3080b90.

Evidence: `button-vtable.json`, `button-virtuals.json`,
`button-event-callbacks.json`, `button-delegate-broadcast.json`,
`button-delegate-vtable.json`, `button-delegate-execution.json`.

## Implementation implications and remaining gates

Use the actual event path for reusable mod actions; do not infer clicks from
IsPressed polling or execute signature functions as commands. Two candidates
need further ownership/ABI investigation: a real script-delegate receiver with
an SDK-owned reflected callback, or a narrowly owned Slate delegate adapter that
preserves the original reply and accounts for cloning. Neither is implemented.

Whichever path is verified must queue copied owner/action tokens on the game
thread, return immediately through the original engine path, and run Python
callbacks only in the persistent external controller's poll. It must revoke
delivery before menu detach/lease release, discard stale session registrations,
handle late or cloned callbacks safely, and bound the queue with explicit
overflow reporting. Required live tests include real mouse/keyboard activation,
one delivery per action, original reply preservation, callback exceptions,
unregistration, controller loss and relaunch. Menu lifecycle evidence alone
does not establish those capabilities.

## Live constructed-button corroboration

The first read-only pass found no constructed exact-base Button suitable for
corroboration. The bounded `inspect_button_events.py --owned-specimen` run then
created the previously verified disabled Button/tree and inspected it after
Slate creation. Button index96514/serial19372 had a cached SButton with vtable
6e6e7e0 and reference-controller vtable6e65f20. Its click delegate at SButton+2d8
had vtable7382098,3 allocation units, weak index/serial matching the Button,
callback3089290 and zero object adjustment. Repeated pointer/data reads agreed.
The trailing32-bit delegate-container word was observed as zero; its meaning is
unverified (the initial artifact labels it `capacity_observation`).

The specimen performed no click, callback replacement or delegate binding.
It removed the owned tree and restored the exact strong-holder baseline.
Evidence: `button-events-live.json`, `button-event-specimen-live.json`,
`button-event-specimen-run.log`. These corroborate live storage and identity,
not a validated event hook, callback ABI under execution or teardown adapter.

## Concrete Slate owner candidate

The live-correlated reference-controller vtable6e65f20 has destroy-object entry
1632a80 (calls161aee0 on controller+10) and destroy-controller entry161d960
(resets the base controller vtable and frees a398-byte allocation when requested).
Allocation1610f90 initializes strong/weak counts at8/c, constructs the embedded
388-byte SButton at10 and follows the same decrement/destroy/weak-release order
as the independently verified viewport controller. Evidence:
`button-reference-vtable.json`, `button-reference-functions.json`.

`target_slate_reference.h` now uses compile-time profiles for these two exact
target types. The existing viewport alias keeps its original verified constants;
the SButton profile has its own vtables/destructor entries. No generic arbitrary
addresses or destructor callbacks are accepted from Python. The same durable
OwnedSlateReference states guard acquisition/release and quarantine interruption.

`target_button_reference.h` adds a candidate that checks the exact live Button
class and identity, game-thread/GC/exit context, cached shared owner, delegate
vtable/allocation units, weak identity, original click method and adjustment.
It publishes its capture before acquisition and can later detect changed Slate
or delegate storage. Holding the SButton can protect its allocation while an
adapter unregisters, but does not by itself prevent delegate replacement or
solve copied callbacks. The caller must keep the UButton lease and revoke any
event adapter before releasing the captured Slate owner.

Validation: existing native lifecycle/reference/request/session fixtures pass;
the new capture adapter and v13/v14 runtime translation units compile with /W4
/WX (`button-reference-candidate-build.log`). No loaded DLL was rebuilt. SButton
native retention/release is NOT live-validated or installed; it is a prerequisite
candidate for the eventual callback adapter, not a completed click API.

## v15 menu-owned SButton reference integration and live normal close

The isolated E33_BUTTON_REFERENCE_SESSION/v15 runtime now captures the exact
child's SButton reference after successful menu attachment/activation, inside
the durable AttachUnknown interval. Native cleanup releases it after widget
detachment and before the captured viewport baseline. Failed/uncertain acquisition
or release stays protected by the existing menu/session quarantine; no captured
state borrows the controller mapping. No callback pointer is modified.

`Session(button_references=True)` opts into v15 and its full v14 capability chain.
Its separate message/mapping names prevent adoption by a v14 controller. Payload
layout is unchanged; menu responses additionally report the native reference
state. Python checks that successful prepare/close report Empty0 and successful
attach/focus report Live2. Missing, malformed or inconsistent state acknowledgements
abort ownership rather than infer success.

Live `verify_live_scoped_menu.py --button-references` passed on PID21804:
prepare reported0, attach/focus reported2, and explicit native close reported0.
The original viewport focus, root/children and exact UObject holder baseline
were restored. Evidence: `button-reference-progress.json`,
`button-reference-live.json`, `button-reference-run.log`.
All203 Python tests pass; native fixtures and v13/v14/v15 layout compilation pass
(`button-reference-python-tests.log`, `button-reference-integration-fixtures.log`,
`button-reference-v15-build.log`). This proves normal acquisition/release, not
that the final-strong-owner destructor branch was exercised live.

Pinned v15 DLL SHA256:
96f167748196f71c28cb430a0272de32270afad8500f06424c805954096b9af8.
Controller SHA256:
3f98e72f0473634379a3b583154369f25b7241ee7a3cf8b93a4f6adf9a353f95.
Do not overwrite/rebuild the DLL while PID21804 remains alive. The existing v13
persistent controller and v14 runtime artifact were preserved.

The v15 controller-loss test now passes independently of v14:
`verify_live_menu_disconnect.py --button-references` terminated only its own
controller after focus and bypassed Python cleanup. The native runtime restored
the same viewport and exact UObject holder baseline; a fresh v15 session reported
an empty menu and Empty0 button reference. Evidence:
`button-reference-disconnect-{progress,live,result}.json` and
`button-reference-disconnect-run.log`.

Remaining: v15 game-relaunch testing; callback binding/observation,
cloning-aware revocation, transport queue and persistent Python action dispatch.
Controller replacement does not establish game-relaunch behavior or exercise the
final-strong-owner destructor branch.

## Instance-vtable adapter investigation and action queue candidate

Further target decompilation identifies a narrower alternative to changing the
member-function pointer at delegate+20. Click helper RVA16e0bb0 checks the stored
delegate at SButton+2d8 through vtable+30 and invokes that same instance through
vtable+58, passing a local reply buffer. It does not first clone the delegate.
The mouse-path routines RVA16f0240 and16f2120 reach this helper. The original
execute entry RVA3059490 resolves the weak UButton, calls its unchanged method
and returns the reply-buffer pointer. Original callback RVA3089290 broadcasts
OnClicked before building its handled reply. These are static findings, not a
live SDK click-delivery test.

Both clone variants RVA3054a90 and3054b10 explicitly write the engine vtable
RVA7382098 to the new instance and copy the original member-function pointer.
Thus an adapter confined to an individual delegate's vtable, leaving its method
pointer untouched, would not propagate SDK hooks through these clone paths.
Copy helper RVA1122400 invokes clone slot40 into temporary storage, destroys the
old destination and transfers the new allocation. Destructor RVA1260100 returns
the instance and frees its48-byte allocation only when flags bit0 is set; even
a flags0 invocation can precede reuse/free by the surrounding container.

Preferred next candidate: retain the SButton, validate the original delegate,
replace only that instance's vtable with durable pinned storage, forward execute
to the immutable engine entry without interpreting/copying the FReply, and
observe destruction to revoke routing before memory reuse. Preserve original
clone entries so their copies remain engine-native. Restore the exact original
table before detachment; never overwrite another owner's replacement. Verify
the complete table extent and actual register-level ABI before publishing it.
Late calls, reentrant destruction/replacement, moved storage and thread ownership
still require adapter fixtures and live corroboration. No hook is installed.

Evidence: `button-adapter-functions.json`, `sbutton-input-vtable.json`,
`sbutton-input-functions.json`, `sbutton-click-dispatch.json`, plus the earlier
`button-delegate-execution.json`. No game mutation occurred in these queries.

`native/menu_action_events.h` now implements the game-thread-owned bounded queue
needed by this adapter. Registration tickets contain copied session, monotonically
increasing registration, owner and action IDs. The adapter must capture a ticket
before forwarding to Unreal and validate it on completion: the original call can
synchronously revoke or replace a route. Revocation discards queued events for
that registration; owner cleanup preserves other routes; close removes all routes
and queued events. Generations never reset across sessions, and overflow is
reported without replacing existing events. Queue methods are not thread-safe:
the future runtime adapter must enforce game-thread access for bind/execute/drain.

`test-menu-action-events.cmd` passes with /W4 /WX. The fixture covers forged
tickets, duplicate instances, queue/registration capacity, overflow reporting,
owner isolation, revocation during an original call, same-address rebind and a
reused session ID. Evidence: `menu-action-events-fixture.log`. The queue is not
yet connected to IPC, Python callbacks or the live delegate. This is not proof
of mouse/keyboard delivery, native reply preservation or live unregistration.

## Verified table/ABI and reversible lifecycle core

The exact delegate vtable contains13 entries, ending with execute at+58 and a
second optional-execution entry at+60 (RVA305a2e0); the next table begins with
destructor RVA1260100. The preceding word is another function pointer, not an
assumed RTTI locator. `button_delegate_contract.h` records and validates all13
entries and prepares a shadow changing only destructor/execute/optional-execute.
It preserves every clone entry and does not write engine memory.

Assembly corroborates execute's RCX=instance/RDX=reply-buffer ABI and return of
the original buffer in RAX. Destructor takes RCX=instance and flags in EDX,
conditionally frees48 bytes on flags bit0 and returns the instance in RAX.
The optional-execute entry resolves the weak object, calls the original method
using its own192-byte reply buffer, destroys that reply and returns success in
AL (false when weak resolution returned null). An adapter must forward both
execution entries and only enqueue the optional path when it succeeds; it must
not fabricate or shallow-copy FReply. No runtime call to these new adapter
entrypoints has been made.

Evidence: `button-adapter-table.json`, `button-adapter-abi.json`,
`button-execute-return.json`, `button-execute-safe.json`, `button-safe-abi.json`.
Two requested assembly addresses in the first ABI query were not instruction
boundaries and returned errors; the separate return/safe queries supply the
actual instruction evidence. These errors are not counted as verification.

`owned_button_delegate.h` adds the candidate lifecycle around the queue:
Empty/Installing/Active/Revoked/Restoring/Destroyed/Quarantined. It publishes
mutation states before vtable exchanges, restores only an expected shadow table,
revokes routing before waiting for active calls and never replays unknown
install/restore outcomes. A destructor notification revokes and restores before
forwarding, then prevents any later dereference even while an earlier execute
unwinds. Close during an original callback defers restoration until that call
returns, suppressing its revoked ticket. Quarantine keeps the owner protected.

The expanded native fixture passes /W4 /WX for table validation/clone-slot
preservation, invalid installation, reentrant close, failed execution, destruction
during execution, no access after free, conflicting table replacement and unknown
outcomes after both installation and restoration writes. The exception fixtures
model interrupted operations; they do not prove engine SEH behavior. Evidence:
`button-delegate-fixture.log`.

Remaining integration gates: pinned immutable forwarding thunks/table, target
Ops validating the retained live delegate, game-thread guards and SEH/finally
boundaries, transport/Python routing and real mouse/keyboard/lifecycle tests.
These headers are candidates, not installed capabilities. Existing runtime
v13/v14/v15 binaries were not rebuilt or changed.

## Native forwarding and real SEH fixture

`button_delegate_forward.h` now supplies the candidate forwarding implementations
for both execution slots and destruction. Normal execute forwards the original
instance/reply arguments and returns the original pointer without reading or
copying the reply. Optional execute forwards the bool result and queues only on
true. Both use Windows `__try`/`__finally` to unwind the captured registration
ticket; an abnormal original return revokes delivery and quarantines ownership
while the original exception propagates. Destructor bookkeeping happens before
forwarding and contains only its own SDK faults: the original destructor runs
once outside that exception handler and its exception semantics are preserved.

Foreign-thread calls forward to the immutable engine entries without touching
the game-thread queue and atomically latch a permanent fault. Runtime integration
must check that latch on EVERY owner-thread control/drain operation and quarantine
before inspecting any possibly freed delegate. This is a required integration
contract, not a claim that current runtimes already enforce it. Thunks, table and
original entries must remain pinned/immutable even after explicit unregistration.

The Windows fixture passes /W4 /WX, including all192 sentinel reply bytes, exact
return pointer, one event for successful execution, no event for optional false,
reentrant close, late-thunk passthrough, original execute/optional/destructor SEH,
SDK pre-destructor exchange SEH and exactly-once original destructor forwarding.
A real worker thread verifies foreign-thread passthrough and fault latching.
Unlike the earlier lifecycle model, these tests raise actual Windows structured
exceptions through the forwarding functions. They still use fixture delegates,
not the live game. Evidence: `button-forward-fixture.log`.

Windows compilation also exposed `max` macro collisions in the queue/lifecycle
headers; parenthesized numeric_limits calls now compile correctly with Windows.h.
All three action fixtures pass. No pinned game DLL was rebuilt or live delegate
changed. Remaining work is target-validated Ops, process-pinned publication,
runtime lifecycle/IPC/Python integration, and real input/cleanup validation.

## Target validation and pinned publication candidate

`target_button_delegate.h` now connects the contract to the retained target
Button. Installation validation requires the exact original/shadow table
addresses, aligned captured delegate, Live SButton reference, unchanged leased
Button/delegate identity and all13 original entries. The containing runtime must
still perform executable fingerprint validation before initialization.

Table initialization accepts only module-static table storage with all three
callbacks in that same module, then pins the module before exposing the immutable
table. Base, original callbacks and captured game-thread ID are never replaced
after readiness. Stack/heap shadow storage is rejected by module lookup. Table
preparation is not yet called by an installed game runtime.

Target expected-value exchanges are restricted to the captured delegate and the
original/shadow table pair. Pre-destructor restoration does not dereference the
UObject or require GC inactivity; the caller must still own the retained SButton
and invoke it on the captured thread, with outer SEH containment. The permanent
foreign-thread fault latch is checked by the shared control gate before any
runtime control or drain action may inspect delegate storage. The gate fixture
proves queued events are removed and ownership quarantined without touching a
simulated freed instance after a fault. It does not prove arbitrary concurrent
engine destruction safe; an unexpected thread remains a quarantining failure.

All three action fixtures and target install/close/forwarding translation-unit
compilation pass /W4 /WX (`button-target-compile.log`). No existing runtime DLL
was rebuilt. Next integrate the adapter's binding/revocation before menu detach
and lease release, expose bounded action IPC, and validate an isolated runtime
live before connecting persistent Python callbacks and registry controls.

## Runtime ownership integration candidate (v16)

`TargetButtonActions` now owns the queue, binding, pinned table and three
forwarding entrypoints in durable module storage. It publishes one immutable
thunk owner per module and keeps the same retained-reference record across
sessions, so a late thunk cannot route through a replacement owner. Binding
uses copied session/owner/action IDs; close clears the queue only after the
delegate lifecycle returns Ok. Drain checks the control gate before reading
events and reports bounded overflow. The current menu contract owns one button;
multiple native controls remain a later extension, not a claimed capability.

The E33_BUTTON_ACTION_SESSION runtime candidate stores this owner alongside its
retained SButton. Explicit menu close and backend/controller-loss cleanup both
close actions before entering menu focus/deactivate/detach/reference cleanup.
Deferred action close stops menu cleanup; quarantined/unknown outcomes quarantine
the menu and preserve lease protection. Menu commands consult the action fault
gate before operating. Outer SEH also quarantines action ownership.

The candidate uses separate v16 message/mapping names, preventing accidental
adoption through the existing v15 transport. The payload currently retains the
existing layout; action binding/drain wire commands are not yet exposed. No v16
DLL/controller was built or loaded, and no live action binding occurred.

`test-menu-action-events.cmd` passes all three fixtures, target adapter compilation,
both v15-compatible and action-enabled runtime translation units, and v16 layout
compilation/execution. Output confirms E33SDK.Session.v16 / E33Session16 names
with the current456192-byte packet (`button-action-owner-compile.log`). Native
integration exposed observer-global name-shadowing warnings, corrected without
changing the observer implementation. Remaining gates: binding/drain protocol,
controller/Python integration, isolated v16 build and real input/lifecycle tests.

## Bounded v16 action packet and runtime dispatch

Session command108 now accepts a2632-byte version1 ButtonActionPacket appended
at offset456188 (v16 SessionPacket total458824 bytes). Operations are Bind1,
Drain2, Unbind3 and Status4. Requests carry the current menu owner/child lease and
a nonzero action ID only for Bind; they cannot select a raw object or delegate.
Output fields must be zero, including all64 event records. Responses report
outcome, lifecycle state, registration generation, dropped count and copied
session/registration/owner/action/sequence events. Malformed requests are rejected
before dispatch; SEH returns Unknown and quarantines both action/menu ownership.

The runtime checks the active menu's session/owner/child lease and both protected
object leases. Bind additionally requires a successfully attached/focused,
non-quarantined menu, valid target context and Live retained SButton. Drain copies
through aligned native temporary storage before writing the packed packet.
Unbind revokes actions while preserving the menu; explicit menu close separately
marks close intent BEFORE action cleanup, preventing a new bind during deferred
action or menu cleanup. Controller-loss cleanup applies the same close intent.

Protocol fixtures reject invalid operations, missing ownership, polluted output
fields and every nonzero field in every event slot. Menu fixtures verify prepared,
closing, closed and quarantined menus reject bindings. The five native fixtures,
target and v15/v16 runtime compilation, and v16 layout execution pass
(`button-action-protocol-build.log`). The controller and Python transport do not
yet send this packet; no v16 DLL has been loaded and no live action claim is made.

## Controller serialization and Python decoder

The v16 controller now selects runtime-session-v16/runtime_session_v16.dll,
advertises button_action_protocol1 and its native session nonce, accepts strict
lowercase-hex `button-action` packets and returns the complete response packet.
It validates request fields before dispatch. The added binary command is excluded
from console-text decoding. v15 remains on its original runtime path/capabilities.

`_button_action_wire.py` constructs clean packets and correlates responses against
the operation, owner, child lease and action ID. It validates outcomes, lifecycle
states, registration, event bounds, zero unused output and within-packet sequence
ordering. Events must match the handshake session nonce and requested owner;
their registrations must match the returned active registration. Unknown outcomes
discard all partial events rather than dispatching them. The future callback
owner must additionally match its saved registration/action IDs and track sequence
progress across drains before executing Python.

Five Python tests pass for valid requests, lifecycle responses, foreign/stale or
unordered events, bounds/correlation and unknown outcomes. A binary response
written by the native fixture decodes to the expected event and dropped count in
Python (`button-action-native-golden.bin`, `button-action-native-python-layout.json`).
All native fixtures and both v15/v16 runtime AND controller translation units
compile with /W4 /WX (`button-action-controller-build.log`); Python results are in
`button-action-wire-tests.log`. These are offline checks. Session selection,
Python transport/callback ownership, isolated v16 binary builds and live validation
remain pending; no new runtime DLL was loaded.

## v16 session opt-in and first live transport proof

`Session(button_actions=True)` now selects research-probe-v16 and implies the
full retained-button/menu capability chain. A missing/non-integer action protocol
or invalid64-bit session nonce closes the candidate session and fails startup.
SessionTransport captures those handshake fields, requires every action capability
and validates the complete clean request before sending `button-action` bytes.
`supports_button_actions` reports the capability; it is not a click-validation
claim. Scoped callbacks are still pending.

All213 Python tests pass, including ten dedicated wire/transport tests covering
v16 selection, unchanged v15 selection, handshake rejection, malformed payloads,
acknowledgement correlation and native v16 layout. Evidence:
`button-action-session-tests.log`. The suite runs with the project's D: temporary
directory configuration; an initial run without it hit sandbox temp permissions.

The isolated v16 DLL/controller built successfully and
`verify_live_button_action_transport.py` passed against game PID21804. The session
advertised action protocol1 and a valid nonce, reported empty menu/reference state,
rejected status for an absent menu owner with911/Returned, remained responsive to
ping and closed normally. It created no widget, changed no focus and installed no
button hook. Evidence: `button-action-v16-build.log`,
`button-action-transport-live.json`, `button-action-transport-live.log`.

The DLL is now pinned in PID21804: do not rebuild/overwrite while that process
remains alive. DLL SHA256:
9334f2b99fe47a9defa9f17117f93a4b1d7fd341a87f36635b0273e682372cd8.
Controller SHA256:
1ee764faee0c45df4a2334aa5916431807f873d0bae3d6054a06e109034846e0.
Prior v13/v14/v15 artifacts were preserved. Next implement scope-owned action
handles and poll dispatch, then exercise binding, actual input, unbinding,
controller loss and relaunch. Transport proof does not satisfy those gates.

## Python-owned callbacks and live binding/cleanup proof

`NativeMenu.bind_action(callback)` now returns a menu-owned ButtonAction. Python
ownership is published before native binding. Each drain is validated as a whole
against the saved action/registration and previous sequence before delivery.
`Session.poll()` invokes callbacks on its external owning thread; self-removal or
menu/session close stops remaining batch delivery. Callback exceptions including
SystemExit become bounded traceback history in `action.failures`. Removal revokes
the callable immediately, keeps deferred cleanup pending and blocks rebinding.
Menu close revokes Python delivery before native close; session close and unknown
ownership abort revoke all menu callbacks. Interrupted transport calls become
unknown ownership rather than a retryable clean failure.

All220 Python tests pass, including Session.poll delivery, replay/mixed-batch
rejection, self-removal, deferred cleanup, interrupted bind and exception handling
(`button-action-callback-tests.log`). Usage is documented in SDK_API.md.

`verify_live_scoped_menu.py --button-actions` passed on PID21804 using the pinned
v16 DLL. The verified owned specimen prepared/attached/focused, bound registration1,
drained zero events, explicitly unbound, rebound registration2 and closed the menu
while the second action remained bound. Native menu cleanup restored the viewport
and Empty0 SButton reference; root/children and exact UObject holder baseline were
restored. The test session then closed normally. Existing v13 host remained live.

Evidence: `button-action-binding-progress.json`, `button-action-binding-live.json`,
`button-action-binding-run.log`. This proves actual native adapter installation,
explicit removal/rebinding and menu-driven teardown, not a real click or successful
forwarding of an engine-triggered action. No input was simulated. Next test actual
mouse/keyboard activation, persistent Python callback behavior and cleanup after
controller death/relaunch. General keybinds and multiple controls remain pending.

## Real mouse delivery and label isolation

The first real-input specimen received no events from a mouse click over its
overlapping disabled TextBlock or from Space. It timed out, then removed the menu,
restored viewport focus, cleared the WidgetTree root and removed both children.
Its post-finally exact-holder assertion was not reached on the failure path;
do not describe that failed run as a complete holder-baseline proof.
Evidence: `button-input-progress.json`, `button-input-live.json` and
`button-input-run.log`.

`verify_live_button_input.py --without-label` passed on the same PID21804 and
unchanged pinned v16 runtime. Three separate mouse clicks on the visible blue
SDK-owned Button delivered sequence1,2,3 to the same Python session/registration4.
The second callback deliberately raised RuntimeError; the traceback was retained
and the third callback still arrived. An additional click after explicit removal
produced no fourth event during the bounded observation. Menu close restored the
same game viewport, removed the root/child, restored the exact holder baseline,
and the session closed normally. The process exited0.

A Space press between mouse activations produced no additional event. Keyboard
activation is not proven; focus acquisition alone does not establish keyboard
routing. Removing the overlapping label isolated the mouse issue, but does not
by itself prove the precise Slate hit-test path. The next targeted check uses the
live reflected ESlateVisibility HitTestInvisible member on that label, with a
GetVisibility readback, instead of treating disabled state as non-hit-testable.

Evidence: `button-input-unlabelled-progress.json`,
`button-input-unlabelled-live.json`, `button-input-unlabelled-run.log`.
No game menu item or save was selected. General keybinds, multiple buttons and
v16 controller-death/relaunch validation remain pending.

The follow-up `--noninteractive-label` run resolved the native enum by reflected
path/member (ESlateVisibility::HitTestInvisible, observed value3), called the
verified Widget.SetVisibility and read the same typed value back. Clicking
directly over the visible text delivered sequence4,5,6 under fresh registration5.
The intentional second callback failure was contained again; a fourth click after
removal did not deliver another event. No runtime patch or input-mode change was
needed. Decorative siblings over a control must have explicit hit-test visibility;
SetIsEnabled(false) alone was insufficient in the original specimen.
The labelled run also restored the same viewport and exact holder baseline,
removed its root and both children, closed normally and exited0. Both successful
runs used separate session nonces and monotonically advancing registrations and
event sequences; no old event was delivered into the new session.
Evidence: `button-input-label-hit-test-progress.json`,
`button-input-label-hit-test-live.json`, `button-input-label-hit-test-run.log`.

## Bound-action controller death and session recovery

`verify_live_button_action_disconnect.py` passed on PID21804 with the unchanged
pinned v16 DLL. Its worker attached/focused an owned menu, bound the button and
drained an empty queue. It then killed only its own controller PID25668 and exited
with os._exit(23), bypassing all Python scope/session finally handlers. The native
owner watcher restored the same viewport focus and exact pre-worker UObject holder
set. No menu-close command was sent by Python.

A fresh v16 session reported no active menu and Empty0 button reference, then
rejected the old owner/child-lease status request with911/Returned, state0 and no
events. It created another owned specimen, bound a newer registration, drained
zero events, explicitly removed/rebound it, and closed the menu with the replacement
action still bound. The replacement action closed, native reference became Empty0,
viewport and exact holder baseline were restored, and the recovery session closed
normally. The supervising process exited0. Evidence: `button-action-disconnect-*`
JSON artifacts and `button-action-disconnect-run.log`.

This establishes controller-death teardown and subsequent binding in the same game
process. The worker queue was empty when disconnected; pending-event loss and game
relaunch are separate validation cases. No new runtime DLL was built or loaded.

## Isolated v16 development candidate

Candidate `expedition33-0.1.0-candidate-20261009T165925Z` packages clean source
revision5f0c6e0, including the existing v16 controller/runtime and the
`--button-actions` launcher opt-in. All338 files (including MANIFEST.json) match
the extracted directory and ZIP bytes. Exclusion checks passed; raw evidence,
logs, settings and game data are not packaged. ZIP SHA256:
f14cd0b3c038591f3b743a41788c45904c4a8033584f88634a29bcfde6dd19a7.

Isolated CPython3.13.15 (-I -S -B) ran220 bundled tests successfully, skipping
seven unavailable native-fixture artifact checks. Those native artifacts are not
part of the release bundle. Isolated launcher help and all three menu-backend
selection checks passed without attaching to the game. The DLL/controller are
copies of the unchanged pinned source binaries. Evidence: `button-v16-package.json`,
`button-v16-package-validation.json`, `button-v16-package-tests.log`.

This is an offline-verified candidate, not a new validated release. Live use from
this package after a fresh game launch remains required; current source-session
proof cannot establish which DLL a newly launched packaged controller would load
while another copy is already resident in the game.
