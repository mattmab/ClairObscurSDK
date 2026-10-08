# Native console and persistent Python command integration

## Current status: lifecycle, packaged relaunch, configurable toggle

PROVEN v4: game9552 exited normally with console and observer active (exit code0); controller reported SESSION_TARGET_EXITED and cleared the console namespace and Python session. See local evidence/console-game-exit.json. A normal Steam relaunch produced game21820. The isolated extracted package at package-validation-20261008T205309Z enumerated96056 objects, passed reflection/bool/mod smoke checks, and displayed `Hello after relaunch` and the loaded mod's return value in the native console. Native `t.MaxFPS` returned120. The packaged host closed normally. This supersedes pending lifecycle/package statements in the chronological sections below.

PROVEN v5 in game21820: `console_research_host.py --mod --key F10 --seconds 240` opened the native expanded console with F10. Entering `py print("F10 console works"); key_counter = 17; my_mod.some_function()` displayed the print and mod call1 result. F10 closed and reopened the console; `py key_counter += 1; key_counter` returned18. F10 closed it again. Screenshots from Computer Use preserve these observations in the task. Nineteen Python unit tests and native session fixtures passed before this UI test. Package refresh, binding cleanup input check, and v5 relaunch coverage remain pending.

IMPLEMENTED key API: `console.set_toggle_key("F10")`, None to remove, F1-F12 accepted. The additional binding uses the existing owned GameThread message hook, ignores modified chords and repeated keydown, validates console identity/vtable and independently decoded Typing/Open FNames, then invokes the verified native state transition. Detach/close resets the binding. It does not change the engine's Tilde mapping. Arbitrary key chords and native Up/Tab integration for intercepted Python commands remain unsupported; dispatcher history/completion APIs are available.

## Latest status: mod commands (v4)

PROVEN in game9552: ModLoader.enable(name, console=True) creates the native console before enabling the mod and exposes its instance as `my_mod`. ConsoleExample registers `sdk.hello`. Entering `sdk.hello native console` returned its greeting with call1; `py my_mod.some_function()` returned the same instance's greeting with call2. `py my_mod.greeting.remove()` removed registration; entering `sdk.hello removed` then produced the engine's ordinary Command not recognized response. Native registration replacement discards queued SDK commands (counted as dropped) so a queued command cannot transfer to a new owner. Native names are bounded to256 ASCII names of64characters; commands remain bounded to4096 UTF-16 units and16 queued entries. Python never runs on the GameThread.

PROVEN local fixture: native passthrough, Python/custom routing, queue overflow rejection, failed registration parsing preserving the previous table, stale queue clearing, and late-call fallback after detachment. Seventeen Python tests pass, including registration transport failure not publishing a new callback and disable/re-enable preserving namespace while resynchronizing command names. Live normal close, game exit/relaunch and candidate packaging validation of v4 are next.

Public entry points now include `console.register(name, callback, owner=mod)` returning an idempotent removable handle, `remove_owner`, `expose`, `history`, and `complete`. Mod disable should remove its handles; session close clears all registrations and Python references even if a mod's disable fails. ConsoleExample illustrates this. `launch.cmd console` runs it in the isolated controller; `--seconds N` provides a bounded run. Python results also use the SDK logger, with rotating files in the launcher. These APIs are trusted local Python, not a sandbox.

## Latest status: live Python integration (v3)

PROVEN on PID9552/GameThread36408, same recorded executable SHA256: the per-instance UConsole command slot +0x2c8 intercepts `py` into a bounded 16-entry queue. The controller polls copied UTF-16 text, executes in its persistent Python namespace, and schedules native output through +0x2d8. Original native commands pass through unchanged. The primary vtable clone retains its RTTI locator and 123 slots; only the command slot changes. Native code/storage remain pinned for late calls. Queue access is confined to the owning GameThread; atomic context checks reject other threads.

PROVEN via in-game entry and visible output: `py print("Hello World")`; variable assignment returning41; a later command returning `(42, 9.0)` using retained counter and imported math; `py 1 / 0` displaying a traceback; subsequent `py help()` succeeding; `py sdk.console.execute("stat fps")` enabling the native119.98FPS/8.33ms display. A normal `stat fps` command disabled it through the original handler. Closing/reopening the UI retained Python state and scrollback. Tool screenshots and controller JSON responses preserve this evidence. One combined help/execute typing attempt did not reach the dispatcher; separately entered commands passed, so the combined attempt is not counted as success.

PROVEN console-specific abrupt disconnect: terminated only SDK controller23084, leaving game9552 alive. Native target-owned cleanup removed the open UI. Independent `scripts/inspect_console_runtime.py` confirmed ViewportConsole=0; evidence/console-v3-after-disconnect.json. The host reported a dead-pipe error during abort; `_session.py` now suppresses the redundant close/flush error so it cannot mask the initiating failure. This cleanup change still needs regression coverage.

IMPLEMENTED: `session.console.enable/disable/execute/write/poll`, persistent external namespace with `sdk` bound to that session, bounded output and tracebacks. The research host services console polling explicitly. Native command history works; intercepted Python history is currently dispatcher-only, not native Up navigation. Lexical completion is dispatcher-only. Custom registration exists in Python but direct native command interception/mod integration is pending. Configurable key changes and console-specific game exit/relaunch remain unvalidated. Earlier sections below are chronological findings, superseded by this status where stated.

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

## Live pointers and retained UI paths (2026-10-08)

OBSERVED by scripts/inspect_console_runtime.py after a fresh validated enumeration: live viewport index85500 has ViewportConsole=null, a non-null World and GameInstance; GameEngine_2147482617 points to that viewport and to the Console class. InputSettings contains two24byte console-key entries; the first decodes through the live name pool as Tilde. The second is a localized non-ASCII key (preserved in JSON). The 24byte key specimen is corroborated by ConsoleKey parameter reflection; broader FKey ownership still requires care. Evidence: console-runtime-pointers.json. Reads are observations, not a GC-atomic snapshot or durable handles.

OBSERVED actual PlayerController virtual targets: ConsoleKey(+0xcf0) leads to1413dae10, which only releases the passed key's shared reference; SendToConsole(+0xcf8) points to the common no-op141004480. These reflected helpers are not the activation mechanism in this build. ConsoleCommand(+0xdd8) points to143af9c00, which checks Player at+0x330 and routes to143af9c40. Evidence: console-virtual-functions.json.

OBSERVED retained UConsole methods: vtable+0x2c8 ->143dc4d30 updates HistoryBuffer, caps it at50, saves config, echoes text and dispatches to a player or its viewport outer. +0x2d8 ->143dde5a0 splits output lines and stores bounded scrollback; +0x300 ->143dc3250 edits typed characters and updates completion; +0x3c8 ->143dcff60 changes console state and Slate focus, including a zero-state closing path. These nontrivial methods support further native UI investigation but do not yet prove visible rendering/input. The raw vtable dump includes adjacent data beyond confirmed methods; do not infer every sampled slot belongs to UConsole. Evidence: console-ui-functions.json, console-construct-functions.json.

OBSERVED reflected GameplayStatics.SpawnObject: entry143744670,24byteparams(class0,outer8,result16). Its native helper14372aa60 validates class ancestry/non-null outer and class-required outer type, constructs native object parameters, then calls1413bf660. This provides a target-derived creation path for a GameThread experiment instead of copying a stock StaticConstructObjectInternal signature. Construction, GC ownership, viewport attachment, input/render routing and reversal still need runtime validation. Evidence: console-SpawnObject.json, console-spawn-body.json.

OBSERVED KismetSystemLibrary.GetConsoleVariableIntValue:20byteparams(string0,intreturn16), thunk14384c6f0 uses manager14923e008/vtable+0xb8 lookup then variable+0xa0 integer getter. A future execute/readback pair can establish native command effects independently. No new engine calls or memory writes were performed in this investigation.

## Persistent Python dispatcher component

IMPLEMENTED and UNIT-TESTED only: _console_dispatch.CommandDispatcher keeps one Python namespace across commands, evaluates a final expression for display, captures stdout/stderr and tracebacks into a32768-character buffer, records100 history entries, and contains BaseException including SystemExit. No-argument help() prints guidance without opening interactive stdin; help(object) renders plain text without a pager. Native command text is passed unchanged to an injected native-execution callback. Custom commands have explicit owners, removable handles, duplicate/name bounds, and owner cleanup. Completion currently covers registered command names and top-level Python names without evaluating properties. close() clears callbacks, namespace and history.

Five dispatcher unit tests plus the existing ten tests pass. They cover persistent variables/imports, expression results, Hello World output, syntax/runtime/SystemExit errors followed by successful execution, native routing to a test callback, custom command removal, bounded output/history, close releasing mod references, recursive dispatch rejection and simple completion. This is not evidence of in-game routing, native execution or UI output; those remain absent. The dispatcher is intentionally internal until attached to the real console/session path. Trusted Python can block its controller or run arbitrary local code; exception containment is not a sandbox or execution-time limit. Redirected stdout/stderr is process-global during delivery, so concurrent background Python writers are not isolated per command.

## Construction guard follow-up

OBSERVED via Ghidra:1412099e0 returns the /Script/CoreUObject.Object Class singleton. This identifies the ancestry check used by SpawnObject's helper, rather than assuming it from source conventions.1413abed0 checks thread-local construction state and reports an invalid empty-name default-subobject construction only when the provided outer is the currently constructing object; its presence is not an unconditional prohibition on ordinary NewObject calls.1413a87c0 initializes native construction parameters; the reflected SpawnObject wrapper remains preferable to manually assembling this larger internal structure. Evidence: console-creation-guards.json. No construction has been attempted in the game yet.

## First live UConsole construction

PROVEN on PID9552/GameThread36408: research_probe --console-construct-proof invokes the existing validated Actor getter prerequisite, checks shutdown/incremental-GC indicator bytes are clear, verifies SpawnObject thunk bytes and exact reflected metadata, selects Console Class/default GameplayStatics/unique live CustomGameViewportClient, then dispatches GameplayStatics.SpawnObject with the class and viewport outer on the game thread. Returned object class, outer, native vtable, internal index and registry slot agree. The viewport Console field remains null. The temporary scheduling hook was removed and scheduling_hook.dll unloaded. Evidence: console-construction-live.jsonl.

Independent subsequent enumeration found Console_2147479697 index96606/serial19302 at the exact returned address1897100880128. This is a newly created engine UObject, not the class default object or a synthetic SDK record. Evidence: console-after-construction.json. The object is deliberately unattached; no SDK code pointer or viewport reference was installed, and the SDK does not manually free engine memory. Ordinary GC reclamation of this unreferenced specimen has not yet been observed. UI opening, native command execution and Python routing remain unproven.

FAILED first attempt: expected function flags were mistyped as0x4020403 rather than the recorded decimal67249155 (=0x4022403). Guard103 rejected before creation; evidence console-construction-rejected-flags.jsonl. Correcting the expected value from the existing metadata, without weakening the check, allowed the second attempt. The first scheduling fixture invocation omitted --self-test and printed usage; the corrected --self-test passed thread rejection, non-game invocation rejection, timeout, removal, unload and child exit0. Existing public SDK hook verifier subsequently passed12callbacks/10cycles with exception containment and entry restoration.

Next experiment must retain the created instance through the reflected viewport reference, with session-owned attachment/removal, game-thread close before detachment, identity checks and shutdown rules. Creation success does not establish those lifecycle properties or justify leaving a raw cached object pointer across commands.

## Native console UI and stat fps live proof

PROVEN on PID9552/GameThread36408: runtime_session_v2.dll adds session-owned console attachment. It creates a Console with the live viewport as outer, validates identity, records index/serial, and sets the reflected ViewportConsole reference on the verified GameThread. Repeated attach returns the existing owned instance; detach validates ownership, calls the target's console state transition with None/zero to restore input focus, then compare-exchanges only its owned viewport reference back to null. Normal session close uses the same cleanup. During exit purge it avoids cached UObject dereferences. The DLL remains pinned as before; v1 and v2 message/mapping namespaces differ. Source/controller now target v2; packaging was updated accordingly.

PROVEN via Computer Use: Tilde/grave opened the native one-line console, a second press expanded it. Typing stat fps and pressing Return displayed native command echo and a green119.99FPS/8.33ms overlay. Up recalled stat fps from native history; Return toggled the overlay off. Tilde closed the console, and another Tilde reopened it. Closing the SDK session while the one-line console was open removed the UI; independent read-only probe then found ViewportConsole=0. These are the game's UConsole rendering, history and native command path, not an SDK imitation. GUI screenshots are retained in the task tool outputs. The game stayed at the main menu; no save was loaded.

PROVEN regression: v2 transport fixture passed six sessions (three normal, three abrupt controller exits); attachment/detachment commands were idempotent in a live session. Existing public getter hook verifier passed12callbacks/10cycles and exception containment after the UI test. This does not yet prove console-specific abrupt-disconnect, exit-purge, relaunch or GC-stress behavior. Those need dedicated tests beyond the generic transport fixture.

IMPLEMENTED but internal: SessionTransport commands console-attach, console-detach, console-status. NOT IMPLEMENTED: intercepting py/custom commands, delivery to the persistent external Python dispatcher, Python-to-native console execute, console output from Python, configurable key changes, mod registration integration. Those remain acceptance blockers. Current default Tilde already works through the game's existing InputSettings configuration; no key input hook was required.

The engine's console command path calls its own config/history saving routine; native command history may persist through the game's normal user configuration behavior. The SDK itself did not edit game installation files. Unattached/detached console instances are left to engine GC; no manual deletion or forced collection is attempted. The attachment check tolerates a formerly-zero weak serial being assigned lazily while requiring nonzero captured serials to remain stable.
