# RC12 and World Builder 0.30.1 validation

RC12 / World Builder 0.30.1 release validation - 2026-10-15

PASS: 1,097 SDK regression tests.
PASS: 81 standalone World Builder regression tests.
The sandbox initially blocked 9 localhost socket tests; the full suite passed
when rerun with localhost access. Expected mock failure tracebacks are test output.
PASS: release runtime, probe and thumbnail worker builds (/W4 /WX).
PASS: native targeting fixture (>32 candidates, vanished hits, foreground
occlusion, capture ownership and camera movement).
PASS: staged SDK launch-sdk.cmd --check reports release 0.1.0-rc12, 3 mods,
verified true. Runtime/license packaging verified 34 runtime and 20 notice files.
PASS: ZIP CRC and nested sdkmod checks; no settings, logs, backups, research,
map saves, screenshots or personal mod content included.

Previously completed live testing of the fixes: foreground/rear prop targeting,
drag, F8 on/off, F7 open/close, console and reader health. All 28 existing edits
were retained. Prior menu checks covered Pause > Mods, text sizing and Keybinds.
PASS (subsequent 2026-10-15 clean-install run): exact final RC12 and World Builder
0.30.1 ZIPs installed without inherited settings or optional mods. Normal game
launch and SDK autostart, Pause > Mods via held Escape workaround, enable World
Builder, Keybinds, F8-to-F6 press-a-key rebind and reset, text size 1.35-to-1.89
and reset, F7 catalog open/close, default F8 off/on, foreground/rear cube
targeting, drag undo entry, and console execution after testing all passed.
Test cubes and preview removed: zero tracked edits after cleanup.
Observed menu construction 2269.463 ms; readiness 9.287 seconds from gameplay
gate. Unavailable temporary assets logged thumbnail failures and were skipped.
This run did not inject reader failure or exhaustively retest all catalog assets.
Map restoration errors across streamed areas remain a documented limitation.

Finalized packages update documentation/metadata only; executable payloads are
compared byte-for-byte against the clean-install tested archives.

Final verification: the only changed archive entries are the outer and inner
World Builder readmes. All other expanded bytes match the in-game-tested ZIPs.
The full 1,097 + 81 regression suites passed again before publication, as did
the native targeting fixture and finalized SDK `--check` integrity validation.

Final Nexus/GitHub ZIP SHA-256:

```text
5c364849fb1d2c0035fbd9b1d8b7e4f0b831ff3f85f6e8c398d89281de3cb378  Expedition33-SDK-0.1.0-rc12.zip
f78ecdb6345e0f081a9ca4c5814ad1888a4970d39eeab2a0fabe387c9caa1a30  E33WorldBuilder-0.30.1.zip
```
