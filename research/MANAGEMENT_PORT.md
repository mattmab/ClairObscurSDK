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
