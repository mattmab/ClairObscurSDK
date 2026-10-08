# HOOKING

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: temporary Windows scheduling hooks run on the intended fixture/game thread and are removed; the DLL unloads. Unreal-function hooks and Python callback delivery are not implemented yet.

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
