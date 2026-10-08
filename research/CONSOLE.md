# Native console and persistent Python command integration

## Required v0.1 capability (user addition, 2026-10-08)

Native in-game console UI, preferably configurable tilde toggle; preserve the
engine's own supported console commands/CVars. Add `py` command routing to the
existing persistent external Python session, with persistent variables/imports,
SDK and loaded-mod access, captured output/results/tracebacks, and error isolation.
Support mod-owned command registration/unregistration. History and completion
should be investigated and provided where feasible. Engine operations execute on
the GameThread; Python execution must not block that thread. Disconnect, shutdown,
console close/reopen and game relaunch must be tested. This is first-class scope,
not satisfied by a separate terminal or a CVar-only API.

Desired path: in-game console -> bounded native command queue -> persistent
external Python dispatcher -> SDK/mod APIs -> scheduled engine operations. Native
commands continue through the engine path. `sdk.console.execute("stat fps")` is a
target API, not an implemented claim. Example acceptance commands include
`py print("Hello World")`, `py sdk.console.execute("stat fps")`, `py help()` and
`py my_mod.some_function()`.

## Current evidence

OBSERVED live PID9552: native Console Class index2072 and Default__Console
index29570/serial1057 exist. The only Console-class instance found by the inventory
is that class default object. CustomGameViewportClient_2147482419 index85500,
serial15933 is the live viewport specimen. GameViewportClient, InputSettings,
ConsoleUtils, ConsoleKey, SendToConsole and ExecuteConsoleCommand metadata also
exist. Evidence: evidence/console-live-inventory.json. Names alone do not establish
working UI, command execution, creation semantics or a key binding.

NOT IMPLEMENTED/NOT TESTED: native console activation, key routing, console command
execution, persistent `py` dispatcher, in-game output, command registrations,
history/completion. No stock UE offsets or object creation calls have been assumed.

Next: inspect reflected viewport/console/input fields and native function metadata,
trace constructors, initialization, input and execution paths in Ghidra, then
design the smallest reversible GameThread experiment. Preserve existing hook
transport and packaging work while adding this independently verified capability.

## Initial target-specific console leads

PROVEN read-only reflection: Console size0x130; ConsoleTargetPlayer +0x38, texture references +0x40/+0x48, HistoryBuffer ArrayProperty +0x68. GameViewportClient size0x3b0; ViewportConsole ObjectProperty +0x40, World +0x78, GameInstance +0x80. CustomGameViewportClient size0x3f0 inherits those fields. InputSettings size0x140; ConsoleKeys ArrayProperty +0x130. Engine ConsoleClass ClassProperty +0x118, GameViewport ObjectProperty +0xa80. Evidence: console-reflection.json. Actual live values and array element layouts still need reads/validation.

PROVEN reflected function metadata: KismetSystemLibrary.ExecuteConsoleCommand index6060, entryRVA0x3847c70, params32bytes: WorldContextObject object at0, Command StrProperty at8 (16bytes), SpecificPlayer object at24. PlayerController.ConsoleKey entryRVA0x3b23ad0 has a24byte Key struct; SendToConsole entryRVA0x3b28190 has16byte string. PlayerController.SetConsoleTarget lookup failed (NO_VALID_OBJECTS); do not assume that owner from a name-only inventory.

OBSERVED Ghidra decompilation: ExecuteConsoleCommand thunk reads three parameters, resolves a world through 143d8d100 using global1494de3f8, tries a manager vtable+0xe0 path, then player vtable+0xdd8 or engine interface+0x28/vtable+8. ConsoleKey and SendToConsole thunks forward to player vtable+0xcf0/+0xcf8. These are control-flow leads, not validated callable ABIs or proof that UI survives shipping compilation. Evidence: console-native-thunks.json. No command has been executed yet.
