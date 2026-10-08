# HOOKING

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: persistent public Session hook handles observe the fixed native Actor getter, deliver copied contexts to external Python, contain callback exceptions, restore the entry on removal and clean up after disconnect. Normal game shutdown and relaunch were tested, including with the console active. Arbitrary function hooks and synchronous cancellation remain unsupported. Entries below preserve the chronological experiments.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Scheduling experiment candidate

HYPOTHESIS: a Windows WH_GETMESSAGE hook scoped to the proven game-thread ID can serve as a controlled scheduling entry point. First test in our own x64 message-pump fixture. Never use a global hook; no keyboard capture or input interception is needed. The callback must recognize only the SDK registered message, preserve unrelated messages, communicate a bounded result, and avoid blocking the target thread. Native DLL initialization must remain minimal; no engine calls from DllMain.

Microsoft documents that a hook for another process requires a DLL and exposes a thread ID parameter: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowshookexw . Cleanup guidance: https://learn.microsoft.com/en-us/windows/win32/winmsg/using-hooks . Hook removal and DLL lifetime must be tested separately; do not assume unhook means every callback has returned or the module is already unloaded.

This is a scheduling hypothesis, not the requested Unreal function callback milestone. Native-to-Python event delivery, hook handles, explicit removal, exception containment and mod teardown still require implementation and verification.

## Scheduling fixture and live proof

PROVEN: hidden x64 fixture child creates a message queue; our thread-specific DLL callback verifies process/thread IDs and a per-run random shared-mapping nonce before accepting a request. Callback returns42. Tests reject the wrong thread and reject game invocation in the fixture executable, recover with another ping, verify a request timeout, remove the hook, and process a queue barrier proving no callback occurs after removal. Module enumeration proves DLL unload and the child exits0. Three fresh processes reproduced the full sequence.

PROVEN in game: the same scheduling path runs in PID25988/TID27548, returns42, removes its hook and unloads. The subsequent fixed reflected invocation uses that scheduling callback; see FUNCTION_INVOCATION.md. Neither experiment patches game code, UObject vtables or UFunction entry pointers.

The hook passes unrelated messages to CallNextHookEx and only changes its own validated request message to WM_NULL. It only executes on PM_REMOVE. Microsoft explicitly permits a callback still running after UnhookWindowsHookEx returns, so success additionally requires observing the remote module absent: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-unhookwindowshookex . Message semantics: https://learn.microsoft.com/en-us/windows/win32/winmsg/getmsgproc . No forced game DLL unloading is used.

NEXT: preserve an original reflected function entry, install a reversible observer on the verified game thread, deliver bounded native events to Python, and exercise remove behavior. A scheduling callback does not satisfy the Unreal function-hook milestone by itself.

## Observer lifetime fixture (2026-10-08)

PROVEN only in our own executable: native/observer_fixture_dll.cpp publishes a pass-through function pointer, records object identity/thread/result into a bounded 64-record buffer, suppresses nested notifications, and restores the original pointer with compare-exchange. Removal detaches event storage while holding the same SRW lock used by writers. Conflicting ownership is reported without overwriting the new owner. No game metadata has been modified by this fixture.

The observer module is pinned until process exit using GetModuleHandleExW FROM_ADDRESS|PIN. This is intentional: a thread can fetch a callback pointer before removal and enter after removal. An active-call counter alone cannot establish safe DLL unloading. Removing the observer stops recording and restores the entry; it does not unload its code. The original entry remains immutable after first publication. Microsoft contract: https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandleexw . This design must be kept separate from the existing temporary scheduling DLL, whose unload is already verified.

PROVEN: scripts/build-observer-fixture.cmd compiles with MSVC /W4 /WX. Three fresh executable runs each test 1,000 concurrent install/remove cycles, a deliberately prefetched callback invoked after removal and FreeLibrary, return/context correctness, nested notification suppression, overflow accounting, duplicate rejection, idempotent removal and slot-conflict preservation. Evidence: evidence/observer-fixture-verified.json. Published code remains resident; the fixture process exits normally. This does not yet prove an Unreal hook, Python callback, game shutdown handling, or containment of native faults. Python delivery is still pending.

## Python delivery semantics

PROVEN in unit tests, not against game events: src/expedition33/_callbacks.py implements owner-thread delivery of copied immutable context, bounded subscriptions/diagnostics, explicit handles, removal during dispatch, and callback release on close. Exceptions including SystemExit disable only the failing subscription; traceback text is retained without keeping exception frames or mod instances alive. Recursive dispatch fails within the callback isolation boundary. Seven tests pass via python -m unittest discover -s tests -v, including 1,000 enable/disable cycles, weak-reference lifetime checks, hostile exception formatting, and wrong-thread rejection.

This is an internal component, not yet exposed as sdk.hook. It has no game transport or native installation authority. Callback execution will be asynchronous on the external Python owner thread and cannot cancel/modify an engine call. Native event connection and real game observation remain the next experiment.

## Live scoped UFunction observer: 2026-10-08 19:45 UTC

PROVEN against the recorded SHA256, PID25988, GameThread27548: scripts/verify_live_observer.py observed real calls to Actor.IsActorBeingDestroyed through the UFunction native entry at +0xd8. The target was Default__Actor index28233/serial1010. Two captured events per run report this exact object address (checked natively and against the separately enumerated Python snapshot), game thread and false return. These events originate in the native pass-through hook after the original thunk returns; they are not notifications synthesized from a read-only result or merely from calling invoke_proof.

Mechanism: fixed_observer_v1.dll uses the validated scheduling path, performs the full fixed-invocation validation/baseline call, atomically replaces only the known getter's entry, invokes reflected dispatch twice, and restores the original entry in a native finally block. It then invokes the getter again with the hook absent and verifies the event count remains two. The observer core is shared with the concurrent fixture. Engine machine code and game files are untouched; the one UFunction pointer is temporarily changed in live memory. The versioned observer DLL is pinned until game exit; storage is detached under the writer lock on removal. This is distinct from scheduling_hook.dll, which still unloads after ordinary invocation.

Python observe_proof validates every event and cleanup field before delivery, then calls the user callback on the external caller's Python thread. Context contains immutable identity observations, target, sequence, GameThread ID and bool result. The getter has no input parameters, so there are no argument fields to marshal in this specimen. Native collection finishes and restores the entry before Python runs; Python cannot modify, block or cancel the original call.

Three live observer runs proved normal delivery, intentional RuntimeError isolation (one invocation of the failing callback, disabled thereafter), and successful later delivery without duplicates. Independent before/after stored-bool snapshots and function metadata matched. A subsequent ordinary reflected invocation succeeded and its scheduling DLL unloaded. Computer Use then showed the normal game main menu/build68322. Evidence: evidence/python-live-observer.json. Reproduction: build-fixed-observer.cmd, build-research-probe.cmd and build-scheduling-fixture.cmd, then verify_live_observer.py. Existing fixture was rebuilt against the shared core and passed its concurrent/lifetime sequence again.

LIMITS: this is a scoped, user-triggered getter observation proof, not a persistent sdk.hook API. Game shutdown/relaunch integration, session-owned subscriptions, general targets and mod lifecycle still need implementation and live testing. Native faults are guarded around the experiment but no arbitrary-state rollback is claimed. If restoration cannot be verified, the command reports failure instead of publishing events. A pinned DLL cannot be rebuilt in-place while that game process holds it; the SDK must document and version this lifetime explicitly.

## Persistent-session lifetime prerequisite

Target analysis now establishes ordinary-GC exclusion for the getter/default Actor's registry prefix, and a shutdown path that explicitly bypasses this exclusion; see OBJECT_SYSTEM.md. This changes cleanup design: an arbitrary watchdog thread must not dereference the cached UFunction slot during exit purge. Next implementation must schedule normal removal on the game thread, retain callback code for late entries, keep event storage under native ownership until detached, and treat target-process exit as a terminal transport event. Prefix membership is deliberately not exposed as generic UObject ownership. No persistent hook has been left installed by the research so far.

## Persistent sessions and public hook handles: 2026-10-08 20:10 UTC

PROVEN: runtime_session_v1.dll retains a target-owned message hook after removing its external bootstrap. Commands execute on the verified GameThread. A native worker waits only for controller exit and wakes the target thread; it never dereferences Unreal state. Target-thread cleanup restores the UFunction entry, detaches event storage and removes the message hook. Code remains pinned until process exit to protect late-fetched callback pointers. The normal-GC prefix and exit flag derived in OBJECT_SYSTEM.md guard the cached specimen; this is not generic object pinning.

PROVEN in our executable: three fixture runs total 18 sessions, including nine abrupt controller exits, with cleanup on the target thread and successful subsequent reopen. PROVEN in game PID25988/TID27548: three persistent sessions each captured two separate reflected calls, consumed events exactly once, removed idempotently, called without collecting after removal, reenabled, and restored on close. Deliberately killing only our controller also restored the entry, and another session opened successfully. Stored Actor bools were unchanged. Evidence: evidence/session-fixture-verified.json and evidence/python-live-session.json.

PROVEN public API: from expedition33 import sdk; sdk.Session provides find_object, call, hook, poll and close. scripts/verify_live_sdk.py completed ten enable/disable cycles, 12 successful callbacks, intentional SystemExit containment with another subscriber still receiving the event, idempotent handle removal, and context-manager restoration. After the last subscription disappears, poll/remove reconciles and removes the native observer. Callbacks run only during explicit poll on the Python owner thread, using copied immutable context. No synchronous cancellation or argument mutation is offered. Evidence: evidence/python-live-sdk.json. Seven callback unit tests and the shared native observer fixture (1,000 concurrent cycles) pass after the changes.

LIMITS: only Default__Actor.Actor.IsActorBeingDestroyed is supported. Other objects/targets are rejected before transport commands. Buffer capacity is 64; dropped events are counted, not silently reported as delivered. Controller disconnect and ordinary session close are proven; actual game shutdown with an active session still requires a controlled live experiment. The shutdown branch avoids touching the cached engine slot after exit-purge starts and detaches native storage; do not claim that branch is live-proven yet. No mod loader or v0.1 release is earned by this milestone.

## Active-hook game exit and fresh-process recovery: 2026-10-08

PROVEN: scripts/verify_game_exit.py armed a persistent observer on PID25988 and received one real callback. Computer Use showed the main menu, selected Quit and confirmed Return to Desktop. A retained Windows process handle signaled exit code 0. A later invocation failed closed with SESSION_POST_FAILED; Python close released its subscriptions. Evidence: evidence/game-exit.json. This proves normal process exit with an active observer, not that the conditional exit-purge cleanup branch was necessarily executed before process teardown.

PROVEN: Steam Play launched fresh PID9552. Independent native discovery enumerated 82,102 live objects across two chunks while startup was still progressing. The public example mod then passed three lifecycle cycles, and the public hook verifier passed ten enable/disable cycles with exception containment and entry restoration. No prior process address was reused as an SDK input. Evidence: evidence/python-live-enumeration.json, python-live-mod.json and python-live-sdk.json (these latest-run artifacts supersede their previous contents).

The controller now retains a SYNCHRONIZE process handle and checks it before posting commands, avoiding reliance on a potentially reused thread ID after target exit. Normal operation of the revised controller passed the fresh-process SDK verifier. Its new SESSION_TARGET_EXITED diagnostic has not yet been observed in another live shutdown; the earlier shutdown evidence records the previous SESSION_POST_FAILED diagnostic accurately.
