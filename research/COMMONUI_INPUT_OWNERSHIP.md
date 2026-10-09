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
