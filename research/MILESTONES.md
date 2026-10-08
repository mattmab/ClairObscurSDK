# MILESTONES

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Current state: 1/12 (build fingerprint established; inventory follow-ups remain)

0. Environment inventoried — D: tree and installed apps inspected; MSVC 14.44.35207 and Windows SDK 10.0.26100.0 installed; x64 fixture compilation and execution proven.
1. Target game/build fingerprinted — SHA256, x64 PE headers, local Steam build identified.
2. Ghidra MCP operational — pending; dependency fetch succeeded, existing Ghidra source distribution compiling. MCP bridge handshake alone is proven; backend validation still pending.
3. Expedition 33 binary analyzed — pending Ghidra.
4. Unreal runtime anchors identified — pending.
5. Name/object infrastructure understood — pending.
6. Native probe enumerates live objects — pending.
7. Python queries live objects — pending (first capstone).
8. Reflection/property reads — pending.
9. Safe invocation — pending.
10. Hooks/callbacks — pending.
11. Minimal mod loader — pending.
12. Private SDK package/docs/trivial mod — pending.

No runtime offsets are validated. No SDK release exists.
