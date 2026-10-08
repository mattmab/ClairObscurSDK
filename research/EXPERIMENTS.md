# EXPERIMENTS

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Harmless MCP fixture

Added native/fixtures/mcp_smoke.c: two integers added in a noinline function, print result 42, exit success. It neither attaches to nor modifies any game. Compile after the native toolchain installation finishes. MCP proof should import this image, enumerate functions, decompile research_add, annotate it, save/reopen, and query the annotation. No such proof has run yet.

## Live enumeration capstone — 2026-10-08

STALE/DISPROVEN candidate: short name-pool instruction signature matched 13 locations. Rejected before runtime use. Added surrounding name-index decoding instructions; refined signature matched exactly once. Registry signature also matched once. Evidence: anchor-signature-uniqueness.json and anchor-signature-uniqueness-refined.json.

PROVEN: MSVC compiled our native reader without warnings. Absent-game test returned GAME_NOT_RUNNING. Normal Steam launch followed by native first-32 enumeration succeeded. Editable Python module installation required setuptools/wheel in the D: environment; initial missing-backend failure was resolved there.

PROVEN: scripts/verify_live_enumeration.py called the real native runtime reader and returned 96,053 live objects in 1.967 seconds, max index96,604, PID25988. It verified core class identities and traversal beyond the 65,536-slot chunk boundary. Computer Use confirmed the game remained healthy at its main menu. This fulfills the first capstone, not reflection/invocation/hooks or the complete goal.

Repeat live query: 96,053 objects in 1.980 seconds, same PID and max index. First evidence preserved as python-live-enumeration-first.json.

## Reflection and annotation experiments

PROVEN: native/Python metadata queries for Actor/HUD/Object pass inheritance, inherited-property equality, distinct-name and bounds checks. Absent class returns NO_VALID_OBJECTS. Enumeration regression still reports96053.

OBSERVED: Ghidra set_comment succeeded on registration/name routines and comments are returned in subsequent decompilation. save_program timed out with outcome unknown while whole-image analysis remained active; persistent save is not yet proven. GUI shows Constant Reference Analyzer progressing. No analysis cancellation or repeat save issued.

## Stored property values

PROVEN: scripts/verify_live_bools.py reads Default__Actor and Default__HUD through Python/native reflection, validates33/39 observations with true/false shared-byte specimens and repeated Actor equality. Metadata and object enumeration regressions also passed. All game access remains read-only; no invocation, injection, hooks, writes or save loading performed.

## Dispatcher, function parameters and game thread

PROVEN: live vtable slots on Object/Actor/HUD resolve to statically inspected dispatch implementations. Python function metadata validates two single-byte boolean returns and a24-byte struct return. Wrong-owner query rejects. Ghidra create_function at observed native entry pointers resolves earlier missing-boundary failures. Game-thread DWORD27548 is owned by PID25988 according to Windows. Existing boolean live tests pass after the extension. No game invocation performed.

## Thread scheduling and actual invocation

PROVEN: independent fixture processes5172/14068/2480 ran callbacks on their exact main threads, returned42, rejected wrong-thread and non-game invocation requests, passed timeout/removal checks, unloaded DLLs and exited0. The fixture cleanup was improved to avoid posting WM_QUIT after the child had already exited (thread-ID reuse risk).

PROVEN: game-thread ping in PID25988/TID27548 then actual Python reflected call Default__Actor.IsActorBeingDestroyed returnedfalse twice. Native validations and callback result transport passed. Before/after stored boolean observations match; scheduling hook removed; remote DLL absent before success. Game remained healthy at menu. No save loaded, no gameplay mutation performed. Source: native/scheduling_*.cpp, scheduling_protocol.h, fixed_invocation.h, thread_ping.h; verifier: scripts/verify_live_invocation.py.

## Development candidate packaging checkpoint

PROVEN: scripts/package_dev.py builds an allowlisted zip containing SDK source, native binaries, example mod, tests and research Markdown; game files, analysis databases, dumps, credentials and evidence are excluded. Candidate 20261008T201839Z SHA25645fc3c0284678f8e44372fcf157a928f26cc55ae4f72874e34769ba515214782. launch.cmd uses pinned CPython3.13.15 with -I -S -B, verifies manifest checksums and imports from the bundle. The bundle smoke run enumerated96053liveobjects in PID9552, reflected80Actor fields/read33bools, and completed ExampleMod with a real native callback and unload. Console integration is newly required and absent, so this artifact is explicitly a candidate, not v0.1 completion. DEVELOPMENT.md documents setup, APIs and constraints.
