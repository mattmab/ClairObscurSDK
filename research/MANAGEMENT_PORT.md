# Unified management harness: source audit and feature matrix

Updated2026-10-08. Status: source audit and design; no E33 native menu or general
keybind implementation is claimed. The existing E33 console and Introspection
Harness remain operational. The full additional request, including all17 live
acceptance tests, is preserved locally in USER_REQUEST_MANAGEMENT.txt.

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
| Registry | mods_base.mod_list shared by native and console UI | Pending stable-ID registry attached to one runtime; do not duplicate enabled state |
| Installed/loaded mods | Startup discovery plus registered mod objects | Existing folder loader is minimal; expose discovery separately from loaded/enabled status |
| Lifecycle | Enable/disable hooks, keys, commands; protected core/library entries | Shared loader Session with per-mod resource scopes implemented; resource sharing live-tested, full multi-mod loader/relaunch validation pending |
| Metadata | Name, author, version, description, type, custom status | One definition and immutable UI views for both frontends |
| Values | Bool, slider, selections, hidden/grouped/nested settings | Pending shared typed validation, defaults, change callbacks and stable option IDs |
| Buttons/actions | Option callbacks, native workspace actions | Pending one action dispatcher for UI, console, keybind and introspection adapters |
| Persistence | Per-mod JSON, enabled/options/key mappings | Versioned store, atomic writes, previous-generation recovery and stale-writer rejection unit-tested; runtime integration/migrations pending |
| Console entry | mods command with screen stack | Pending UMG-independent management component; use owned `mods ...` navigation to avoid capturing arbitrary engine/py lines |
| Console controls | Selection, enable/disable, edit, button, bind, back, quit | Preserve capabilities with clear help/errors and stale-selection rejection |
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

All17 new acceptance tests remain unproven for the unified harness. Existing
console/introspection tests establish their previous scopes only. The earlier
Introspection parity requirements remain active alongside this matrix.

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
