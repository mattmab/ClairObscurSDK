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
`nRepeat live query: 96,053 objects in 1.980 seconds, same PID and max index. First evidence preserved as python-live-enumeration-first.json.
