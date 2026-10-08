# KNOWN_UNKNOWNS

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN on the recorded build: live object/name enumeration, native class hierarchy and property/function metadata, stored boolean reads, a fixed game-thread reflected call, persistent scoped observation of that getter, and local mod enable/disable/unload. Native console construction, Unreal command passthrough, persistent external Python commands, mod command registration/removal, controller-death cleanup, combined console/observer game shutdown, and packaged operation after relaunch have live evidence. Configured F10 opening/closing/reopening and Python state retention are also live-proven.

Remaining research: complete and durably save an appropriate Ghidra analysis pass after the recorded analyzer memory failures; expand independently verified nested array/struct/enum metadata; finish actor/component and local-player relationship evidence. General property values beyond stored bools, arbitrary function marshalling, arbitrary-object GC ownership, synchronous event cancellation and multiple enabled mods remain unsupported. Fixed-target lifecycle evidence must not be generalized to arbitrary objects.

Native Up/Tab integration for intercepted Python/custom commands is unsupported; dispatcher history and lexical completion APIs exist. Configurable keys are limited to an additional F1-F12 toggle, with F10 tested; this does not remap Unreal's existing Tilde binding. Gameplay/map-transition validation and all-key coverage remain unproven. The latest tested isolated package contains v4; the working v5 key addition needs a refreshed package validation before distribution.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.
