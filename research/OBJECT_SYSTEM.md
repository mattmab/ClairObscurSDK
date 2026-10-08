# OBJECT_SYSTEM

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Reference lessons, target still unknown

OBSERVED in BL-SDK: native registry access and FName resolution underpin lookup. A Python wrapper's existence is independent of the engine object's lifetime. py::nodelete avoids deleting engine-owned memory but cannot guarantee the pointer stays valid. Reference WeakPointer uses registry index/serial validation where supported.

HYPOTHESIS to test for Expedition 33: a chunked object registry and interned name pool. Do not import chunk size, entry stride, flags or offsets. Evidence required: static access paths plus runtime identity consistency across multiple objects and repeated observations.

No Expedition 33 object pointer has been read by our code yet.
