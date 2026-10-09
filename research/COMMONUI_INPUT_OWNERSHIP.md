# CommonUI input ownership investigation — 2026-10-09

Target: Steam build23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
This work uses the existing v13 host and does not add raw input hooks.

## Live observation

`inspect_menu_input_ownership.py` captures current object identities, bounded
reflected descriptors and stored scalar state. It excludes asset-template paths
from its instance inventory. At the main menu in PID21804 it observed one local
player, one player controller, one CommonUIActionRouterBase, one
CommonInputSubsystem and31 instantiated CommonActivatableWidget descendants.
The main-menu root and its TitleScreen child were active; the controller's
stored bShowMouseCursor was true. This is not a complete Slate focus snapshot.
Widget/UserWidget inventories are bounded to64 entries, not total counts.

`inspect_commonui_native_state.py` independently checks the executable hash and
registry identity, then reads only the target-derived native fields. It repeats
the relevant state/header reads and identity checks; it does not pin objects or
claim an atomic GC snapshot. The router's active-root shared reference was
nonnull, but the optional input-config engagement byte was zero. Therefore its
zero mode/capture bytes must not be interpreted as an active configuration to
restore. The absence itself is meaningful and must survive any future snapshot
API. A blanket GameOnly restore would not reproduce this observed state.

## Target code and correlated metadata

| Path | RVA / field | Evidence |
| --- | --- | --- |
| Router class resolver |473dd60 | CommonUIActionRouterBase class, native size170hex |
| Router lookup |4745fc0 | Class-checked local-player subsystem lookup through local-player+138 |
| Diagnostic input state | Router+30 through37 | Mode33, capture34, hide-cursor36, optional engagement37; raw bytes only when absent |
| Diagnostic tree root | Router+88 | Shared reference consumed by the diagnostic tree helper; not a UObject handle |
| ActivateWidget thunk |4795d00 | Checks reflected bIsActive at368hex, then virtual+4e0 |
| DeactivateWidget thunk |4796d40 | Checks the same state, then virtual+4e8 |
| Activation/deactivation virtuals |4772150 /4772170 | Set/clear active state, then virtual+4c8 /+4d0 |
| Activation effects |4774a80 | Optional visibility, optional Enhanced Input mapping, Blueprint event, native and reflected delegates |
| Deactivation effects |4774fe0 | Optional visibility, mapping removal, helper4759e40, Blueprint event and delegates |
| GetDesiredFocusTarget |4797a00 → virtual+4c0 →4774940 | Blueprint event result, then UserWidget focus fallback311eb00 when null |
| RequestRefreshFocus |479aef0 | Broadcasts native delegate at widget+3e0; not a direct focus setter |

The native base default object, live TitleScreen and live main-menu root shared
vtable RVA7a4fe08 and the activation/focus virtual targets above. The router's
vtable was RVA7a530b0. Reflected metadata independently identifies bIsActive,
InputMapping, bIsModal, bSupportsActivationFocus and bAutoRestoreFocus.
These observations do not authorize raw writes to those fields.

The five previously undefined, live-correlated function entries were defined in
the local Ghidra database and saved successfully. No game executable was edited.

## Consequences for the native menu

Investigate an SDK-owned CommonActivatableWidget as the menu's lifecycle owner,
using verified reflected activation/deactivation and existing scoped retention.
First establish the base lifecycle, then viewport/tree membership and focus
restoration before connecting shared management actions. An undisplayed widget
cannot prove input capture or focus restoration. The base class's null desired
focus target also cannot provide keyboard navigation for our controls by itself.

CommonUI's current optional config may be absent even with an active tree. A
restoration design must preserve that condition and respect changes made by the
game while our menu is open. The internal config bytes are research observations,
not a supported public input-state API. No hooks, FKey ownership, delegate
registration or interactive Mods Menu capability is claimed here.

Evidence: `menu-input-ownership.json`, `commonui-native-state.json`,
`commonui-router-lookup.json`, `commonui-activation-thunks-resolved.json`,
`commonui-activation-native-resolved.json`, `commonui-activation-effects.json`,
and `commonui-save.json`. Before-probe copies use
`menu-input-before-activation.json` and `commonui-native-before-activation.json`.

## Owned lifecycle live proof

`verify_live_activatable_widget.py` passed at10:02:04 through the existing v13
console Python host. It created and retained a native base
CommonActivatableWidget, verified that InputMapping was null and initial active
state false, then invoked ActivateWidget twice and DeactivateWidget twice.
IsActivated returned true/true/false/false. GetDesiredFocusTarget returned null.
Final deactivation and scope close restored the exact engine-holder baseline.
No viewport attachment or mapping was requested. Evidence:
`activatable-widget-live.json` and `logs/enum-harness-v13.stderr.log`.

The subsequent native snapshot confirmed the same object identities, router
config bytes, active-root shared reference, vtables and existing menu active
states. A whole-snapshot comparison initially failed because the two menu
objects' registry item_flags changed from4 to1. These changes are preserved,
not erased or described as an identical snapshot; their cause is not established
by this probe. The scoped comparison is recorded in
`commonui-activation-baseline-comparison.json`, with full after-state in
`commonui-native-after-activation.json`.

This proves an undisplayed base widget's activation lifecycle only. Next add a
bounded viewport/tree specimen with a real child focus target and demonstrate
return to the previously focused game widget, including absent router-config
state, before exposing native menu open/close through shared management actions.

## Focus getter/setter boundary

The live Widget descriptors correlate with HasKeyboardFocus RVA31000d0,
HasUserFocus31004b0, SetKeyboardFocus3106fc0 and SetUserFocus310c1e0.
The getter/setter thunks obtain an existing cached Slate reference via30cede0;
that helper attempts weak-to-shared promotion of widget+108/+110, with a fallback
at+f8/+100. It does not construct a widget merely to answer a focus query.
HasKeyboardFocus calls the Slate object's virtual+1a0 and returns false when
there is no cached widget. HasUserFocus additionally validates a local player
controller and resolves its Slate user.

The setters can enqueue a deferred request in the local player's focus machinery
when the immediate Slate request fails. A returned void call therefore does not
prove focus moved; independent getter readback and stale-target/teardown handling
are required. Evidence: `widget-focus-thunks.json` and
`commonui-focus-restoration.json`. The latter also contains deactivation helper
4759e40: its observed body resets per-action timing/hold state and is not proof
of restoring a previous Slate focus owner.

`inspect_live_menu_focus.py` scans keyboard/user focus sequentially over a bounded
TitleScreen subtree, without setters. Its output is a sequence of observations,
not an atomic snapshot or a global Slate focus inventory. Desired focus is
recorded separately from actual focus. The first attempt failed at Python scope
construction before any engine call; explicit scope cleanup corrected that probe.

The corrected scan completed at10:19:08 on game PID21804: all66 sampled widgets
returned false for both keyboard and user focus. ContinueButton was returned as
the desired focus target only. This does not establish absence of focus elsewhere
in Slate, or that opening/closing the native console preserves prior menu focus.
No focus setter or input-mode change was executed. The prepared transfer probe
requires both getters to confirm its explicitly supplied prior owner before it
displays anything; it remains unvalidated. Preserve this distinction when adding
the menu recovery contract rather than substituting desired focus for current
focus. Raw observations: `evidence/main-menu-focus.json`.

## Visible CommonUI lifecycle proof

At10:25:26 on2026-10-09, `verify_live_widget_visible.py` completed on the same
v13 persistent host and game PID21804 with activatable=True, a disabled Button,
and the label "SDK CommonUI lifecycle test". The SDK-owned
CommonActivatableWidget was attached to the viewport and activated; IsActivated,
IsInViewport, text and layout readbacks passed. A live screenshot showed the
blue panel and label over the main menu. The label overflowed its panel, so this
is not finished menu layout or interaction acceptance.

After the bounded45-second observation, deactivation/readback, viewport removal,
RootWidget restoration, label/child removal and exact engine-holder baseline
restoration all passed. A second screenshot confirmed panel removal. No focus
callback, input-mode setter, key mapping or enabled control was used. Evidence:
`evidence/widget-commonui-visible-live.json` and the persistent host log. This
extends the earlier undisplayed activation proof to a visible owned widget tree;
it does not establish CommonUI router integration or focus restoration.

## Console-free focus and viewport identity

`inspect_focus_via_harness.py` completed16 getter requests through the existing
FileService on controller23916/game21804, without opening the console. A preceding
Down key did not activate a menu action. Continue/NewGame/Settings/QuitButton and
their four InternalRootButtonBase children all returned false for keyboard and
user focus. Fresh request UUIDs, exact session matching and preserved responses
prove the owner-thread Harness transport path; no timeout/replay occurred.
Evidence: `menu-focus-via-harness.json` and its listed response IDs under
`settings/E33Introspection/responses/`. This is a bounded sequential sample.

The target's Slate path explains the result. Widget.HasUserFocus calls1542500,
which dispatches via application-base virtual190. Live this resolves to15ed2d0.
That function indexes16-byte user references at application+2f8/count+300, then
calls1641050. The comparison helper obtains the current focused widget through
163dc80: it promotes the last weak reference in user+70/count+78. The keyboard
user mapping virtual8 resolves to10044d0, which returns0.

Read-only native corroboration found one user (index0), a four-widget focus path,
and a last widget with vtable RVA6e78128. Constructor17570e0 installs that vtable;
allocator3228a00 is called with the explicit type string "SViewport" in the
GameEngine, movie player and streaming-pause call sites. GameEngine creation
3709d70 stores the reference at GameEngine+10d0/+10d8. The live focused widget
and reference controller exactly match this GameEngine-held viewport. They also
match the registered viewport weak reference at SlateApplication+398/+3a0.
Thus the observed focus belongs to the game's Slate viewport, not a sampled UMG
button. `inspect_slate_focus_dispatch.py` preserves the corroboration in
`slate-focus-dispatch.json`. Stable repeated reads do not acquire ownership or
constitute an atomic snapshot; these offsets are research, not a callable SDK API.

The reflected WidgetBlueprintLibrary.SetFocusToGameViewport has no parameters
and native entry313faf0. After defining that verified entry in Ghidra, inspection
shows it calls1603dc0 with focus reason2. This helper promotes the registered
viewport, builds its widget path and dispatches application virtual160, live
1603b30. That target iterates eligible Slate users and also updates the stored
fallback focus target/cause. It is therefore NOT a per-user restoration API.
No live setter was called. A bounded transfer specimen may use this path only
after confirming the supported single-user viewport baseline; a general mod
menu still needs per-user ownership, stale-target checks and disconnect recovery.

Evidence chain: `slate-focus-query.json`, `slate-focus-dispatch-functions.json`,
`slate-user-focus.json`, `slate-focused-widget.json`,
`slate-focused-vtable-xrefs.json`, `slate-focused-constructor.json`,
`slate-focused-allocation.json`, `slate-viewport-callers.json`,
`set-focus-game-viewport-schema.json`, `set-focus-game-viewport.json`,
`slate-restore-viewport.json` and `slate-focus-all-users.json`.

## Single-user viewport focus transfer passed

`verify_live_viewport_focus.py` passed on the existing v13 Python23916/game21804
session at10:44:56 on2026-10-09. It required exactly Slate user0, the verified
keyboard-user mapping, and matching current/GameEngine/registered viewport
references before construction and again before the focus setter. It displayed
an owned CommonActivatableWidget with an enabled Button and "SDK focus test"
label, then invoked Widget.SetUserFocus for the live local player controller.

Both HasKeyboardFocus and HasUserFocus returned true for the owned button; a
separate Slate observation no longer matched the original viewport. After an
acknowledged setter, the probe revalidated the viewport identity and single-user
baseline, invoked SetFocusToGameViewport once and verified exact viewport focus
restoration. Both button getters then returned false. After deactivation, viewport
removal, root/child cleanup and exact holder-baseline restoration, another Slate
observation still matched the original viewport. Visual observation confirmed the
panel appeared and disappeared. No input mode, binding or menu action changed.

Evidence: `viewport-focus-progress.json`, `viewport-focus-live.json`, and the
existing persistent host log. `commonui-native-after-focus.json` still shows the
original main-menu/TitleScreen active bits, router root and absent optional input
configuration. These are scoped observations, not a claim of all engine state
being identical. The initial probe stopped before creation/setters because a
reference count changed between read-only observations. The reader now retries
the entire read-only observation at most three times, retaining all identity and
stability assertions. It never retries an engine mutation.

This is normal-close proof for a single-user viewport baseline, not a general
focus API or controller-loss guarantee. Current native backend_close releases
object leases before console detachment; it has no menu-specific restoration or
viewport removal record. Production menu ownership must therefore register a
native cleanup record before transferring focus, and run its guarded restoration
and viewport detachment before releasing owned widgets. Python finally blocks
cannot provide that guarantee after controller termination. Handle changes of
focus to unrelated UI without stealing it back, stale prior targets, multiple
users, mod-scope close and terminal engine teardown explicitly. A native bounded
ownership record and game-thread cleanup tests are the next prerequisite to
shipping an interactive menu; no speculative generic callback should be exposed.

## Native lifetime candidate (offline only)

`native/menu_lifetime.h` adds a durable MenuLifetime record for this cleanup
ordering. Registration binds a session, lifecycle owner and distinct widget/child
lease tokens after read-only target validation. Its protection query is intended
to gate explicit lease release. The record is published before attachment and
focus dispatch; every engine mutation enters an Unknown state before calling the
adapter. Interrupted calls and failed postcondition verification quarantine the
record, preserve protection and forbid replay or reuse.

Close observes current focus, restores only if it still belongs to the owned UI,
then deactivates and detaches before dropping protection. This includes focus
acquired implicitly by attachment/activation. Deferred cleanup keeps its exact
stage; it rechecks focus before a pending restoration and does not repeat already
completed steps. Unrelated focus is preserved. Stale prior targets and terminal
teardown quarantine without speculative engine calls. The target adapter must
validate the game thread/GC/lifetime context and own its restoration data in
native storage; client pointers or callbacks are not part of this contract.

`scripts/test-menu-lifetime.cmd` compiles under MSVC /W4 /WX and passes the
fixture: exact call ordering, foreign owner/session rejection, lease protection,
already-prior/unrelated focus, attachment-acquired focus, deferral before cleanup
and between steps, external focus changes during deferral, interrupted calls at
all five mutation stages, rejected postconditions at all stages, stale targets,
terminal teardown, and close before attachment. Log:
`evidence/menu-lifetime-fixture.log`. These are simulated adapter operations;
they do not validate engine ABI or controller-exit cleanup live.

This header is not yet included in runtime_session.cpp. Remaining integration:
provide the build-verified target adapter; register native records before menu
attachment; gate every explicit protected lease release; close records before
backend_close releases the pool; keep unresolved records/leases pinned; map the
operations through an isolated protocol version; expose mod-scope ownership;
exercise normal close, controller exit, unrelated-focus change and relaunch live.
The full native Mods Menu and key-dispatch feature remains incomplete.

## Native viewport retention and focus adapter candidate

Live read-only corroboration now includes the viewport reference-controller
vtable RVA740a750 and its object/controller destructor entries322bc20/161dae0.
Ghidra confirms322bc20 destroys the embedded viewport at controller+10, while
161dae0 resets the controller vtable and frees the allocation when requested.
The allocation and existing release paths establish strong/weak counts at+8/+c.
Evidence: updated `slate-focus-dispatch.json` and `slate-reference-destroy.json`.

`target_menu_focus.h` implements a bounded native game-thread snapshot and a
TargetMenuFocusOwner candidate. Capture checks GameEngine registration/class,
game-thread/GC/exit conditions, exact application and mapping vtables, exactly
one Slate user, bounded focus arrays, and agreement between GameEngine-held and
registered viewport references. It requires current focus to be that viewport.
It then publishes identities into native storage and retains a concrete viewport
reference through `target_slate_reference.h`. Ownership prevents the captured
viewport/controller allocation from being recycled while the record is live;
subsequent observation still rejects changes in the engine, user or viewport.

`owned_slate_reference.h` tracks acquisition/release in durable states. The target
adapter uses the verified atomic reference operations and exact destructor
entries; interrupted operations are quarantined without replay. Release obeys
the same game-thread/GC/exit gate. MenuLifetime now includes baseline release as
its final guarded stage after detachment and before removing lease protection.
An unattached registered record releases only its captured baseline. Adapter
setup must also clean up a captured baseline if later registration fails; runtime
integration must track that durable storage even before MenuLifetime registration.

Validation: both native fixtures pass under MSVC /W4 /WX; the target focus adapter
compiles. New cases cover the original engine owner releasing its reference,
final-owner destruction, deferred reference release, interruption after increment
or decrement, foreign controller rejection, and deferred/interrupted/rejected
baseline release in the menu sequence. Log: `menu-focus-adapter-build.log`.
The target ownership operations have NOT run inside the live game. No ABI/lifecycle
success is inferred from simulated fixture operations or compilation.

Remaining target adapter work includes verified reflected attachment/focus/
deactivation/removal operations, owned-child focus attribution, protocol capture
and release gates, and backend_close ordering. Native controller-loss restoration
is still unsupported pending that integration and live validation.

## Reflected menu operation adapter candidate

`target_menu_ops.h` now binds ten fixed attachment, activation, focus, query and
cleanup calls to durable native plans. `menu_call_contract.h` constrains each
operation to its target-verified native entry, parameter schema and permitted
target. Registration preflights all live UFunction/FProperty metadata through
the existing reflected dispatcher without executing ProcessEvent. Actual calls
repeat validation and require a returned outcome and appropriate readback.

The candidate requires distinct SDK leases, the exact base CommonActivatableWidget
and Button, child ownership through the widget's WidgetTree, and no assigned
InputMapping. Attachment requires the captured viewport still to own focus;
focus acquisition rejects unrelated UI. Restoration rechecks ownership and
leaves unrelated focus alone. These narrow constraints reflect the successful
specimen, not general CommonUI or arbitrary mod-widget support.

Validation: menu lifecycle and Slate reference adversarial fixtures pass; the
new packet fixture checks all ten contracts, cross-operation substitutions,
invalid outcomes, Z-order bounds, missing player arguments and malformed output
fields. The complete target adapter and existing v13 runtime translation unit
compile with /W4 /WX in an isolated directory. Evidence:
`evidence/menu-ops-adapter-build.log`. The loaded v13 DLL was not rebuilt.

This remains an uninstalled candidate. Native protocol integration, protected
lease-release enforcement, pre-registration baseline cleanup, backend-close
ordering and live controller-loss/relaunch tests remain required. Compilation
and synthetic packets do not establish live cleanup support.

## Native session integration candidate

`menu_session.h` adds durable protection during baseline capture, before
MenuLifetime registration. Rejected registration releases only the prepared
baseline; deferred cleanup preserves the record; interrupted ownership is
quarantined. A new owner cannot reuse the record until complete cleanup.

The isolated E33_MENU_SESSION/v14 path now carries a versioned MenuPacket with
Prepare, Attach, Focus, Close and Status operations. Prepare copies all identities
and ten verified call plans into pinned native storage before acquiring ownership.
The shared IPC mapping is never retained as cleanup storage. The request message
and mapping names are distinct from v13. No controller implementation or installed
v14 binary exists yet.

Runtime integration rejects explicit release of either protected widget lease.
On session close, menu cleanup precedes pool cleanup. A deferred menu keeps
cleanup pending where the existing transport permits; an unresolved menu pins
the entire bounded pool while console/observer teardown continues. A subsequent
session open rejects an active old record. The existing v13 path is unchanged
unless E33_MENU_SESSION is explicitly selected.

Validation: four native fixtures pass, including preparation rejection, deferred
baseline cleanup, ownership interruption, no-replay quarantine and malformed
menu envelopes. The target adapter, existing v13 runtime and isolated v14 runtime
translation units compile under /W4 /WX. Evidence:
`evidence/menu-session-adapter-build.log`. These tests do not exercise actual
engine reference ownership or backend-close behavior inside the game.

Next: implement controller serialization/transport and an isolated v14 build;
validate normal close, protected-release rejection, controller death, unrelated
focus and relaunch. Only then expose interactive menu actions/key dispatch.
General UMG/per-user restoration remains outside the proven single-user
viewport baseline and needs additional target investigation.

## v14 transport built and tested live

Controller-side menu transport now advertises menu_protocol=1, selects the v14
DLL, and exchanges exact-size menu envelopes. Python checks the full capability
chain and reply correlation, preserving returned/deferred/unknown outcomes.
`Session(menu_ownership=True)` selects this experimental backend; it does not
expose a finished Mods Menu. The internal wire API requires the ten plans in
MenuCall order and the native adapter still validates their live metadata.

`build-menu-candidate.cmd` produced isolated v14 DLL/controller artifacts.
Native layout fixtures verify separate v13/v14 mapping/message names, preserved
existing payload offsets, 246608-byte MenuPacket and plans at byte128. All193
Python tests pass, including malformed/cross-request acknowledgements and the
complete transport capability gate. Native lifecycle fixtures also pass.

`verify_live_menu_transport.py` passed against game PID21804, thread38100 and
the verified executable hash: v14 handshake, ping, empty menu Status and normal
session close. No widgets, focus changes or console attachment occurred. The
existing v13 Python23916/probe19188 and Harness UUID5537552beed74b01b66b8a96c7f0d377
remained live afterward. Evidence: `menu-transport-live.json`,
`menu-python-tests.log`, `menu-transport-fixture-build.log`, `menu-v14-build.log`.

Pinned v14 DLL SHA256:
794a396f782560df4561fe63f0edec3ba85806494999d6d0914a61c6b9e7211d.
Controller SHA256:
2daec85e4ffc2cfef248d8eb4d22c240ff7e461fc014388f72fc43b711d1f252.
Do not rebuild/overwrite this DLL while PID21804 remains alive, even though its
test session closed: the runtime module is pinned. Any required native change
needs a cooperative game relaunch or a separately isolated candidate version.

Next live gate: construct owned widget/child plans, prepare native ownership,
attach/focus, reject protected lease release, close and verify exact restoration
and holder counts. Then validate controller death, unrelated focus and relaunch.
The successful empty-session transport test does not establish those behaviors.

## Live native v14 owned-widget close

`verify_live_native_menu.py` now passes against the same verified build/PID21804.
The specimen constructs the existing SDK-owned CommonActivatableWidget, Canvas,
enabled Button and text, then serializes ten live reflected plans into v14.
Prepare, Attach, Focus and Close each return error0. Both widget and button
lease-release attempts return Busy403 while the native record protects them.
The test uses raw release requests so that the intentionally rejected operation
does not revoke the Python lease handles needed for subsequent cleanup.

Independent Slate observation confirms focus leaves the GameEngine viewport and
returns to the exact same viewport after native Close. Reflected readback confirms
the widget is no longer active/in the viewport. Python then removes its owned
tree references/children and releases the remaining scope; the complete strong
holder set exactly matches its pre-test baseline. No input mode was changed.
Evidence: `native-menu-progress.json`, `native-menu-live.json`,
`native-menu-run.log`. This is functional/readback evidence, not a new screenshot
or finished menu appearance claim.

The visible-widget research helper accepts a separate native lifecycle adapter
so the proven construction/layout specimen can exercise native ownership instead
of duplicating Python Add/Activate/Remove calls. It closes the adapter before
changing RootWidget or releasing scoped resources. Unknown native operations are
not retried; the native durable state remains authoritative.

Controller-death cleanup, unrelated-focus behavior and game relaunch still need
their own live evidence. Normal explicit Close is not proof of those paths.

## Live native controller-death cleanup

The separate `verify_live_menu_disconnect.py` run passed. Its worker prepared,
attached and focused another SDK-owned widget through v14, confirmed protected
lease rejection, then killed only its own native controller and exited with
os._exit(23). No Python scope/session finally handler ran. The parent observed
the original GameEngine viewport focus and the exact pre-test strong-holder set
restored on its first post-exit observation. A fresh v14 Session then opened,
reported no active menu record and closed normally. The original v13 persistent
Harness/controller processes remained live.

Evidence: `native-menu-disconnect-progress.json` records acknowledged native
Prepare/Attach/Focus and the deliberate disconnect; `native-menu-disconnect-live.json`
records the constructed objects and baseline before exit;
`native-menu-disconnect-result.json` records independent post-exit Slate/holder
observations and new-session acceptance. `native-menu-disconnect-run.log` records
the successful parent verifier. This proves the single-user viewport-baseline
controller-exit cleanup path on the current process/build. It does not prove
game-exit/relaunch, unrelated focus preservation, general UMG focus restoration,
or recovery from an interrupted engine mutation.

## Scope-owned Python menu API

The v14 lifecycle is now exposed as `scope.prepare_menu(widget, child, player,
z_order=1000)`, returning NativeMenu with `attach()`, `focus()` and `close()`.
The inputs must be already-retained objects belonging to that mod scope; the
helper builds the ten reflected plans from current catalog/schema evidence.
No caller supplies native addresses, offsets or serialized call packets.
`scope.supports_menu_ownership` detects the capability.

The handle is session-owned before native acquisition and remains tracked if
preparation requires deferred cleanup. Mod-scope close closes its menu first,
then releases leases. Deferred menu cleanup and leases remain session-owned for
subsequent poll/close; unknown outcomes abort the controller ownership path and
are never replayed. Explicit release of a protected Python lease is rejected
before sending and preserves its handle for eventual normal release.

Example after creating the supported retained widget tree in the same scope:

```python
menu = scope.prepare_menu(widget, button, player)
if menu.attach():
    menu.focus()
# Explicit close restores/detaches; scope.close() also owns this responsibility.
closed = menu.close()  # False means deferred cleanup; session.poll() continues it.
```

Attach/focus also return False if native context defers them; callers may attempt
that explicitly deferred operation later. Exceptions with unknown outcomes must
not be retried. This remains one menu per session, one Slate user, a captured
viewport baseline and exact base CommonActivatableWidget/Button classes. It does
not create controls, register actions, select input modes, or dispatch keybinds.
SDK lifecycle/transport tests cover cleanup ordering, deferred ownership, foreign
capability rejection, lease-handle preservation and no replay after uncertainty.

Live validation: `verify_live_scoped_menu.py` passes through this API on v14,
including protected Python release rejection with handles still active, native
attach/focus/close, exact viewport restoration and full root/child/holder cleanup.
Evidence: `scoped-menu-progress.json`, `scoped-menu-live.json`,
`scoped-menu-run.log`. All201 Python tests pass in
`menu-ownership-python-tests.log`. Native binaries were not changed or rebuilt.
Live scope-close deferral, unrelated-focus changes and game relaunch still need
their own evidence; the offline scope-ordering tests do not prove those paths.

## Live unrelated-widget focus preservation

`verify_live_menu_unrelated_focus.py` passes on the verified v14 runtime in
PID21804. It opens/focuses the scope-owned CommonActivatableWidget menu, then
constructs an independent, separately retained UserWidget/Canvas/Button tree.
The latter receives SetUserFocus and reports both keyboard and user focus.
Its Slate widget differs from the menu button. Closing the primary NativeMenu
preserves the independent widget's exact Slate widget/controller identities;
both reflected focus getters still return true afterward.

Only after recording that result does the specimen restore the original
GameEngine viewport for cleanup of its independent test UI. Both widget scopes
then restore their root/children and exact strong-holder baselines. Final Slate
observation confirms viewport focus. The test changes no input mode or game
settings and performs no action/keybinding registration.

Evidence: `menu-unrelated-focus-progress.json` records the distinct focused
widgets, identity-preserving close, viewport restoration and passed result;
`menu-unrelated-primary-live.json` and `menu-unrelated-secondary-live.json` record
the independent scope lifecycles and holder baselines;
`menu-unrelated-focus-run.log` records normal completion. This is live evidence
for preserving another widget's focus during close, not proof of arbitrary
CommonUI routing, multiple users, deferred scope cleanup or game relaunch.
