# SDK_API

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: our native reader and Python API enumerate live objects in Steam build 23765773. Reflection, invocation, hooks, and the full SDK remain unfinished.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Current research API

`expedition33.objects(*, limit: int = 0) -> list[ObjectSnapshot]` queries a running game. Zero means all occupied slots; positive limits bound returned objects. Each immutable record contains pid, index, serial, address, name, class_name, metaclass_name, and class_index. `RuntimeQueryError` reports native/protocol failure. Addresses and index/serial pairs are observations, not persistent validated handles.

PROVEN by live integration check: 96,053 objects including `/Script/CoreUObject` (Package), `Object` (Class), and the self-metaclass `Class`. Property values, calls, and hooks are not implemented. Native class metadata is available below.

## Native class metadata

`expedition33.reflect_class(name) -> ClassMetadata` queries a uniquely named native Class. It returns the class hierarchy, instance sizes, and inherited property metadata (owner/name/type/offset/element_size/dimension). It rejects duplicate native class names; BlueprintGeneratedClass is outside this initial API. No property values or persistent pointers are returned.

PROVEN: Actor -> Object, sizes656/40, 80 properties; HUD -> Actor -> Object, sizes896/656/40, 96 properties. Object has no fields. Live check compares all inherited metadata and verifies bounds; unknown class fails explicitly. Reproduce with scripts/verify_live_reflection.py.
