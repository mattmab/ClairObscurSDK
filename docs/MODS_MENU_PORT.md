# Matt's E33 Mods Menu

This is the chronological port record. For current installation and release
scope, read the [RC11 notes](RELEASE_0.1.0_RC11.md). The latest source startup
measurements and pause-button/console checks are in
[startup validation](STARTUP_MENU_VALIDATION.md); they supersede the older
12-second construction figures and unconfirmed pause-input checks below.

The SDKManagement native frontend now uses `ScrollWorkspaceMenu` and
`ScrollWorkspaceView`. Both the development checkout and the installed game SDK
have the replacement. Start the existing `Launch Native Mods.cmd` and use the
pause menu's Mods entry, or enter `mods ui` in the console.

The reference is the user's MattsBL4ModsMenu.sdkmod, including its workspace
extension. The E33 World Builder supplies the dark full-screen palette, teal
buttons, scaled game text and split content/inspector layout. BL4-specific hooks
and engine objects are not imported. The existing E33 ownership, registry,
generation checks, travel cleanup and protected-core rules remain in use.

## Features

- Search, refresh and filters for enabled, disabled, configurable, keybound,
  reloadable, core and unloaded mods.
- Native mouse-wheel/scrollbar mod list with inline enable/disable switches,
  conflict warnings and a persistent selected-mod inspector. Core switches are
  locked. Recycled rows keep native control ownership bounded while the
  scroll extent covers the entire filtered list.
- Load, enable, disable, reload and unload, with metadata and option previews.
- Native value field with Apply, Reset and Cancel. Text is literal; other values
  use JSON syntax, including quoted string choices and `true`/`false` booleans.
  Existing registry validation enforces option types and ranges.
- Actions accept optional JSON in the value field. Blank means no argument.
- A dedicated scrollable keybind manager with All/Bound/Unbound/Conflicts and
  per-mod filters. Click a conflicting key to inspect its owners; each row has
  Rebind, Unbind, Disable mod and Reset, and its name opens the mod inspector.
  Rebind captures the next keyboard press directly. Escape unbinds; Cancel
  preserves the old binding. Conflicting assignments name the other owners.
- Confirmed bulk enable/disable, reload of enabled user mods, unbind and key
  default restoration. Protected mods are excluded. Confirmed generations are
  checked again before dispatch, and failures are reported without retry.
- Diagnostic and bulk result JSON files in `settings/ModsMenu`.
- Persistent World Builder, KAIROS Cyan, Crimson, Vault Gold and Neutral Dark
  themes, plus text-size preferences under Menu appearance / SDK Management.
- Escape cancels an active option edit before closing the menu.

## E33 adaptations and validation limits

The layout uses the World Builder's 1920×1080 coordinate convention. Mod and
global key lists use native scrolling and a recycled row pool within the
installed runtime's 64-control limit. Detail/action screens still
use the existing bounded presentation pages.
Key capture supports the E33 runtime's 63 single keyboard keys; modifier chords
and gamepad bindings are not supported. The launcher
remains the native E33 pause-menu entry; BL4's draggable overlay launcher is not
ported. Other resolutions/DPI and gamepad navigation remain unverified.

Live validation on 2026-10-15 used loaded exploration gameplay at 2048x1152.
Mouse navigation, native typing/search, numeric Apply/Reset, Escape close and
Escape edit cancellation were exercised through Windows input. Visual checks
confirmed the two-pane layout, readable focused input, Crimson/Neutral Dark
themes and maximum text scale without overlaps in the inspected screens.

An isolated harmless fixture exercised the actual registered native control
callbacks and UMG text getters/setters: all filters, empty search, clear,
boolean/integer/float/text/choice settings, validation failures, cancel/reset,
refresh, JSON actions, reports, key remap/unbind/default, load/enable/disable/
reload/unload, diagnostics export, all five bulk operations, themes, text-size
bounds and close/reopen. Bulk tests used separate settings and no gameplay mods.
This verifies the manager operations, not every individual gameplay mod action.
The 83 targeted automated tests also pass against the installed SDK source.

The scrolling revision adds three regression tests (86 total in the targeted
suite). In-game mouse-wheel scrolling and scrollbar dragging reached the last
of 19 fixture mods; clicking after scrolling selected the correct inspector.
Mouse clicks disabled and re-enabled a fixture using its inline switch. Two
enabled fixture mods shared F9: both appeared in the conflict view and Unbind
cleared the conflict. Native callback checks also covered per-mod filtering,
reset, rebind and return, disabling an owner, opening its mod and option editing.
Fixture settings and mods were isolated from the user's normal installation.

Live testing found and fixed a native paint-batch mismatch for editable text,
focused input contrast, the old development launcher target, and installed
archive materialization overwriting the new manager. The installed archive and
release hashes now include the replacement; release verification passes.
The game pause-menu entry was attached, but opening it using automated game
key input was not confirmed. Other resolutions, controller input and travel
recovery have not been included in this acceptance pass.

Installed files were backed up to
`D:/HobbyDevelopment/Analysis/BL4MenuPort/backup-20261015-175652`.
The installed SDK's existing World Builder widget capacity and construction
behavior were preserved; only the shared content-construction hook was added.

## Press-a-key capture validation

The v53-keycapture runtime adds an explicit, capability-negotiated capture map.
Only foreground menu input is captured; repeats and modifier chords are ignored.
The first accepted press restores gameplay routing before updating the binding.
Cancel and Close revoke capture and queued events. Native changes against the
World Builder v53 source are integrated in `native/`.
The compiled candidate and its build script are retained under
`D:/HobbyDevelopment/Analysis/BL4MenuPort/key-capture`.

In-game Windows input on 2026-10-15 verified F8, F9, K and F10 capture,
Cancel retaining F8, Escape unbinding while the menu remains open, and F9
conflict feedback naming both owners. Closing during capture and reopening also
passed. These checks used isolated fixture settings, preserving user bindings.
All 53 targeted Python tests and the native keybind fixture passed. Installed
release verification passed with the new runtime and launcher hashes.

## Second comparison and held-key repair (2026-10-15)

Compared the BL4 main workspace, configuration screen, global bindings and
capture handlers against the E33 implementation again. Added native scrolling
for settings and per-mod bindings, direct boolean toggles, choice cycling,
per-setting reset, configuration previews in the inspector, and four direct
keybind shortcuts beside settings (the full list remains in Mod keybinds).
The sidebar capture retains the refreshed registry selection after saving.

Flight previously dispatched the rebound R key correctly but its held-input
check still queried hard-coded Q. Both vertical controls now resolve their
configured keys and revoke held input on remap, unbind or conflict. The user
confirmed that holding R now descends in the running game. The saved R binding
was preserved in the installed archive update.

Live isolated fixtures verified boolean toggle, choice cycling, numeric Apply
and Reset, scrolling to the twentieth setting, toggling that recycled row
without changing the first row, readable main previews, and direct sidebar F10
capture followed by navigation back. 73 targeted Python tests pass.

This earlier revision has been superseded by the layout and focus fixes below.

## BL4 layout, typography and focus fix (2026-10-15)

The header now contains Mods/Keybinds tabs and a persisted .75–2.75 text slider
with minus, plus and Reset (1.35). Main content follows BL4's 596/1238 split;
configuration uses its 438/826/548 summary/options/keybind columns. Options and
keybinds use independent native ScrollBoxes, including recycled action targets.
Text uses the E33 common style with the BL4 48px design base compensated for
E33's 36px style; label slots and truncation budgets follow their physical bounds.
Compact controls cap text at their available height, as in the reference.

The Keybinds teardown was reproduced with isolated fixtures. Native binding
failed on its 32nd new control (1012 Busy, batch error 1203) because the lifetime
focus table had already retained other tab controls. Active bindings were below
64, but the menu owns 105 distinct reusable buttons across tabs. Runtime v54-menu
raises the separately retained focus table to 128, leaving active callback
capacity and ownership/cleanup validation unchanged. The integrated source is now in `native/` and builds with
`scripts/build-release-runtime.cmd`.

In-game fixtures verified independent physical wheel scrolling of 20 settings
and 25 keybinds, capture of F8 on the last scrolled key, persistence, repeated
Mods/Keybinds/configuration navigation, slider dragging and closing/reopening
after slider focus. The regular installed menu also survived an actual
Keybinds-tab click with all nine enabled mods and retained its command backend.
79 targeted Python tests and the native 105-control/five-tab focus regression
pass. Installed manifest verification passes.

The pause entry is now attached immediately after the core manager enables,
before optional saved mods restore or prewarm. Projected reads and bounded
layout batches reduce entry construction. Loaded-game startup measured 5.9s
from controller start to the visible entry, including 2.198s construction.
The full 105-control menu still takes about 12s to construct; this is not an
instant-start implementation. E33 retains World Builder styling, its game font
and the native pause entry instead of BL4's movable launcher.

Follow-up installed-game verification: restarted the controller on the running
game and opened Mods through the pause button. Verified maximum text (2.74),
minimum (.75), and Reset (1.35); the corrected summary retains text instead of
collapsing to an ellipsis. Loaded the temporary MenuQA fixture through the game
console: its 20 settings and 25 keybinds scroll independently. Settings remained
at Extra toggle 3 while keys moved to Extra key 9. Switching from configuration
to global Keybinds rendered all 35 bindings without SDK teardown. Closing the
menu and pressing the console key reopened the native console successfully.
This reload took 7.578s from gameplay-ready to entry attachment (1.949s entry
construction); saved mod restoration and first menu creation still added delay.
