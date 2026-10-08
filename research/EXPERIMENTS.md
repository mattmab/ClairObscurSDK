# EXPERIMENTS

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Harmless MCP fixture

Added native/fixtures/mcp_smoke.c: two integers added in a noinline function, print result 42, exit success. It neither attaches to nor modifies any game. Compile after the native toolchain installation finishes. MCP proof should import this image, enumerate functions, decompile research_add, annotate it, save/reopen, and query the annotation. No such proof has run yet.
