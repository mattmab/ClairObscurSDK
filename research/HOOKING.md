# HOOKING

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

No hooks have been installed. A thread-specific scheduling fixture is the next prerequisite experiment.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Scheduling experiment candidate

HYPOTHESIS: a Windows WH_GETMESSAGE hook scoped to the proven game-thread ID can serve as a controlled scheduling entry point. First test in our own x64 message-pump fixture. Never use a global hook; no keyboard capture or input interception is needed. The callback must recognize only the SDK registered message, preserve unrelated messages, communicate a bounded result, and avoid blocking the target thread. Native DLL initialization must remain minimal; no engine calls from DllMain.

Microsoft documents that a hook for another process requires a DLL and exposes a thread ID parameter: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowshookexw . Cleanup guidance: https://learn.microsoft.com/en-us/windows/win32/winmsg/using-hooks . Hook removal and DLL lifetime must be tested separately; do not assume unhook means every callback has returned or the module is already unloaded.

This is a scheduling hypothesis, not the requested Unreal function callback milestone. Native-to-Python event delivery, hook handles, explicit removal, exception containment and mod teardown still require implementation and verification.
