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

## Nested type descriptors

PROVEN 2026-10-08: PropertyMetadata now exposes optional struct_name, enum_name, inner_type and inner_element_size. These are descriptor observations, not property value conversion. Build-specific static derivation: live property vtables lead to 14136f810 (StructProperty +0x70 descriptor), 1412aa430 (EnumProperty +0x78 descriptor), 14136e840 (ByteProperty optional +0x70 enum), 14133ec00/14133f630 (ArrayProperty +0x78 child) and 1412abb90 (EnumProperty +0x70 child). Ghidra decompilation corroborates pointer use; function metadata remains provisional during ongoing whole-image analysis.

Native reader verifies descriptor registry identity, expected ScriptStruct/Enum class, serial stability, child ownership pointing to the parent FField, property class flags, positive bounded element size and stable pointer/prefix reads. Live validation on Actor, HUD, GameInstance, PlayerController, InputSettings and Console passed. Examples: Actor.PrimaryActorTick -> ActorTickFunction; RemoteRole -> ENetRole; UpdateOverlapsMethodDuringLevelStreaming -> EActorUpdateOverlapsMethod with ByteProperty storage; Tags -> NameProperty/8 bytes; GameInstance.LocalPlayers -> ObjectProperty/8 bytes.

Reproduce with scripts/verify_live_reflection.py. Evidence: nested-property-leads.json, nested-property-inner-owners.json, nested-property-decompile.json, nested-property-type.json, nested-property-accessors.json and nested-property-api.json. No recursive struct field expansion, enum member decoding, general array value reads, or GC lifetime guarantee is implied.

```python
import expedition33
for prop in expedition33.reflect_class("Actor").properties:
    print(prop.name, prop.type, prop.struct_name, prop.enum_name, prop.inner_type)
```
