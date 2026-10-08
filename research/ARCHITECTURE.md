# ARCHITECTURE

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: independent external enumeration/reflection, stored boolean reads, a narrow game-thread reflected call and observer, persistent external Python sessions, native console dispatch, and local mod lifecycle. Arbitrary calls/handles and broader property conversion remain unsupported.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Current architecture, after reference inspection

USER REQUIREMENT: BuildFingerprint -> RuntimeDiscovery -> UnrealRuntime -> safe reflection/invocation -> Python binding -> public API -> mod lifecycle. References and source-backed lessons are in REFERENCE_SDK_ARCHITECTURE.md.

DECIDED: Do not implement guessed layouts or a fake public objects() API. The initial native probe will use only a validated build and primitive. A static scanner is analysis tooling, not that probe.

IMPLEMENTED: the native external reader exposes immutable live observations to Python. A small pinned in-process DLL owns verified GameThread scheduling, the fixed getter observer, and per-instance native console hooks. The external CPython controller owns persistent state and mods; copied bounded queues carry console input and observer events. Python never runs on the GameThread. Session teardown restores owned entries/pointers, clears registrations and releases Python references, while DLL code stays pinned for prefetched late calls until process exit.

Required invariants: reject unsupported build before applying layouts; distinguish not-found from ambiguous discovery; bounds-check registry counts and chunks; validate object index/class/name relationships across multiple specimens; handle destruction/reuse; keep unsafe operations unavailable until each prerequisite is proven.
