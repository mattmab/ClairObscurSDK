# BL4_VS_EXPEDITION33

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## What BL-SDK already did for us

OBSERVED source-backed comparison: BL-SDK supplies engine-version adaptation, registry/name access, field lookup, parameter storage, dispatch, detours, Python conversions, GIL acquisition, and logging. A mod author's object.Property expression hides all of that infrastructure.

INFERRED difference: target's embedded 5.4.4 string and MSVC runtime imports differ from the reference README's tentative BL4 UE5.5/Clang+PGO description. Neither claim establishes the exact target ABI. Borderlands engine flavours and Gearbox-specific data types do not transfer automatically.

Unknown here: object/name layouts, GC/lifetime behavior, reflection offsets, dispatcher ABI, safe game thread, hook coverage, interpreter shutdown. These must become experiments before an SDK exists.
