#Requires AutoHotkey v2.0
#SingleInstance Off
; Development-only one-shot input helper. MIT. No SDK installation changes.
; AutoHotkey64.exe e33-held-key.ahk T 180
; Allowed keys: T, Esc, Tab, Enter, Space, F5, F6. Duration: 50..500 ms. No persistent hotkeys.
held := ""
OnExit(ReleaseHeld)
ReleaseHeld(*) {
    global held
    if held != "" {
        SendEvent("{" held " up}")
        held := ""
    }
}
try {
    if A_Args.Length = 1 && A_Args[1] = "--check" {
        Report("Script loaded; no input sent.")
        ExitApp(0)
    }
    if A_Args.Length < 1 || A_Args.Length > 2
        throw Error("Usage: e33-held-key.ahk T|Esc|Tab|Enter|Space|F5|F6 [50..500 milliseconds]")
    keys := Map("t", "sc014", "esc", "sc001", "escape", "sc001", "tab", "sc00F", "enter", "sc01C", "space", "sc039", "f6", "sc040", "f5", "sc03F")
    key := StrLower(A_Args[1])
    if !keys.Has(key)
        throw Error("Only T, Esc, Tab, Enter, Space, F5 and F6 are permitted")
    duration := A_Args.Length = 2 ? Integer(A_Args[2]) : 180
    if duration < 50 || duration > 500
        throw Error("Hold duration must be 50..500 ms")
    windows := WinGetList("ahk_exe SandFall-Win64-Shipping.exe")
    if windows.Length != 1
        throw Error("Expected exactly one Expedition 33 window")
    target := "ahk_id " windows[1]
    WinActivate(target)
    if !WinWaitActive(target, , 2)
        throw Error("Game did not become active")
    Sleep(100)
    if !WinActive(target)
        throw Error("Game lost focus before input")
    if GetKeyState("Ctrl", "P") || GetKeyState("Alt", "P") || GetKeyState("Shift", "P") || GetKeyState("LWin", "P") || GetKeyState("RWin", "P")
        throw Error("Release physical modifier keys before testing")
    SetKeyDelay(-1, -1)
    held := keys[key]
    try {
        SendEvent("{" held " down}")
        started := A_TickCount
        while A_TickCount - started < duration {
            if !WinActive(target)
                throw Error("Game lost focus; releasing key")
            Sleep(5)
        }
    } finally {
        ReleaseHeld()
    }
    Report("Sent " key " held for " duration " ms; released.")
    ExitApp(0)
} catch as err {
    ReleaseHeld()
    Report(err.Message)
    ExitApp(1)
}

Report(message) {
    FileAppend(message "`n", A_ScriptDir "/../build/held-key.log")
    try FileAppend(message "`n", "*")
}
