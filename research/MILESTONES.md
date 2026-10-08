# MILESTONES

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Stages 0-2 are established; the object/name subset and first live Python capstone are proven. Whole-image analysis and later SDK stages remain active.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Current state: 11/12 frontier (trivial public-API mod lifecycle proven)

0. Environment inventoried — D: tree and installed apps inspected; MSVC 14.44.35207 and Windows SDK 10.0.26100.0 installed; x64 fixture compilation and execution proven.
1. Target game/build fingerprinted — SHA256, x64 PE headers, local Steam build identified.
2. Ghidra MCP operational — proven by fixture import, metadata/function queries, decompilation, and exact annotation persistence after save/close/reopen. See GHIDRA_MCP.md.
3. Expedition 33 binary analyzed — whole-image autoanalysis failed with a 16 GB heap exhaustion. Restarted with 32 GB after user stopped the old process; saved program reopened and anchor annotations/getter boundaries restored and saved. Whole-image analysis is running again, not complete.
4. Unreal runtime anchors: object registry and name pool proven; dispatcher and GameThread ID corroborated; world/engine and other anchors pending.
5. Name/object infrastructure: chunk traversal, identity fields, name decoding proven; GC lifetime and broader reflection remain pending.
6. Native live enumeration: PROVEN with our read-only external process reader.
7. Python live queries: PROVEN, 96,053 objects across two registry chunks in 1.967 seconds.
8. Reflection/property reads: native class inheritance and property metadata PROVEN; stored BoolProperty reads PROVEN; other value types and GC-safe handles pending.
9. Safe invocation: PROVEN Python -> native -> game-thread reflected dispatch -> boolean return on Default__Actor; general marshalling remains pending.
10. Hooks/callbacks — persistent UFunction observer and public sdk.Session handles PROVEN on the harmless getter, including Python SystemExit containment, ten enable/disable cycles, normal close, controller death cleanup and reopen. Independent native fixture proves concurrent removal/late-entry lifetime. Actual game shutdown/relaunch validation remains pending.
11. Minimal mod loader — PROVEN through three live ExampleMod load/enable/disable/unload cycles; import and lifecycle failure cleanup and module/instance release covered by unit tests. Explicit trusted local mods only; one enabled mod at a time.
12. Private SDK package/docs/trivial mod — candidate packaging in progress. Added v0.1 requirement: native in-game console plus persistent external Python command dispatch, mod-owned command registration, output/errors and clean lifecycle; see CONSOLE.md. Not yet implemented or tested.

Offsets are scoped to the recorded SHA256, checked against unique code signatures and live identity invariants. No SDK release exists.


