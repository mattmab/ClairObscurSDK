# SDK_API

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: our native reader and Python API enumerate live objects in Steam build 23765773. Reflection, invocation, hooks, and the full SDK remain unfinished.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Current research API

`expedition33.objects(*, limit: int = 0) -> list[ObjectSnapshot]` queries a running game. Zero means all occupied slots; positive limits bound returned objects. Each immutable record contains pid, index, serial, address, name, class_name, metaclass_name, and class_index. `RuntimeQueryError` reports native/protocol failure. Addresses and index/serial pairs are observations, not persistent validated handles.

PROVEN by live integration check: 96,053 objects including `/Script/CoreUObject` (Package), `Object` (Class), and the self-metaclass `Class`. Stored BoolProperty values are supported below; other value types, calls, and hooks remain unimplemented. Native class metadata is available below.

## Native class metadata

`expedition33.reflect_class(name) -> ClassMetadata` queries a uniquely named native Class. It returns the class hierarchy, instance sizes, and inherited property metadata (owner/name/type/offset/element_size/dimension). It rejects duplicate native class names; BlueprintGeneratedClass is outside this initial API. This metadata query returns no property values or persistent pointers.

PROVEN: Actor -> Object, sizes656/40, 80 properties; HUD -> Actor -> Object, sizes896/656/40, 96 properties. Object has no fields. Live check compares all inherited metadata and verifies bounds; unknown class fails explicitly. Reproduce with scripts/verify_live_reflection.py.

## Stored boolean observations

`expedition33.stored_bools(object_name) -> BoolSnapshot` resolves a uniquely named live native object and reads its inherited BoolProperty backing storage. It returns object identity observations and immutable values with owner/name/array element/raw byte/mask/byte offset. It does not invoke custom getters, pin objects, or create an atomic multi-property snapshot. Blueprint classes, other value types and writes remain unsupported.

PROVEN: Default__Actor index28233 exposes33 booleans; Default__HUD index29206 exposes39 including Actor fields. Repeated Actor snapshots matched. The live specimen has bHidden=false and bCallPreReplication=true in the same byte, with distinct reflected masks. scripts/verify_live_bools.py reproduces this build-scoped specimen check.

## Function metadata

`reflect_function("Actor.IsActorBeingDestroyed") -> FunctionMetadata` returns owner/name/index, process and game-thread IDs, flags, parameter buffer size, return offset, build-scoped entry RVA and reflected parameters. Owner/name ambiguity fails. This is a read-only inspection API; entry RVAs are research evidence, not externally callable pointers. The fixed invocation proof below is available; this metadata API itself remains read-only. scripts/verify_live_functions.py checks two independently decompiled boolean thunks, a24-byte struct return, and wrong-owner rejection.

## Fixed invocation proof

`invoke_proof() -> InvocationProof` performs the actual reflected call Default__Actor.IsActorBeingDestroyed on the game thread, returning process/thread IDs, live registry indices, boolean result and verified hook-removal/module-unload status. It accepts no target/function arguments. This is a controlled invocation experiment, not a general call API or gameplay feature. A skipped dispatcher leaves a0xcc sentinel and fails rather than returning a fabricated result.
