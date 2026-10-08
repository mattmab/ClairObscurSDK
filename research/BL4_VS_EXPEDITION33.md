# BL4_VS_EXPEDITION33

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Source-backed reference comparison and independently validated Expedition 33 primitives are available. The current SDK is a narrow research implementation; it does not claim BL-SDK feature parity.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## What BL-SDK already did for us

OBSERVED source-backed comparison: BL-SDK supplies engine-version adaptation, registry/name access, field lookup, parameter storage, dispatch, detours, Python conversions, GIL acquisition, and logging. A mod author's object.Property expression hides all of that infrastructure.

INFERRED difference: target's embedded 5.4.4 string and MSVC runtime imports differ from the reference README's tentative BL4 UE5.5/Clang+PGO description. Neither claim establishes the exact target ABI. Borderlands engine flavours and Gearbox-specific data types do not transfer automatically.

PROVEN here after the initial comparison: target-derived object/name layouts, native reflection metadata, the GameThread reflected getter path, bounded observer hooks and lifecycle, external persistent Python, and native console/Python command routing. Lifetime is restricted to verified permanent-prefix targets plus separately validated console ownership; arbitrary GC-safe objects and broad marshalling remain open. Unlike the reference embedded interpreter, our Python process is external and services copied queues. Native console entry therefore crosses our transport before Python/mod execution. This boundary contains Python errors and controller shutdown without placing the interpreter on the GameThread.
