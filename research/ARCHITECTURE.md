# ARCHITECTURE

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Current architecture, after reference inspection

USER REQUIREMENT: BuildFingerprint -> RuntimeDiscovery -> UnrealRuntime -> safe reflection/invocation -> Python binding -> public API -> mod lifecycle. References and source-backed lessons are in REFERENCE_SDK_ARCHITECTURE.md.

DECIDED: Do not implement guessed layouts or a fake public objects() API. The initial native probe will use only a validated build and primitive. A static scanner is analysis tooling, not that probe.

PROVISIONAL: Prefer an external read-only first probe where feasible. In-process scheduling, allocation, dispatcher calls and Python hosting are deferred until game evidence supports them. A process handle alone does not satisfy the object-identification milestone.

Required invariants: reject unsupported build before applying layouts; distinguish not-found from ambiguous discovery; bounds-check registry counts and chunks; validate object index/class/name relationships across multiple specimens; handle destruction/reuse; keep unsafe operations unavailable until each prerequisite is proven.
