# Unified management harness: source audit and feature matrix

Updated2026-10-08. Status: shared registry/settings/actions and console frontend
implemented; no E33 native menu or general keybind implementation is claimed. The existing E33 console and Introspection
Harness remain operational. The full additional request, including all17 live
acceptance tests, is preserved locally in USER_REQUEST_MANAGEMENT.txt.

2026-10-09 widget progress: v9 base UserWidget creation, same-operation retention,
stable serial publication, viewport add/remove and explicit release passed live
through persistent console Python, restoring the exact holder baseline. This fixes
the lazy serial boundary exposed by the earlier v8 specimen. See WIDGET_OWNERSHIP.md.
CanvasPanel/Button construction and child attachment/removal now also passed
through the persistent v9 host, including retained CanvasPanelSlot identity and
exact holder cleanup. v10 now also passed root assignment/readback, stale-value
rejection, viewport add/remove and explicit root restoration, with exact holder
cleanup. Native menu rendering, focus lifecycle and general key dispatch remain
unfinished; the lifecycle specimens are not a native Mods Menu.

The RootWidget setter uses the reusable session/mod-scope assign_object API
and target-verified engine assignment path (WIDGET_OWNERSHIP.md). The persistent
management host now runs v10. Original Harness scalar ObjectProperty set also
passed live through a fresh adapter instance sharing that host. The controlled
handover to the isolated v10 package now passed: the normal persistent Harness
imports the updated adapter and advertises scalar ObjectProperty set. The
packaged widget-root assignment/viewport/restoration specimen also passed with
exact holder cleanup. Fresh-game startup and normal game exit now also passed
with the repaired v10 package (DEVELOPMENT.md records the discovered timeout and
the successful retest). Next implement
visible control layout and validated focus/key handling. See DEVELOPMENT.md for
package evidence and INTROSPECTION_PORT.md for the exact set boundary.

Layout follow-up: WIDGET_LAYOUT_VALUES.md records live parameter/struct metadata
and Ghidra thunk evidence for Vector2D, LinearColor, Margin and Anchors.
The opt-in v11 transport now invokes these profiles through its game-thread
schema gate. Position/size round trips and margin effects passed live on an
SDK-owned child; anchors/color dispatch returned and holder cleanup passed.
The original Harness's typed `$struct` adapter is implemented separately; see
INTROSPECTION_PORT.md for validation. A disabled native Button now rendered live
inside an SDK-created CanvasPanel/UserWidget at the expected position and size.
The bounded specimen removed its viewport entry and child, restored RootWidget
and returned every holder to the exact baseline. See WIDGET_LAYOUT_VALUES.md.
Text/font ownership, enum input modes and focus restoration remain
separate required capabilities, not assumed consequences of the numeric codecs.
Next add owned text values and usable labels, then connect controls to the shared
registry/actions with verified input/focus restoration. The visible specimen is
not yet a functioning Mods Menu or a general keybind implementation.

The v11 source host/game completed normal exit with all exit codes0. Isolated
candidate20261009T075928Z then loaded its own DLL into a fresh Steam launch and
passed the original Harness typed-value probe with exact holder cleanup. The
persistent management/console host now runs from that package. See DEVELOPMENT.md
for the source revision, hashes, process identities and evidence.

Owned-text follow-up: target constructor/copy/reference-count/destructor paths
are now correlated with the text conversion thunks. A reusable candidate native
ownership helper passes43 offline lifecycle/fault checks and its actual adapter
compiles with/W4/WX. It is not yet connected to transport or live widgets. See
WIDGET_LAYOUT_VALUES.md for the exact boundary and integration gates. The running
v11 package and its console remain unchanged during this work.

Text transport prerequisite: a separate candidate envelope and Python codec now
pass native/cross-language validation, including bounded UTF-16 and existing
object-result lease correlation. All163 Python tests pass. It remains disconnected
from the public session and running game; native dispatch/lifecycle integration
and live labels are the next gates. No new menu capability is advertised yet.

The native candidate now connects an ownership-aware durable text frame to the
actual reflected dispatcher through an explicit optional callback table. Offline
fault/quarantine tests and v5/v11 compile compatibility pass, as do163 Python
tests. The runtime has not opted in yet: the next step is session/controller and
planner integration, followed by live text round trips and TextBlock labels.
Existing console, packaged lifecycle and numeric layout behavior are unchanged.

The isolated v12 candidate now builds with its own session/mapping and full text
controller transport. Native session storage owns the text frame across failures;
normal cleanup, deferred close and quarantine/reopen rejection are wired. Internal
Python transport gating and compiled layout checks pass (167 Python tests total).
Public text planning/result decoding and live handover are still pending. No v12
code has been loaded into the running game and no live text/menu claim is made.

Public v12 text invocation now passed live (08:52:18 local): SDK-owned TextBlock
ASCII/Unicode/empty SetText/GetText round trips, invalid input rejection, and
the original Harness's copied-text retain/reuse/release behavior. Exact scoped
holder cleanup passed; v12 is the current persistent source host after a clean
v11 handover. See WIDGET_LAYOUT_VALUES.md. Visible labels, actions and focus/key
handling remain unfinished; no native Mods Menu is claimed by this text probe.

The v12 visible specimen now rendered an actual two-line TextBlock in the
SDK-created panel. Text readback after Slate creation, viewport removal, root
restoration, both child removals and exact holder cleanup passed at08:58:56.
This supplies a verified native label building block. The original BL4 menu's
context-dependent input/focus restoration still needs an E33-specific contract;
its blanket ignore-input resets are not adopted without ownership tracking.

The v12 package now also passed a fresh Steam launch and native-console-driven
original Harness text probe, including exact holder cleanup. The source game
and both controllers exited normally with code0 before this launch. The current
persistent management host runs from candidate20261009T125943Z; see DEVELOPMENT.md.
Next input dependency: the target's GameAndUIEx/UIOnlyEx thunks describe
InMouseLockMode as a one-byte EnumProperty referencing EMouseLockMode with a
ByteProperty underlying field. That metadata does not yet authorize enum calls:
verify members and the native schema gate before connecting focus transitions.

Native UEnum member observation now passed live for EMouseLockMode and ENetRole,
including native stale-identity/wrong-type rejection. The reusable source API is
`expedition33.enums.describe_enums`; see REFLECTION.md for target derivation and
limits. This establishes mouse-lock values without guessing, but the invocation
codec and owned input/focus restoration remain the next gates. The running v12
package has not been changed, and neither input mode nor focus was mutated.

The original Harness schema now includes bounded enum member metadata and passed
live against GameAndUIEx. A candidate native byte-enum schema/membership gate
passes24 fault/identity/context cases; it remains disconnected from dispatch.
Next connect explicit enum identity/value planning and versioned transport, then
validate a bounded call before applying the menu's input/focus ownership policy.

Typed enum planning and candidate version4 retained wire now pass Python/native
validation, including a packet derived from the live GameAndUIEx schema. No enum
call was dispatched. Session/dispatcher integration and focus restoration remain
next; the existing packaged v12 host and original Harness invocation are unchanged.

V13 session/dispatcher and public capability integration now compile and pass
offline checks (184 Python tests plus native gates and compatibility). It is
isolated from the running v12 package. Live enum dispatch, Harness enum argument
adaptation, focus restoration and clickable management controls remain pending;
see WIDGET_LAYOUT_VALUES.md for the exact candidate and next validation steps.

V13 now passed live typed ESlateVisibility Hidden/Visible round trips on an
SDK-created Button, raw-integer rejection, child removal and exact holder cleanup.
The cooperative v12 handover completed and source v13 is the current persistent
console/management host. No widget was displayed and focus/input mode was unchanged.
The original Harness enum argument/result adapter and native interactive menu
remain next; see WIDGET_LAYOUT_VALUES.md for the preserved first-attempt test error
and successful corrected run.

## Preserved implementation references

Primary source is the installed BL4 sdk_mods directory. Nineteen original files
(including three complete archives, native keybind module, wrappers/stubs,
menu source/tests and crash notes) are copied unchanged under
`D:/HobbyDevelopment/Analysis/ClairObscurSDK/bl4-management-original-20261008`.
Archives were extracted there with path containment checks. The local manifest
`evidence/management-source-manifest.json` records original paths and hashes.
No BL4 original was edited or imported into the Expedition33 controller.

| Reference | Observed version/provenance |
| --- | --- |
| MattsBL4ModsMenu | 1.3.3; installed archive SHA256 9d27ef6a2761612cf02a5ae698668fdd324e550bbd96b80e479709799dcf7b18; entry point, workspace, policy and pyproject exactly match local package source |
| console_mod_menu | 1.6; installed archive SHA256 145bec5ace3e884058435472973759c6c29dfce69adc22176c9ae10968d17eb5 |
| mods_base | 1.12; installed archive SHA256 16d8cd0da9870af849eae3831922507df3eab66ede2e9420933067000f42c2e8 |
| keybinds | Installed Python wrapper1.1, .pyi and keybinds.pyd preserved; no local native C++ source found in the searched SDK source/development directories |
| Oak2 startup | Actual installed sdk_mods/__main__.py preserved; discovers/imports mods and initializes framework/input dependencies |

MattsSDKModsMenu is not assumed to be a separate implementation: the located
package is MattsBL4ModsMenu. Additional source-name searches remain part of the
audit. The BL4 SDK has both this native menu and console_mod_menu installed;
they use mods_base rather than separate mod registries.

Supplementary native input reference:
[Oak2 keybinds.cpp](https://github.com/bl-sdk/oak2-mod-manager/blob/d606e796733eced318e2a44e51b871a7becae55e/src/keybinds/keybinds.cpp),
cloned for inspection at that exact commit under the D: Analysis directory.
This source is not asserted to match the installed binary. MattsBL4ModsMenu is
MIT; mods_base and Oak2 carry LGPL3. Preserve source licenses if reusing code.
Our framework implementation remains independent and does not load these SDKs.

## Observed architecture and differences

The native menu entry point constructs UserWidget, WidgetTree and CanvasPanel
objects with a controller/HUD outer, sets the root and viewport geometry, then
adds the overlay at a high Z order. NativeUMGFactory builds children in one tree.
workspace.py installs presentation behavior over that runtime: searchable lists,
filters, inspector, native scroll panels, actions, options, keys, themes, text
scale and launcher placement. It is not merely a wrapper around a BL4 asset.
This BL4 construction path remains unverified on Expedition33.

Input is more involved than an InputKey hook: a camera-modifier POST hook polls
buttons, sliders, text and rebinding. It also hooks BL4-specific menu-open/close
paths and narrow PRE input handlers. Rebinding polls IsInputKeyDown because
InputKey hooks were unreliable while native UMG owned focus. Native press/release
button state has a manual hit-rectangle fallback; scroll children use native hit
testing. The toggle is unbound by default. Identity matching synchronizes separate
display and runtime keybind objects before persistence; our registry should avoid
creating those duplicate sources of truth.

Input restoration differentiates gameplay from an underlying pause/title menu.
The source adjusts cursor/block/look/move flags and invokes WidgetBlueprintLibrary
input/focus helpers plus BL4 UI-state commands. Those resets are not transferable
without verifying E33 ownership; resetting all input flags could overwrite another
menu's state. Preserve and restore only the state owned by our menu.

The 1.3.3 crash note attributes reopening crashes to retained destroyed scroll
widgets. The fix drops all tree-owned references and hit rectangles, skips scroll
reads without a canvas and stops polling after callbacks rebuild a tree. Its note
explicitly says live BL4 reopen validation was pending. Do not relabel those source
tests as live proof. E33 needs generation checks and safe engine ownership, not
Python exception handlers around stale native pointers.

Oak2 console_mod_menu has a screen stack, numeric selection, back/quit/redraw,
metadata/status, options and keybind screens. It repeatedly captures the next
console line regardless of content through mods_base.command. That behavior
must change to preserve E33 engine and Python routing. Its optional press-to-bind
screen imports keybinds.raw_keybinds and ui_utils, degrading on ImportError. The
installed keybinds package exposes registration handles, not that optional module.

mods_base owns one mod list and loads settings on registration. Mod enable and
disable register/remove commands, hooks and keybinds around lifecycle callbacks.
Libraries/enabling_locked entries have distinct lifecycle policies. Options include
bool, slider, spinner/dropdown, button, hidden, grouped/nested and keybind adapters.
JSON persistence stores enabled/options/keybinds by identifiers; the inspected
default writer has neither versioned migration nor atomic recovery. Those are
additional requirements for our implementation, not capabilities to claim copied.

The supplementary native Oak2 keybind code detours GbxEnhancedPlayerInput InputKey
using a configurable vtable index default85 and a BL4 FInputKeyParams layout. It
matches FNames/events, skips OakPlayerController cursor-visible states, copies
callbacks before invocation, catches exceptions and can synchronously return Block.
None of its index/layout/classes is accepted as E33 evidence. E33 Python is external:
input suppression must be a bounded native policy installed in advance; it must
not wait for a Python callback round trip on the game thread. Modifier combinations,
capture contexts and reliable focus filtering require additional verified work.

## Feature parity and implementation matrix

| Capability | Reference behavior | E33 implementation requirement/status |
| --- | --- | --- |
| Registry | mods_base.mod_list shared by native and console UI | Stable-ID registry attached to loader; generations revoke stale selections; console path live-tested |
| Installed/loaded mods | Startup discovery plus registered mod objects | Existing folder loader is minimal; expose discovery separately from loaded/enabled status |
| Lifecycle | Enable/disable hooks, keys, commands; protected core/library entries | Shared loader Session with per-mod resource scopes implemented; resource sharing live-tested, full multi-mod loader/relaunch validation pending |
| Metadata | Name, author, version, description, type, custom status | ModDefinition and copied UI views; name/author/version/description/protected policy/error status implemented |
| Values | Bool, slider, selections, hidden/grouped/nested settings | Typed bool/int/float/choice/text values, bounds/defaults/callbacks implemented; grouping/hidden/nested presentation pending |
| Buttons/actions | Option callbacks, native workspace actions | Shared owner-thread dispatcher with generation/enabled checks; Introspection status/roots/request adapter implemented |
| Persistence | Per-mod JSON, enabled/options/key mappings | Versioned store, atomic writes, previous-generation recovery and stale-writer rejection unit-tested; runtime integration/migrations pending |
| Console entry | mods command with screen stack | SDKManagement registers UMG-independent `mods ...` navigation; opened live in native console |
| Console controls | Selection, enable/disable, edit, button, bind, back, quit | Selection/load/unload/enable/disable/options/actions/back/quit implemented; rebinding pending native input work |
| Native presentation | Search/filter/inspector, scrolling, themes, scale, launcher placement | Pending E33 UMG backend using shared definitions; preserve reference usability where practical |
| Native widgets | Runtime-built one-tree overlay | Verify construction/viewport/GC ownership; evaluate asset-backed fallback using CONSOLE_DUMPS.md leads |
| Focus | Cursor, move/look suppression, UI-mode/context restoration | Pending owned focus lease; close/failure/travel must release it without resetting unrelated owners |
| Key registrations | Names/defaults/event filters, opaque handles | Pending SDK-level stable action IDs and owner/generation scoped registrations |
| Input capture | BL4 native detour and menu polling fallback | Pending target-derived E33 input path and key/device identifiers; no borrowed vtable index |
| Remapping | By name or captured key; unbind; reset | Both frontends must edit the same mapping and retain console recovery |
| Conflicts | Native policy reports enabled duplicate keys | Pending deterministic context-aware conflict handling; no silent replacement |
| Modifiers/devices | Installed API single key/event; native params include gamepad | Keyboard/mouse required; controller/modifiers where verified; explicitly report unavailable capabilities |
| Cleanup/reload | Deregistration, native stale-widget fix, optional rlm helper | Generation invalidation, reverse cleanup, no duplicate callbacks; no blind importlib.reload of active hooks |
| Introspection | Separate Explorer, protocol, console commands | Keep existing core unchanged; register management metadata/actions through an adapter |
| UMG failure | Native open catches failures/restores input | Console/shared runtime must survive UMG absence, widget loss or deliberate disable |
| Packaging | Native menu sdkmod and framework modules | One installable management mod, reusable SDK primitives, isolated bundle validation pending |

## Shared model and work order

One controller owns the native transport and persistent Python runtime. Each mod
receives a scoped resource owner, not another independently attached Session.
The loader remains authoritative for lifecycle transitions; the registry exposes
that state rather than another mutable enabled flag. Stable IDs identify mods,
options, actions and bindings; generation tokens reject stale callbacks/UI rows
after unload/reload. Views contain data and IDs, never native widget pointers.

The shared dispatcher validates owner, generation, enabled policy and arguments
before invoking a callback on the Python owner thread. Engine-facing operations
still use the verified game-thread transport. Settings and rebinding use the same
validation/persistence path for both UIs. Keybinds refer to action IDs so keyboard,
mouse/controller, console and UMG cannot diverge into separate callback registries.

Next implementation sequence:

1. Finish the remaining audit details (factory/option edge cases, reload adapters,
   full workspace controls, startup discovery) and record source-specific gaps.
2. Build the shared registry/settings/action primitives and scoped runtime
   ownership, with failure/unload/reload tests. Keep the active user console intact.
3. Implement the console management component on those primitives and integrate
   Introspection without making management depend on Explorer.
4. Verify E33 input capture/suppression and add configurable bindings. A registered
   mapping alone is not proof of live key dispatch.
5. Add UMG using the same registry and dispatcher; validate focus/ownership and
   deliberate UMG failure independently from console availability.
6. Complete all17 user acceptance tests, lifecycle/relaunch and isolated packaging.

The complete17-test unified acceptance gate remains incomplete. The borrowed-session
console milestone below proves a limited subset, not UMG or relaunch behavior.
The earlier Introspection parity requirements remain active alongside this matrix.

## Shared resource ownership milestone

PROVEN2026-10-08: SessionScope resources share an existing native Session.
Scopes wrap fixed getter calls/hooks and console commands/exposures, revoke their
callbacks before cleanup, remove only their own handles and reject calls after
close. Exposed names are removed only if their values have not been replaced by
the user. This is cooperative lifecycle ownership for trusted mods, not isolation
from malicious Python or revocation of arbitrary user-created aliases.

ModLoader now creates one Session for enabled mods, closes it after the last
scope is disabled, and contains second-mod enable failures without closing an
existing mod's transport. poll() drains console/events once and pumps enabled
mods; it handles the last mod being unloaded by a console action. The single-mod
my_mod convenience name never replaces another mod's existing binding.

All47 Python tests pass, including simultaneous registrations, failed second
enable, stale scopes, repeated enable/disable and last-mod unload during polling.
The live in-game Python command ran scripts/verify_live_scopes.py against PID34604:
two scoped callbacks observed the first fixed getter call, closing the first
left the second receiving the next call, and closing both restored the command
set and left the original session callable. evidence/shared-scopes-live.json and
the persistent controller log preserve the result (one/two observed events).

The running introspection host was not replaced or reloaded. This live test proves
scope resource behavior on its existing Session, not a complete multi-mod loader,
relaunch or packaged-runtime pass. The loader changes apply to a future host
start. Registry/settings/actions, general keybinds and both management frontends
remain next work; no unified-menu acceptance gate is claimed by this milestone.

## Shared settings primitive

IMPLEMENTED and unit-tested: expedition33.settings.SettingsStore supplies the
single persistence path for future management frontends. Version1 records contain
stable lowercase mod/option/action IDs, a revision, option values, key mappings
and an enabled preference. Preferences do not themselves change runtime state.
Unregistered mods' records survive writes to another mod. Getters return defensive
copies so a UI cannot mutate stored state by editing a returned dictionary.

save(mod_id, record) validates finite bounded JSON, writes and flushes a temporary
file, then atomically replaces the destination. The last accepted generation is
stored as .bak. Malformed primary data recovers that previous generation when
valid; recovery is reported and the damaged primary is preserved as .corrupt.UUID
before a subsequent save. A future format version is rejected without downgrade.
This is previous-generation recovery, not a promise that the latest failed write
survived. Oversized files and unreadable files fail rather than bypassing bounds.

An exclusive short-lived writer lock plus disk fingerprint prevents cooperating
controllers from silently overwriting stale snapshots. An abandoned lock is not
silently removed or replayed; later runtime recovery must verify writer state.
No migration from existing BL4 settings or future-version migration is implemented.
Key-name strings remain preferences, not evidence of supported engine inputs.

All54 Python tests pass, including seven filesystem tests for round-trip records,
defensive copies, corruption recovery/preservation, future versions, stale/locked
writers, failed replacement and invalid/duplicate-key data. This primitive has no
engine dependency and was not claimed as live UI or relaunch validation. Registry
option callbacks, keybind application and console/UMG integration remain pending.

## Shared registry and live console milestone

IMPLEMENTED: ModDefinition, Option and Action in expedition33.management. ModLoader
registers metadata after trusted import, rejects duplicate stable IDs, and removes
registry entries on unload. Enabled state is derived from the loader; actions are
unavailable during enable/disable transitions. Each lifecycle transition changes
a generation token. A frontend must reselect after another owner changes a mod.
Callbacks execute on the external controller owner thread, with bounded JSON
arguments, exception containment and recursive dispatch rejection. Engine-facing
work still goes through the existing verified Session APIs.

Settings validation supports bool, bounded int/float, scalar choices and text.
Saved options apply after enable. A failed application triggers enable cleanup.
While enabled, an edit persists before calling the mod: disk failure leaves the
runtime untouched; callback failure reports that the preference was saved but
application failed. There is no automatic replay or claimed runtime rollback.
Disabled mods can have preferences edited without invoking their callbacks.
Automatic enabled-preference restoration, migrations and grouped option UI remain
pending; loading metadata executes trusted Python but does not enable the mod.

SDKManagement is the protected management mod. It uses ConsoleMenu on the same
registry and supports list/select/load/enable/disable/unload/options/set/reset/
actions/action/back/quit/help. Only `mods` is intercepted; every navigation line
must start with it. There is no next-line capture. The Introspection mod exposes
status, roots and the existing JSON request handler through Action definitions;
its Explorer core remains unchanged and management has no Explorer dependency.

PROVEN2026-10-08 on live PID34604 using scripts/verify_live_management.py:
the temporary candidate loader borrowed the existing host Session (no reattach,
host reload or native rebuild). Real native-console input opened `mods`, selected
ManagementExample, enabled its native getter hook, saved label "Live menu
persistence", invoked the getter action, unloaded the mod, loaded a fresh instance,
restored its setting and invoked the action again. The original instance received
one event and the fresh instance one event: no duplicate/stale callback delivery.
An invalid numeric label was rejected visibly, preserving the prior setting.
Persistent `py` input remained available with a mod selected. Final verification
rejected the original stale selection, removed the temporary harness, restored
the original command/hook sets and called the getter on the original host again.

Evidence: evidence/management-live/443843224acf496683598f262b874ded/result.json,
preferences.json and logs/persistent-console.stderr.log at19:42:01. Console output
and errors were also inspected in game. The old Introspection host continued its
heartbeat; it was intentionally outside this temporary loader's registry. This
test does not prove full startup integration of that older running instance.

All63 Python tests pass. `launch.cmd management` adds the new integrated startup
path with SDKManagement and Introspection on one loader and settings/management.json.
That new launcher path, native UMG, key dispatch/rebinding, fresh-process relaunch,
controller reconnection, and an isolated updated bundle still require live tests.
The existing private v0.1 archive is unchanged. General key support is not inferred
from stored strings, and the console help explicitly identifies the missing backend.

## Integrated host and cooperative shutdown — 2026-10-08

PROVEN on the same game PID34604: the older controller completed its active
command, unloaded Introspection and detached normally before the reader update.
The new persistent management host PID27468/session1764cfbee60a449eaf74b16706e558d7
registered both sdk.management and sdk.introspection. Native backtick opened the
console; `mods`, selection and `mods action status` worked. The file client also
returned live World/GameInstance/LocalPlayer/PlayerController roots.

The new `mods action shutdown` on sdk.management returned its confirmation at
20:01:37 before cleanup. The launcher logged detach; Python27468 and its transport
39364 exited, while game34604 remained alive. This is a cooperative flag checked
after dispatch, not transport closure from inside a callback. A custom host must
honor stop_requested and exit its loader context itself.

Replacement persistent host31328/session6d53cbc6934347bdb4d4763f3e2938f4 attached
at20:03:07. Its file client enumerated live roots again, and native-console
`py print(6 * 7)` displayed42. A first sandboxed launch attempt did not persist;
it had no attach log or remaining host/transport and was not counted as a success.
The replacement runs hidden without a duration limit. Evidence is in
evidence/management-handover.json, management-reconnect.json and
logs/management-host-1.stderr.log / management-host-3.stderr.log.

All68 Python tests pass. Same-process controller restart is now proven; native
UMG, general key dispatch/rebinding, game relaunch and updated isolated packaging
remain pending. Console action output currently needs more readable formatting.

## Live widget/input schemas and call-path audit — 2026-10-08

The dump leads were resolved against the identity-checked live catalog on34604.
All12 targeted UStructs were present: Widget, UserWidget, WidgetBlueprintLibrary,
WidgetTree, PlayerController, InputSettings, EnhancedInputUserSettings,
CommonUIActionRouterBase, InputCore.Key, and the game ControlsPage,
MappingOptionEntry and InvisibleModalInputBlocker generated widget classes.
Fifteen relevant UFunctions were described, including creation, viewport add/remove,
focus/input-mode setters, key events and IsInputKeyDown. Evidence:
evidence/management-live-schemas.json. None was invoked by this investigation.
Presence of a loaded generated class does not prove safe widget construction.

The exact live UFunction entries were matched to Ghidra code:

| Function | Entry RVA | Observed parameter contract and path |
| --- | --- | --- |
| WidgetBlueprintLibrary.Create | 31361b0 | 32-byte parameters: WorldContextObject0, WidgetType8 constrained to UserWidget, OwningPlayer16, return24. Thunk parses FFrame arguments, checks the class, and chooses ownership/context-specific creation paths. It is not a plain C++ function taking that parameter buffer. |
| UserWidget.AddToViewport | 31355b0 | int32 ZOrder,4-byte parameters. Thunk resolves a viewport subsystem and forwards widget/slot information. |
| SetInputMode_GameAndUIEx | 31401e0 |19-byte parameters inside a24-byte reflected extent; PlayerController0, widget8, lock-mode enum16, bools17/18. Thunk obtains a Slate widget reference, dispatches controller virtuals and conditionally flushes input. |
| PlayerController.IsInputKeyDown | 3b27180 |25-byte parameters inside a32-byte extent:24-byte Key then bool return24. Thunk copies reference-counted key state, reads controller+408 and calls143ddc5b0 when non-null. |

These are static code observations correlated with live metadata, not callable
SDK contracts or validated new offsets. Ghidra responses are preserved in
evidence/management-function-thunks.json. In particular, InputCore.Key reflects
only the8-byte KeyName within24 bytes; the thunk's reference-count operations
show why an arbitrary copied/zero-filled FKey cannot yet be treated as a valid
owned argument. Parameter size and allocation extent also need distinct handling.

Next primitives: bounded reflected struct observations (for key/mapping data),
verified FKey construction/destruction or engine-owned key lookup, general
identity-checked game-thread invocation, then widget creation/retention and focus
restoration. Continue with CommonUI routing evidence before input suppression.
No game settings, input modes, widget instances or mappings were changed here.

Follow-up: reflected struct reads now decode ConsoleKeys and the nested Key
members in default action/axis mappings (see INTROSPECTION_PORT.md). The live
default console keys are Tilde and²;154 action mappings and39 axis mappings were
observed, with the action prefix bounded to64. This provides inspectable input
configuration through reusable SDK primitives. It does not prove active mapping
contexts, enable arbitrary key dispatch, or solve FKey argument ownership.
Next: verify engine-owned key construction/lookup and general game-thread calls;
keep the existing console recovery path available during input-hook development.

Invocation follow-up: argument planning now checks the live Create, game-only
input-mode and IsLocalController descriptors without executing them. It preserves
object identities as symbolic patches and rejects unsupported FKey arguments.
The native dispatch packet, game-thread revalidation and result lifetime remain
the next implementation steps; the Python planner cannot yet create a widget.

Additional target evidence:143ddc5b0 looks up key state by FName in PlayerInput and
releases the copied key's control block. Cleanup1413dca00 operates on Key+10;
predicate141405190 calls lazy initializer1413dd470, which fills Key+8/+10 via
1413ded40 when details are absent. This identifies the ownership-bearing fields
beyond reflected KeyName. It does not yet prove a universal constructor contract
or authorize borrowing/copying those pointers. Evidence:
evidence/invoke-lifetime-paths.json and key-details-path.json.
# Invocation progress — 2026-10-09

The transport is now accessible to scoped mods and the persistent Harness through
the opt-in v6 host. The live console-to-Python-to-Harness-to-engine getter passed.
See INVOCATION.md. Native UMG ownership/focus and keybind acceptance remain open.

An isolated v6 game-thread dispatcher passed the live read-only
Controller.IsLocalController specimen and rejection checks. See
INTROSPECTION_PORT.md for the exact tested boundary. This removes the missing
transport/dispatcher prerequisite for further menu experiments; it does not yet
validate Create/AddToViewport, retaining widgets, restoring focus/input mode, or
FKey ownership. The existing v5 `mods` fallback and Python console were restored
and checked after the candidate closed. Native UMG and key dispatch acceptance
gates remain open. Next: typed output handling and object ownership, then a
bounded widget lifecycle specimen before connecting shared management actions.

## Native ownership follow-up — 2026-10-09

See WIDGET_OWNERSHIP.md for target-derived Create/viewport/Slate/GC paths and
the read-only live corroboration of1,124 SObjectWidget holders. A separate
SDK-owned GC holder is the next retention candidate. Its collector ABI,
synchronization and teardown contract still require verification; no widget
creation, retention, focus change or key dispatch is claimed. Keep ownership
registration inside the eventual create operation to avoid a Python round-trip
GC gap. Shared console management remains usable while this work continues.

The follow-up found an existing generic24-byte engine strong-reference holder,
including its exact constructor sequence, collector callback and destructor.
Three live instances corroborate its layout. A native candidate adapter and
lifecycle fixture now compile/pass; no SDK holder has been registered live.
Prefer this target mechanism over a custom SObjectWidget-derived holder. See
WIDGET_OWNERSHIP.md for the remaining lease, fault-recovery and live-test gates.

Follow-up: experimental v7 leases now have live registration/release and
controller-exit cleanup proof (OBJECT_LEASES.md). Next connect scoped leases and
retain Create's output before returning it to Python, then test a bounded widget
lifecycle and input/focus restoration. The UMG-independent console management
host was restored and Python execution verified after the isolated test.

Mod resource scopes now expose explicit existing-object leases. Live closing of
one scope removed only its holder; another scope's reflected getter still worked.
The persistent management host runs v7 with `--leases`, and console-driven lease
creation/context-manager release passed. Next native step remains atomic
invocation-output ownership, then a widget lifecycle/focus specimen.

The v8 native retained-invocation specimen now retains a real object output before
Python acknowledgement and removes its holder on explicit release/session close.
The next integration is a public owned-result wrapper and Harness lifecycle,
followed by the bounded Create/add/remove/release widget specimen. Native menu,
focus recovery and actual key dispatch remain unimplemented. The persistent v7
console management host was restored after testing; see OBJECT_LEASES.md.

Public v8 result ownership and original Harness retain/release/expiry now have
live evidence, including two independent mod scopes and exact holder cleanup.
The launcher exposes `management --retained`. Shared native ownership is now
available for the bounded widget lifecycle specimen; native UMG, focus handling
and key dispatch remain pending. See OBJECT_LEASES.md for limits and proof.

## Current UMG prerequisites — 2026-10-09

Subsequent v9-v13 work now provides verified object output ownership, scalar
object assignment, selected numeric layout structs, owned text and typed byte
enums. The original Harness can invoke these supported paths and retain/reuse
their results; enum JSON and existing text paths passed together in the live v13
host. See WIDGET_LAYOUT_VALUES.md for exact proof and remaining package gates.

The next interaction prerequisite is a reversible input/focus ownership contract.
Target inspection shows the registered CommonUI diagnostic wrappers constructing
and discarding their output (CONSOLE_DUMPS.md). Investigate the action-router
helpers/state rather than assuming those commands provide a usable snapshot.
Native Mods Menu controls, input restoration and real key-event dispatch remain
unimplemented; the existing shared registry and console fallback remain available.

CommonUI follow-up: COMMONUI_INPUT_OWNERSHIP.md records the actual live main-menu
root/TitleScreen activation and an absent optional router input config despite a
nonnull active tree. The SDK-owned, undisplayed CommonActivatableWidget lifecycle
now passes repeated activation/deactivation and exact holder cleanup. Input-mode
bytes from an absent optional must not be used as a restoration snapshot. Next
verify viewport/tree integration and a real child focus target with restoration
to the game's prior focus owner. This is not yet native menu interaction or key
dispatch acceptance.

The subsequent read-only TitleScreen focus scan completed66 widget observations
with no keyboard/user focus reported. Its desired ContinueButton is not a proven
restoration target. Before enabling interactive native controls, establish focus
outside the console transition and handle an absent/unresolvable prior owner.
Keep native key-event dispatch gated on this ownership contract; the shared
registry/console fallback and typed Harness invocation remain the usable paths.

The next bounded specimen passed live: a visible SDK-owned CommonActivatableWidget
with disabled Button and text activated, displayed, deactivated and removed,
restoring RootWidget/children and the exact holder baseline. Visual appearance
and disappearance were observed. Focus restoration, actionable controls, router
integration and key dispatch remain pending; the label's panel overflow is also
not a finished layout. See COMMONUI_INPUT_OWNERSHIP.md for evidence and limits.

Console-free Harness getter calls plus target-derived Slate observations now
identify the actual current focus owner as the GameEngine-held SViewport. Native
menu recovery must support both viewport and UMG focus, not substitute the menu's
desired button. SetFocusToGameViewport is reflected and its static implementation
verified, but affects multiple eligible Slate users and fallback focus state.
Next validate an explicitly single-user viewport-to-owned-child-to-viewport
specimen with readback and exact cleanup. General per-user/disconnect restoration
and real key dispatch remain separate acceptance gates.

The single-user viewport focus specimen now passes live: the owned button gains
keyboard/user focus, SetFocusToGameViewport restores the exact prior viewport,
and restoration survives widget removal with exact holder cleanup. This used the
existing v13 reflected invocation paths and no input-mode changes. Before exposing
interactive native menu open/close, add native ownership/cleanup records so
controller loss restores/detaches before object leases are released. Python-only
finally cleanup is insufficient. Per-user/UMG restoration, unrelated focus
changes, actions and key dispatch remain pending. See the proof and cleanup
ordering discussion in COMMONUI_INPUT_OWNERSHIP.md.

A native MenuLifetime candidate now implements the ordered close/protection
state machine and passes adversarial offline adapter tests. It is not connected
to the live session. The next implementation gate is the target adapter plus
protocol/backend lease-release enforcement, followed by controller-loss and
relaunch validation. Do not count this candidate as native cleanup support yet.

The target operation adapter now compiles with fixed, independently verified
reflected calls, pre-attachment schema validation and unrelated-focus protection.
Its packet, lifecycle and reference fixtures pass; the v13 runtime also compiles
unchanged at its existing call sites. This advances the native menu prerequisite
identified by the console dumps, but remains uninstalled until protocol and lease
release gates are integrated. The shared console fallback and Harness remain the
usable management paths; actionable native controls and key dispatch are pending.

Native v14 candidate integration now tracks pre-registration baseline ownership,
offers a separate menu request envelope, protects explicit lease release and
orders menu cleanup before pool cleanup on controller disconnect. Deferred or
uncertain records block reuse. Offline failure-path/request fixtures and v13/v14
compilation pass. Controller transport and live v14 cleanup/relaunch acceptance
remain pending; this is not yet an installed capability. Keep the existing v13
Harness/console session until an isolated candidate is ready for handover.

v14 controller serialization and Python request/reply validation are implemented;
193 Python tests and native fixtures pass. The isolated DLL/controller now pass
a live empty-menu transport handshake/status/normal-close smoke test alongside
the unchanged v13 host. Native widget ownership/cleanup remains unvalidated live.
Next run the owned-widget specimen through v14, followed by disconnect and
relaunch acceptance; do not count transport-only proof as Mods Menu support.

The v14 owned-widget specimen now passes live Prepare/Attach/Focus/Close,
protected-release rejection, reflected removal/deactivation and exact
root/child/holder cleanup. A separate controller-death run bypasses all Python
cleanup and proves native restoration to the same viewport, exact holder cleanup
and an empty fresh v14 session. Both preserve the existing v13 Harness host.
This establishes the narrow native lifecycle prerequisite for reusable menu
ownership. Next validate unrelated-focus and game-relaunch behavior, integrate
ownership into mod scopes, then add actionable controls and real key dispatch.
General per-user/UMG focus restoration is still unsupported.

Scope-owned Python menu lifecycle is implemented and live-tested through
`prepare_menu`/`attach`/`focus`/`close`; mod scopes own cleanup before leases and
session polling retains deferred cleanup. Protected release rejection preserves
Python handles. All201 tests pass and the public scoped specimen restores exact
focus/root/child/holder state live. Next gates remain unrelated-focus/relaunch,
actionable controls, shared registry rendering and actual key-event dispatch.

The unrelated-focus close gate now has live evidence: an independent UserWidget
button takes focus, closing the primary native menu preserves that exact Slate
widget/controller and both keyboard/user focus getters, then both test scopes
clean up to exact holder baselines and restore the viewport. Game relaunch and
deferred scope cleanup remain separate gates. Native actionable controls,
shared-registry presentation and key dispatch are still incomplete.

Button action investigation now establishes the actual live/static callback
chain (BUTTON_EVENTS.md): OnClicked is a multicast field, and the owned SButton
uses a weak-UObject native delegate whose click method broadcasts that field.
The signature entry is shared dispatch, while IsPressed is only a state query;
neither supplies a verified click event hook. Live constructed-button storage
matches the derived delegate layout and the specimen cleans up exactly. Delegate
cloning copies the callback pointer, so a single-slot swap/restore is insufficient
proof of teardown. Next choose and verify an owned delegate/receiver mechanism
with bounded transport events and persistent Python dispatch before adding menu
actions. No button callback hook or action registration is implemented yet.

The SButton reference-controller allocation and destruction path are now traced,
with a compile-tested exact-build ownership candidate sharing the existing
durable reference state machine. It validates the live Button/delegate chain
before capturing an independent Slate owner, which is needed to unregister an
event adapter before detaching widgets. Actual SButton retention and callback
delivery still require isolated native/live validation; cloning remains a
separate unregistration constraint. See BUTTON_EVENTS.md.

The v15 candidate now integrates SButton retention into menu ownership and passes
live normal attach/focus/close with native Live/Empty state acknowledgements,
viewport restoration and exact holder cleanup. The Python opt-in is
`Session(button_references=True)`; v14 stays the default menu backend. All203
tests pass. Next validate the additional reference during controller loss and
relaunch, then implement a callback mechanism with verified cloning/revocation.
No click action, general key dispatch or completed Mods Menu is claimed.

The v15 controller-loss gate now passes with Python cleanup deliberately bypassed:
native cleanup restores the exact viewport/holder baseline, and a fresh v15
session has an empty menu and Empty0 SButton reference. Game relaunch remains a
separate gate. The launcher exposes `--menu-ownership` and `--button-references`,
and development candidates include the v13/v14/v15 DLL/controller pairs.
Candidate byte/manifest/isolated-help validation does not establish live bundle
acceptance. Next implement cloning-aware callback revocation and bounded action
delivery before connecting native controls to the shared registry. General key
dispatch still needs verified FKey ownership and input/focus policy.

Button input research now confirms that the click helper executes the stored
delegate directly. Both inspected clone paths reconstruct the engine vtable,
so an instance-vtable adapter can leave copied delegates engine-native by keeping
the original member-function pointer. Destruction/reuse and complete ABI/table
verification remain gates before installation. The bounded native action queue
candidate passes offline revocation, overflow, reentrancy-ticket and session
isolation fixtures. Next connect a verified adapter and transport to persistent
Python action dispatch, then build shared-registry controls. See BUTTON_EVENTS.md;
no live menu actions or key dispatch are claimed by this step.

The exact13-slot delegate table and both execution ABIs are now checked against
target assembly. The new candidate lifecycle core passes offline reentrant-close,
destructor/free, foreign-replacement and interrupted-mutation tests, while
preserving all original clone slots. Next supply pinned forwarding callbacks and
the retained-delegate target adapter in an isolated runtime version. IPC/Python
action routing and actual input validation remain required before registry UI
controls can be considered usable. Existing loaded runtime binaries are unchanged.

Native forwarding candidates now pass Windows fixtures for unchanged reply bytes
and return pointer, optional-execute success filtering, reentrant revocation,
late-thunk passthrough, real SEH and exactly-once destructor forwarding. A worker
thread verifies passthrough with an atomic fault latch rather than unsafe queue
access. Target Ops and every runtime control/drain path must honor that permanent
latch before this is publishable. Live input, transport/Python action delivery and
the shared-registry UI remain unimplemented; fixture success does not establish
live menu functionality.

Target-specific adapter validation and module-pinned immutable table preparation
now compile against the existing retained-button infrastructure. Installation
requires the captured identity and exact13-entry engine table; the control gate
fixture revokes pending events without touching freed storage after a latched
thread fault. Runtime publication, teardown ordering, IPC and Python action
delivery remain the next integration gates; this compile-tested adapter has not
been installed in the game.

The v16 action-owner candidate is integrated into both explicit menu close and
controller-loss cleanup before menu restoration/detachment/reference release.
Deferred and quarantined action cleanup blocks further release. Separate v16
message/mapping names isolate the candidate from v15; existing packet layout is
still unchanged and action IPC is pending. Three fixtures, target compilation,
v15/action-runtime compilation and v16 layout execution pass. Next expose bounded
bind/drain operations and persistent Python dispatch, build the isolated runtime,
then validate actual clicks and cleanup. No live action support is claimed yet.

The native v16 bind/drain/unbind/status packet and runtime command108 are now
implemented. Binding is restricted to the current attached/focused menu's owned
button and leases. A close-intent gate prevents re-registration during deferred
action/menu teardown. Strict packet and lifecycle fixtures pass; the v16 packet
now includes the action payload. Next add controller serialization, Python
validation/dispatch and the isolated runtime build before live click testing.

Controller serialization and the standalone Python action decoder are now in
place. A native-generated packet decodes correctly in Python, five protocol tests
pass, and v15/v16 controller/runtime paths compile. The decoder rejects foreign
session/owner events and discards uncertain outputs. Next wire v16 selection and
capability negotiation into Session, then scoped callback registration and poll
dispatch with saved registration/action and cross-drain sequence checks. Live
clicks, unregister/disconnect/relaunch and multi-control menu rendering remain
unvalidated.

v16 Session selection and transport gates now pass213 Python tests. The isolated
DLL/controller also pass a live handshake/empty-menu/absent-owner-rejection/normal
close smoke test on PID21804. No callback was bound. The v16 DLL is now pinned and
must not be rebuilt until that game exits. Next add scoped Python action handles
and poll dispatch, then validate owned-button input and cleanup live. Packaging
and release acceptance for v16 remain separate from this transport-only proof.

Menu-owned Python callbacks and Session.poll dispatch are implemented;220 tests
pass. The live v16 specimen now proves bind/empty-drain/unbind/rebind and closing
with an active registration, followed by exact viewport/reference/holder cleanup.
Actual mouse/keyboard action delivery remains untested. Next exercise real input
and persistent Python callbacks, then controller death/relaunch before using this
path for shared mod registry controls. The loaded v16 DLL was reused unchanged.

## Native action frontend bridge

The registry now provides `action_callback(selection, action_id, argument)` for
`menu.bind_action(...)`. This connects the verified native button transport to the
same action dispatch used by the console frontend. Captured arguments are isolated;
every click rechecks generation and enabled state. An old queued click cannot
reach a newly loaded instance. Native ownership remains with ButtonAction/menu,
so registry dispatch does not introduce another cleanup system.

Three new offline tests cover actual ButtonAction event decoding into registry
invocation, unload/reload rejection, menu-close revocation, immutable argument
snapshots and binding validation. All20 targeted management/button tests pass.
Live adapter validation, multiple controls and keyboard dispatch remain pending.

### Live registry-button validation — 2026-10-09

`verify_live_management_button.py` passed in game16344. Three separate real mouse
clicks exercised the shared registry: the original mod received one copied JSON
argument; after unload/reload, the still-bound old selection raised ManagementError
without invoking either instance; after explicit unbind/rebind, the replacement
received exactly one invocation. The error remained in ButtonAction's failure
history. The visible labelled button was removed, viewport focus restored, root
and children removed, and exact native holder baseline restored. The borrowed
loader closed; the outer Session and probe exited normally with code0.

The previous packaged management host was first closed through native-console
`mods select sdk.management` / `mods action shutdown`; retained process handles
confirmed Python16692 and controller24140 both exited0. Game16344 stayed running.
The probe used source Python23876/controller7140 and the already-resident v16
runtime. This is a live source-adapter test, not a new package/relaunch test.
The persistent source management/Harness host was then restarted normally.

Evidence: `management-button-progress.json`, `management-button-widget-live.json`,
`management-button-run.log`, `management-button-package-exit.json`, and the immutable
per-run result under `evidence/management-button-260f9a3ddd794df3b6d8af8aa70a25ea/`.
No gameplay, keyboard activation or multi-control menu was exercised. The next
UI gate remains multiple independently owned controls and keyboard input ownership.

### Multiple-control lifecycle gate passed — 2026-10-09

The v17 backend now passes live independent blue/green mouse callbacks, selective
callback removal, focused-control removal, and forced controller loss while the
second control owns focus. A fresh controller rejected stale ownership, bound two
new controls, selectively rebound one, and closed with exact viewport focus,
WidgetTree root/children and native holder restoration. See BUTTON_EVENTS.md for
the failure/fix history and raw evidence. The original persistent host closed
cooperatively before the failure test; only the disposable test controller died.

The next frontend work can use these verified primitives: reusable widget
construction and labels, a mod list and details from Registry.views/view, and
generation-checked callbacks for actions/settings/enable state. Reuse a bounded
set of controls for paging instead of allocating new Slate controls for every
refresh: focus ownership retains at most16 distinct controls per menu lifetime.
Native menu acceptance, configurable keybind input routing, and Harness parity
remain incomplete; these lifecycle probes are not the finished Mods Menu.

### Registry-backed native presentation — 2026-10-09

`management_view.ManagementView` now supplies immutable native-menu frames for
registered/installed mods, search, details, enable/disable, settings, actions,
unload and navigation. It reads the existing Registry on every render; it owns
only selection, paging and presentation status. Editor descriptors carry the
actual setting kind, value/default, bounds and choices. Submitted values still
go through Registry validation/persistence/callbacks, as console edits do.

The original preserved BL4 workspace's list/inspector and settings/actions
behavior informed this presentation. Its scroll widgets, BL4 input resets,
theme machinery and hit-rectangle fallback have not been copied. The initial
E33 renderer can page eight rows through at most12 persistent controls, below
the verified16-control lifetime limit; full layout, scrolling, themes, filters,
text editors, sliders and key-capture parity remain explicit follow-up work.

Every render/navigation revokes old frame tokens before dispatch. Registry
generations additionally reject clicks spanning unload/reload. Callback argument
snapshots are copied, unavailable/core controls reject activation, and failed
actions produce status text without replacing the console fallback. Six new
tests exercise real loader/registry/settings behavior, stale events, paging,
typed editor metadata, reset, callback failures and protected controls. All244
Python tests pass. This is an offline-tested presenter, not a rendered or live-
tested management menu. Next connect reusable owned UMG widgets to these frames,
then validate actual mod selection/actions/settings and reopen/cleanup live.

### Native renderer candidate — 2026-10-09

`widgets.OwnedMenuPanel` now constructs a reusable owned UMG tree through the
verified reflected base classes, numeric layout, copied text, typed visibility,
root assignment and native menu lifecycle APIs. It uses no research-script
imports or separate controller. Twelve buttons and their labels are reused
across presenter pages. Native close must finish before root restoration,
child removal and scoped lease release; uncertain mutation outcomes prohibit
automatic retries and preserve the owner for session cleanup.

`management_native.NativeManagementMenu` connects presenter frames to the v17
control pool. Input is revoked before refresh/removal and only re-enabled after
every new binding succeeds. Old queued callbacks carry the old frame identity.
Boolean settings toggle and choices cycle through registry-declared values;
actions use the same registry dispatcher. Text/numeric/JSON input editors,
sliders and key capture are pending. The existing console remains independent.
This candidate is not yet wired into the management mod's startup/lifecycle.

Six additional tests exercise renderer navigation/settings, revoked callbacks,
deferred teardown, native-before-tree-before-lease cleanup, and unknown-outcome
retention. All250 Python tests pass. The first live construction began at14:37:25
in persistent game21568/controller host33780 using `my_mod.registry`; it is not
yet a successful live acceptance test. `verify_native_management_state.py`
captures exact focus/holder baselines before and after this interactive run.
The older shell attempts without src on sys.path failed before querying the game;
their native-menu-before-* files are not the baseline. The authoritative new
baseline is `evidence/native-management-before.json`, captured by persistent Python.

#### Renderer latency investigation

The first live construction advances about one control per57 seconds. A separate
read-only `profile_widget_planning.py` run on the same PID measured a full catalog
(96075 objects,102528 native rows) at2.714 seconds. Planning SetIsEnabled and SetText
each took about0.356 seconds; SetBackgroundColor took0.701 seconds because its
LinearColor descriptor adds another query. No engine functions were executed by
the profiler. Raw evidence: `evidence/widget-planning-profile.json`.

Session.invoke/invoke_retained currently capture the complete catalog for every
call, plus another capture for object results. A panel control needs two objects,
two slots, layout calls, visibility/text and color operations. This explains much
of the observed initial construction cost; it is not yet acceptable menu-open
latency. Read-only timings are not a complete runtime profiler or a speedup claim.

Future optimization should reuse bounded planning observations or prepared calls
while preserving native game-thread identity/schema/context gates and same-call
object-result retention. `reflected_invocation.h` checks these gates immediately
before dispatch, including field offsets/types/extents and argument constraints;
text allocation triggers further identity/context revalidation. This supports
investigating reduced external catalog traffic, not skipping native validation.
Do not retrofit a new dispatch path into the currently running construction.

### First actual native management interaction — 2026-10-09

The first full tree finished construction at14:50:10 and returned an open frame
at14:51:35 on game21568 / persistent Python33780. This run used the renderer
from e32fc60. The native panel visibly listed the enabled Introspection Harness
and SDK Management plus the installed ConsoleExample, ExampleMod and
ManagementExample folders. Real mouse clicks selected the Harness, opened its
actions screen and invoked Port status through the same Registry used by the
console. The status result appeared in the panel. Native Tilde/Python remained
usable while the panel was open.

`evidence/native-management-action.json` preserves frame revision7, the original
Harness status result (parity_complete False), panel state open, uncertain False,
native event sequence9 and empty failure lists for current bindings. It was
written from the persistent console at14:55:41. The before baseline remains
`native-management-before.json`. A close-button attempt was interrupted by
physical user input, followed by the user stopping Computer Use with Escape.
No after baseline exists. Do not claim that this full renderer's close, exact
cleanup, reopen, disconnect, relaunch or settings editing has passed live.

Observed defects: first opening took about14 minutes; navigation repainted over
tens of seconds; descriptions/results overflowed horizontally; labels inherited
disabled tint; unused buttons remained visible as empty rows. These prevent a
release-quality menu even though construction, navigation and a Harness action
are now demonstrated. Source-only follow-up bounds row labels, wraps/caps detail
text, logs full display content, removes disabled tint from hit-test-invisible
labels, and collapses unused rows via target-described enum members. Visibility
updates cache only complete success and preserve unknown outcomes on partial
failure. These visual changes have NOT been applied to or verified in the live
instance. Native scrolling/responsive metrics, editors, keybinds and fast planning
remain open work; text truncation is explicitly indicated rather than hidden.

### Shared invocation planning candidate — 2026-10-09

`Session.invocation_planner()` and `SessionScope.invocation_planner()` now capture
one shared catalog for explicitly prepared retained calls. `prepare()` reads the
function metadata against that observation; `bind()` prepares a new argument
snapshot without changing the original. Each invocation still uses the existing
native identity/schema/context gates and retained-result acknowledgement path.
Object results still require fresh catalog capture and same-call native leases.
The planner owns no UObject and does not retry rejected or uncertain operations.
Refresh (including failed refresh) and close revoke older prepared calls. Session,
scope and Python owner-thread checks remain enforced.

Example with previously resolved, target-build-verified identities:

```python
with sdk.invocation_planner() as planner:
    call = planner.prepare(label, set_text_function, InText="First")
    with call.invoke():
        pass
    with call.bind(InText="Second").invoke():
        pass
```

Keep the planner alive while using its calls. Refresh explicitly when newly
created objects must be resolved, then prepare replacements for revoked calls.
Use a mod's SessionScope factory so returned leases follow that mod's cleanup.

`NativeManagementMenu(sdk, registry, cached_planning=True)` enables a single
scope-owned planner after successful tree construction and before first paint.
Only text, enabled-state and visibility rendering use this candidate path;
construction and teardown keep their existing invocation paths. The default is
still uncached pending live comparison. Close revokes the planner after native
menu/tree cleanup and before releasing the scope. A partial visibility update
still latches uncertainty; there is no fallback that could replay a mutation.

Validation: 266 offline tests pass, including prepared text argument rebinding
without another catalog scan, independent object-result leases, decode failure
cleanup, native rejection, malformed acknowledgement abort, successful/failed
refresh revocation, foreign-process rejection, wrong-thread rejection, scope
cleanup and cached-render dispatch failure. An initial suite run without the
project environment failed on sandbox temporary-directory permissions; rerunning
with `scripts/project-environment.ps1` uses the required D: temporary directory.
No new DLL was built or loaded and the current live host was not modified.

Live prepared calls, repaint speedup and this renderer's full close/reopen remain
UNVERIFIED. This candidate does not solve the approximately 14-minute initial
construction time. Next performance work must measure this repaint path and
reduce construction scans without weakening identity or ownership validation.

### Construction planning candidate — 2026-10-09

The optional `cached_construction=True` argument on NativeManagementMenu and
OwnedMenuPanel now uses shared planning during widget creation and layout, and
keeps that planner for repainting. Defaults remain unchanged pending live proof.
Each successful retained object return already captures a fresh full catalog;
`PreparedInvocation.invoke(refresh_from_result=True)` reuses that exact decoded
catalog for the next preparation, avoiding a second scan. No entries or class
relations are synthesized for newly created widgets. Scalar-only calls reuse
the existing observation and do not imply a new capture.

This option revokes all prior prepared calls before dispatch. A native rejection,
unknown acknowledgement or failed result conversion leaves the planner without
a catalog, requiring an explicit refresh. Returned-object ownership still comes
from same-call native leases, including scope adoption. Teardown continues to use
ordinary fresh invocation, and does not depend on cached plans.

272 offline tests pass. Added coverage checks reuse of a catalog containing a
newly returned object, one result scan, old-plan revocation, capture failure,
rejected dispatch with an existing owner, construction uncertainty without
fallback, and frontend opt-in routing. Live construction timing remains pending.

### Full initial renderer close and controller handover — 2026-10-09

After the user explicitly resumed Computer Use, a real Close-button click
removed the e32fc60 renderer from the viewport. The persistent console then ran
`print(native_menu.panel.state, native_menu.panel.uncertain)` and
`menu_evidence('after')`. At15:11:17 the host reported `closed False` (closed
state, uncertainty false), and exact baseline verification passed. Raw evidence:
`evidence/native-management-after.json`, compared with the preserved before file.
The verified focus is the same game viewport and the complete retained-holder
map matches. This closes the previously missing normal-close check; it does not
prove relaunch or disconnect behavior of the full renderer.

The original host exited0 after the cooperative registry shutdown command at
15:11:54. A fresh source host started15:12:20 with the same pinned v17 binary.
`scripts/benchmark_native_management.py` is called from that persistent console
with a caller-owned `native_menu`, so failed construction does not lose the
cleanup owner. It saves before-state, completion/failure, duration and uncertainty,
and provides a separate exact-baseline close check. The cached-construction
candidate began at15:13:30. Timing/visual/lifecycle results follow when complete.

### Cached-construction live result — 2026-10-09

PROVEN on the same game PID21568 with fresh source Python36472/native15856:
`NativeManagementMenu(sdk, my_mod.registry, cached_construction=True)` opened in
297.6137235 seconds. The previous uncached run took approximately850 seconds;
these are consecutive development observations, not a controlled statistical
benchmark. Repeated controls took approximately19.6 seconds versus56.8 seconds.
The object-result capture and unchanged native gates remained active throughout.
Loaded v17 DLL SHA256 remained
`20711AF456865C0A27BC98CE2562E710D0E95D4AB32E863B6063B423FD8B6B9D`.

Real mouse clicks navigated Harness details -> Actions -> Port status. The
original Harness result appeared in the panel and SDK log at15:19:39. Visual
inspection confirmed brighter labels, wrapped descriptions, collapsed unused
rows, and an explicit 'More text in the SDK log' footer for the long result.
The panel remains a rough prototype over the main menu; scrolling, responsive
metrics, input editors, keybinds and full lifecycle integration remain pending.
Navigation works but was not precisely timed in this run.

A real Close click detached the panel. A subsequent persistent Python console
call to `bench['verify_closed'](native_menu)` passed at15:21:50: state closed,
uncertainty false, same PID and exact viewport identity, viewport focus restored,
and the complete retained-holder map equal to the pre-build baseline. The
controller remains alive and native/Python console input was demonstrated after
close. Raw evidence: `evidence/native-management-cached-open.json`,
`evidence/native-management-cached-after.json`, and
`logs/native-management-cached-host.log`. The earlier full renderer's independent
before/after evidence was preserved.

The candidate materially reduces construction cost but five-minute opening and
slow ordinary teardown remain unacceptable for release. Reopen/relaunch,
full-renderer controller-loss cleanup, gameplay transitions and updated packaging
are not established by this test. Cached options remain explicit while those
validation gates and further performance work are open.

### SDK Management service integration candidate — 2026-10-09

`NativeMenuService` now gives SDKManagement explicit ownership of the native
frontend. The existing `mods` command routes `ui`, `ui open`, `ui close`,
`ui refresh` and `ui status` to that owner. It uses the same Registry as the
console and loads no second controller. The multi-control capability is required;
unsupported hosts retain console management. Ownership is assigned before
construction, so a failure does not discard the cleanup handle. Failed refreshes
revoke input and suspend automatic refresh rather than retrying mutations.

The controller polls copied public registry state at most twice per second.
Changed mod state refreshes the open native view and revokes prior controls.
SDKManagement closes its frontend before unregistering its console commands.
Nested SessionScopes now own child scopes while sharing the actual root Session:
child close preserves siblings and the parent; parent close revokes children
before its own resources. Prepared invocation uses the root transport and adopts
results into the appropriate child scope.

282 offline tests pass, including child ownership, cleanup errors, prepared
results, actual SDKManagement load/disable, command routing, unsupported hosts,
registry refresh, construction/refresh failures and deferred cleanup. This is
source-only integration; no loaded native binary was changed. A live source host
started at15:28:21 and passed the pre-open baseline check at15:29:45. The ordinary
`mods ui` command started construction at15:32:41. Live integration acceptance is
pending until open, registry refresh and exact close-baseline checks complete.

Numeric/text/JSON editors, general keybinds, full-renderer controller-loss and
relaunch validation, responsive layout and updated packaging remain pending.
Synchronous menu work still delays Python command processing, although engine
operations remain on the verified game thread and the game continues rendering.

### Integrated service live acceptance — 2026-10-09

PROVEN in game21568 with the unchanged pinned v17 runtime: native console
`mods ui` completed at15:37:38 (296.568 seconds from the logged start). At15:38:21,
`service_evidence('open', my_mod)` verified an open service, exactly one child
scope, the shared registry and preserved mods/Harness command registrations.
The native console remained available over the panel.

At15:38:58, `mods load ManagementExample` loaded the trusted local example's
metadata without enabling its engine hook. The visible native list automatically
changed from ManagementExample [not loaded] to Management Example [disabled],
alongside the still-enabled Harness and SDK Management. No manual refresh or
second state store was used.

The ordinary `mods ui close` command removed the panel and completed cleanup at
15:41:03. At15:41:21, `service_evidence('after', my_mod)` passed: service
not_created, zero child scopes, exact original game viewport and retained-holder
map, viewport focus restored, shared registry and command registrations retained.
The same persistent Python session executed the post-close check. Raw artifacts:
`evidence/management-service-before.json`, `management-service-open.json` and
`management-service-after.json` under evidence, plus
`logs/native-management-service-host.log`. The example remains loaded but disabled.

This validates the normal integrated command lifecycle and registry refresh,
not full-renderer controller death, reopen/relaunch, gameplay transitions or a
new package. Five-minute construction and slow cleanup remain release blockers.
282 offline tests pass. GitHub metadata independently confirmed private=True and
visibility=private using the existing authorized Git credential; the connector
itself returned404 for this private repository. No visibility setting was changed.

### Shared teardown planning — 2026-10-09

Panels with an existing invocation planner now refresh it once after native
menu detachment, root restoration and readback, then prepare child removals from
that observation. Each removal still goes through the native retained-invocation
identity/schema gates. Children stay leased until removal succeeds. A refresh
failure leaves children and leases owned; an uncertain dispatch latches the
existing no-retry state. Uncached panels retain their previous path. This replaces
one full pre-call catalog scan per child with one teardown planning scan; root
restoration and readback retain their separate validation.

285 offline tests pass, including removal ordering, one refresh, no uncached
fallback, refresh failure preserving ownership, and unknown replies preventing
repeat mutation or premature lease release. The previous host exited0 normally;
fresh source host started15:45:12 against the unchanged resident v17 DLL.

PROVEN on game21568: `verify_cached_panel_cleanup.py` built a caller-owned
two-control panel under SDKManagement's scope. Its labels appeared in the real
game and the native console remained usable. At15:48:44 the close measurement
returned11.240466699993704 seconds, state closed, uncertainty false, no remaining
children, exact retained-holder baseline and exact original viewport focus.
Raw evidence: `evidence/cached-cleanup-before.json`,
`evidence/cached-cleanup-after.json`, `logs/cached-cleanup-host.log`.

This is functional validation of the changed teardown path on six canvas
children, not a same-size before/after benchmark, full 12-control menu timing,
disconnect/relaunch coverage or a packaging claim. Full-menu timing and the much
larger widget-construction cost remain open performance gates.

### Bounded selected-catalog reader — 2026-10-09

Read-only profiling of the live catalog returned96054 objects in2.9245 seconds;
about2.15 seconds was spent waiting for the native reader and its output.
The profile is preserved in `evidence/catalog-cost.prof`. Object-return capture
is therefore a material remaining construction cost, beyond Python planning.

The independent reader now supports `--catalog-select PID INDEX:SERIAL:ADDRESS`
(comma-separated selectors), exposed as `catalog.capture_selected(pid,
identities)`. It accepts1–1024 selected identities and expands their current
outer, class, metaclass and superclass dependencies, bounded to16384 objects.
Every dependency must be registered and its identity must still match when
emitted. The same executable fingerprint, anchors, object headers, class size,
inheritance and end-count checks remain active. This produces a self-contained
partial catalog; it does not merge stale observations, pin objects, enumerate
all live objects or authorize calls. There is no full-scan fallback on failure.

PROVEN on game21568 by `scripts/verify_selected_catalog.py`: the live main-menu
PlayerController selected closure contained19 objects. All selected object and
class rows exactly matched an independent full96054-object capture; the full
Unreal path also matched. Full capture took2.7657038 seconds and selected capture
0.3462925 seconds in this run. Changed serial, address and process selectors were
each rejected. Evidence: `evidence/selected-catalog-live.json`. The native reader
built successfully and289 Python tests pass, including incomplete dependency
graphs, incorrect selectors/process, input bounds and no-fallback behavior.

Only the standalone reader executable was rebuilt. The resident v17 DLL and
its controller binary were untouched. Retained-result decoding and menu creation
still use full captures; adopting selected result closures needs explicit
planning-observation semantics and same-call lease/decode failure validation.
No menu opening speedup or updated package is claimed from this reader test.

### Selected retained-result observations — 2026-10-09

The planner now has explicit `selected_results=True` support. Same-call native
leases are adopted before reading returned identities and their dependency
closures. Compatible observations are combined without refreshing untouched
rows or granting them authority. Recycled identities and changed class relations
fail; there is no automatic full-read fallback or mutation retry. Native dispatch
gates remain mandatory. Capture/decode failures release newly acquired leases.

The first live specimen exposed an important boundary: Create initializes a
WidgetTree child outside the returned UserWidget's outer/class closure. Planning
rejected the next CanvasPanel spawn before dispatch. The partial owner closed
successfully with exact holder/viewport/focus baseline restored, followed by a
cooperative controller shutdown. Evidence: `logs/selected-results-host.log` and
`evidence/selected-results-{before,after}.json`.

The fix adopts the full observation already used to read WidgetTree through
`InvocationPlanner.refresh_from(catalog)`, revoking older plans without another
read. A fresh controller built and displayed the corrected two-control specimen
on game21568 in57.4468428 seconds. Normal close took11.0655405 seconds, left zero
children, reported no uncertainty, and restored exact retained-holder and
viewport baselines plus viewport focus. The native console remained usable.
Evidence: `logs/selected-results-v2-host.log` and
`evidence/selected-results-v2-{before,open,after}.json`.

All296 Python tests pass, including selected capture failure, output lease
cleanup, recycled overlaps, changed class relations, scoped/null results and
explicit observation revocation. This opt-in is validated on the bounded
specimen only. Full management service adoption, full-menu timing, relaunch
coverage, general keybinds and updated packaging remain pending. The resident
native DLL was not rebuilt or replaced.

### Full service selected-result validation — 2026-10-09

SDKManagement's NativeMenuService now enables selected retained-result reads
for its full 12-control panel. The public frontend also accepts the explicit
selected_results option. Registry, native input and ownership paths are unchanged.

PROVEN on game21568 with a fresh source controller: full service open took
169.0852387 seconds, compared with296.568 seconds in the preceding full service
run. This is approximately43% less opening time in these main-menu observations;
it is not a responsiveness or gameplay benchmark. Native mouse navigation reached
Introspection Harness -> Actions -> Live roots. The original Harness returned
the actual World, game-specific GameInstance and PlayerController, LocalPlayer,
and empty Pawn list. The bounded display showed the result and the complete
result was logged. Native Close removed the panel. A subsequent persistent
Python command verified closed state, no uncertainty and no remaining children
before releasing the service's completed owner. Exact retained-holder and
viewport baselines, viewport focus, zero child scopes, shared Registry and all
four console commands were verified. The same persistent Harness answered status
afterward and still correctly reports parity_complete=false.

Evidence: `logs/management-selected-host.log` and
`evidence/management-selected-{before,open,after}.json`. All296 source tests pass.
Source README timing is updated; the existing private package remains unchanged.
Further performance work, native editors/keybinds, full-menu controller-loss and
relaunch coverage, original general traces and agent bridge remain incomplete.
