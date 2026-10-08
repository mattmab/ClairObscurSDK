# REFLECTION

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: live native class inheritance, property metadata, stored booleans, and function parameter metadata. See OBJECT_SYSTEM.md and FUNCTION_INVOCATION.md for code-backed derivations.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Reproducible surface

- reflect_class("HUD"): HUD -> Actor -> Object,96 inherited/direct properties.
- stored_bools("Default__Actor"):33 stored values; Default__HUD39. Shared-byte masks independently corroborated by target export routine.
- reflect_function("Actor.IsActorBeingDestroyed"): one-byte reflected boolean return, no input parameters.

All queries read the running process through our own native reader, reject unsupported hashes, and verify object identity relationships. scripts/verify_live_reflection.py, verify_live_bools.py and verify_live_functions.py exercise actual live specimens. This is not a general safe handle system: no object pinning or atomic GC snapshot exists yet. Arrays, structs, enums and broader scalar conversion remain pending; a type name alone is not a value decoder.
