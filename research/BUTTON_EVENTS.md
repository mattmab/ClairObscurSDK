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
