# Targeted native console investigation — 2026-10-08

PROVEN: both requested commands were entered and executed in the existing native
console at the main menu, using the running SDK console attachment. No discovered
command was executed. Build: Steam23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.

## Verified handlers, arguments and output

| Command | Target executable evidence | Arguments and destination |
| --- | --- | --- |
| `fname.dump` | Registration140cd5650 binds callback1411a62f0; flags0; help describes base names | No argument required; optional `-num=n` limits recent names. Callback writes `FNames_(%Y%m%d_%H%M%S).txt`; helper141166480 appends `Profiling/`. Live destination: `C:/Users/Matt/AppData/Local/Sandfall/Saved/Profiling/FNames_(20261008_191736).txt`. |
| `dumpccmds` | Built-in branch in console-manager processor141052580 calls1410460d0 with command selector1; not an ordinary named registration | Optional first prefix filter, `-showhelp`, `-csv=PATH`; no CSV option routes to the supplied output device. CSV mode defaults to ConsoleCommands.csv when no explicit path is provided. `-setby=` is parsed by the shared helper but used for its CVar branch, not command filtering. |

Executed exactly:

```text
fname.dump
dumpccmds -showhelp -csv=D:/HobbyDevelopment/ClairObscurSDK/evidence/console-dumps-20261008/ConsoleCommands.csv
```

The console confirmed both output paths. Raw outputs are preserved under
`evidence/console-dumps-20261008/`: the unmodified FName file (17,119,664 bytes,
375,495 lines) and ConsoleCommands.csv (28,007 bytes, 257 rows, NAME/HELP columns).
`manifest.json` records SHA256 and encoding; targeted-name-findings.json and
targeted-command-findings.json are derived indexes. Raw dumps remain local,
excluded from Git and release packages. Registration, handler and xref responses
are preserved as `evidence/console-dump-*.json`.

## Useful confirmed inventory, untested facilities

These commands are present in the live command inventory with the described
help; their individual behavior was NOT executed or validated:

- `CommonUI.DumpActivatableTree`: help lists include-actions, include-children,
  include-inactive and optional local-player arguments. Useful candidate for
  studying menu ownership and activation before adding another UI layer.
- `CommonUI.DumpInputConfig`: current per-player input configuration; candidate
  for checking focus restoration around menu open/close.
- `EnhancedInput.DumpKeyProfileToLog`: registered, but help is empty. Investigate
  its handler and settings object before treating it as a usable diagnostic API.
- `Widget.DumpTemplateSizes`: help describes in-memory widget class templates;
  potential cross-check for reusable asset-backed widgets.
- `AssetRegistry.GetByClass/GetByPath/GetByName/GetDependencies/GetReferencers`
  and `AssetManager.DumpLoadedAssets`: possible asset discovery aids. Asset
  registry results would not prove a live UObject or safe instantiation.
- `FName.List`, `FName.Stats` and related name diagnostics are registered.

`dumpccmds` enumerates registered console commands, not CVars or every Exec route.
The shared handler has a separate `dumpcvars` branch, which was not executed.
Absence from this CSV therefore does not prove a command or CVar unavailable.
No complete CVar or generic reflection-command inventory is claimed.

## Names only: leads for reflection, not callable APIs

The base-name dump contains UserWidget, WidgetTree, CanvasPanel, Button, Slider,
TextBlock, ComboBoxString, AddToViewport/AddToPlayerScreen/RemoveFromParent,
WidgetBlueprintLibrary, GetAllWidgetsOfClass, SetKeyboardFocus/SetUserFocus,
SetFocusToGameViewport and SetInputMode_GameOnly/GameAndUIEx/UIOnlyEx.

Input names include EnhancedInputLocalPlayerSubsystem, EnhancedInputUserSettings,
InputMappingContext, MapPlayerKey/UnMapPlayerKey, AddMappingContext,
OnKeyDown/OnKeyUp/OnPreviewKeyDown, IsInputKeyDown, LeftShift, Tilde and
Gamepad_FaceButton_Bottom. This supports targeted object/schema searches; it does
not validate key support, dispatch hooks, modifiers or input suppression.

Game-specific leads include WBP_Settings_ControlsPage_C,
WBP_Settings_MappingOptionEntry_C, WBP_Settings_InputOptionsList_C,
WBP_CommonUI_InvisibleModalInputBlocker_C, WBP_Debug_UINavigation_C,
WBP_Debug_UMG_AnimationDebugger_C and BP_ExtendedCheatManager_C. A pooled name may
come from serialized data or a past load. It proves neither a loaded widget/class,
an enabled debug menu, nor a callable function. Debug and cheat facilities were
not activated.

The registered Sandfall.Save.ClearCloudSaves is explicitly destructive in its
help. It was recorded only. Slate.DeleteResources, forced-input commands, save
profile commands and GC stress commands were also left unexecuted.

## Roadmap consequences

1. Keep the shared registry/settings/actions and console fallback as the first
   management implementation. No dump reveals an existing SDK mods registry.
2. Use the current live catalog and identity-checked schema adapter to resolve
   the candidate settings classes, CommonUI router, widget libraries and Enhanced
   Input settings. Establish parameters/ownership/game-thread paths before calls.
3. Prioritize CommonUI activation and input configuration when validating UMG
   focus restoration; do not rely solely on raw keyboard input.
4. Evaluate existing settings widgets as possible UMG building blocks only after
   verifying live classes and safe creation/lifetime. Preserve a UMG-independent
   console frontend and recovery bindings.
5. Use names to focus the Introspection Harness investigation. Preserve its
   actual object enumeration, schema and lifetime checks; dumps do not replace them.

## CommonUI handler follow-up — 2026-10-09

Target Ghidra evidence narrows the usefulness of the two registered CommonUI
diagnostics. Neither was executed in this follow-up.

- `CommonUI.DumpActivatableTree` registration RVAe9f990 binds RVA476a760.
  That wrapper calls helper RVA475a2b0, then frees the returned array of24-byte
  string/player records. The helper defaults its first three boolean arguments
  to true and the optional player selector to-1; it builds active-root, tree and
  persistent-action text from the player's action router.
- `CommonUI.DumpInputConfig` registration RVAe9fb30 binds RVA476ac90 with a
  world-context delegate. It takes no command arguments. It formats each local
  player's input mode, mouse capture and hide-cursor state, or an absent-router /
  absent-config message, into a temporary string and then frees it.

The decompiled shipping wrappers show no output-device/log emission for their
constructed text. This is static evidence of discarded diagnostics, not a live
proof of visible console output or a reusable public API. Registration and help
therefore do not establish that either command can supply our restoration state.
The tree helper's returned text and the input-config lookup are useful native
investigation leads, but ownership, ABI, thread and lifetime verification are
required before exposing them through our SDK. No offsets from this observation
have been added to a callable runtime API.

Evidence: `commonui-diagnostic-search.json`, `commonui-diagnostic-xrefs.json`,
`commonui-diagnostic-registration.json`, `commonui-diagnostic-handlers.json`,
and `commonui-tree-helper.json`. Next menu work should investigate the actual
action-router state and restoration path; do not assume these console commands
provide usable output or force GameOnly over the game's existing menu.
