# REFERENCE_SDK_ARCHITECTURE

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Source-backed reference study (2026-10-08)

OBSERVED in unrealsdk ac31716b2b462e78f0a841b6d352aa2fa56c7f92 and pyunrealsdk cb5fc362ea228727f334d94b64eb9538d8778bc6. Paths below are relative to their cloned repository roots under D:/HobbyDevelopment/Repos. These are implementation observations, not proofs about Expedition 33.

### End-to-end path

Running process -> game-specific discovery (game/*) -> offset-aware UObject/UClass/UStruct/UFunction and property wrappers -> native SDK -> pybind11 embedded modules -> Python initialization script/mod ecosystem.

- Discovery: game/abstract_hook.h provides the native adaptation surface; game/bl4/bl4.cpp selects PGO/non-PGO discoveries and resolves object/name infrastructure, allocators, dispatch, path lookup, object search, and other primitives. No signatures were transferred. BL4 startup also calls protection-related routines; those are outside this project's scope and are not adopted.
- Representation: unreal/offsets.h defines field getters through an offset table. Its presence is evidence that Unreal conceptual similarity does not imply one universal memory layout. UObject identity includes class, name, outer and internal index (unreal_bindings/uobject.cpp). The target's corresponding fields still need independent discovery.
- Object registry: unreal/wrappers/gobjects.cpp abstracts TArray versus FUObjectArray. Iteration skips null entries; source itself notes GC handling limitations. It is not a ready-made safe concurrent enumeration guarantee.
- Names: unreal/structs/gnames.cpp supports chunked name storage and an FNamePool accessor. Bit splits, stride, encoding and pool layout are version-specific, not generic constants to copy.
- Reflection: pyunrealsdk unreal_bindings/property_access.cpp looks up fields through UStruct metadata and distinguishes FField properties from UObject-based fields by flavour. UObject.__getattr__ routes through this metadata, rather than generated per-game Python classes.
- Invocation: unreal/wrappers/bound_function.cpp validates parameter flags, serializes with FunctionCall lock, temporarily adds FUNC_NATIVE, calls internal process_event, then restores flags. This is reference behavior only; Expedition's flags, dispatcher ABI, thread constraints, cleanup and parameter representation require experiments. A flag restoration path is not automatically exception-safe.
- Native/Python conversion: pyunrealsdk/type_casters.cpp downcasts through Unreal runtime types and explicitly manages new/stolen Python references across the bridge. Property helpers dispatch by property category; arrays/structs receive wrapper types. This motivates a small supported-type set with explicit failures, rather than guessing unknown types.
- Hosting: pyunrealsdk.cpp registers PYBIND11_EMBEDDED_MODULE(unrealsdk), initializes CPython after native SDK readiness, redirects logging, registers console commands, runs configurable __main__.py, catches initialization-script exceptions and releases the GIL with PyEval_SaveThread. The source preserves startup thread state; clean interpreter restart/shutdown is not established by this file.
- Hooks: hook.cpp captures callbacks in StaticPyObject, acquires the GIL at invocation, catches std::exception and logs Python errors, returning without blocking on failure. It defines pre/post semantics and a thread-local recursion-control context. This does not contain arbitrary access violations or corrupted native state.
- Ownership: PyUEClass in unreal_bindings/bindings.h uses py::nodelete. Python does not own/deallocate engine UObjects. WeakPointer plus registry index/serial validation exists separately (weak_pointer.cpp, gobjects.cpp). nodelete alone does not prevent stale dereferences. UnrealPointer manages owned struct/property buffers and destructor behavior, a different lifetime from engine objects.
- Mod loading: pyunrealsdk README/init implementation loads a configured startup script. A full enable/disable/unload mod manager is not implemented by that initialization routine. Do not mistake Python bootstrap for a mod lifecycle system.

### What transfers conceptually

Objects have identity and type; names are interned; reflection describes field types/offsets and function parameters; runtime dispatch can be bridged; language runtimes require thread/ownership discipline. Each binary representation and game-thread rule must be rediscovered.

### What does not transfer as evidence

Borderlands signatures, offsets, flavour layouts, compiler/PGO behavior, name-pool encoding, function-flag workarounds, console injection, Gearbox-specific FGBX types, protection startup behavior, and mod-manager assumptions.

### Other references evaluated

OBSERVED from cloned READMEs (exact revisions in ../evidence/reference-revisions.json): Universal Modder provides engine routing and a reusable knowledge/journal workflow; REA separates provider adapters and provenance-bearing evidence, but introduces another abstraction layer and documents an experimental Windows Ghidra boundary. AI Game Modding Guides describe iterative harness-driven projects and source-of-truth discipline. Use those lessons without installing overlapping orchestration frameworks.

Ghidra MCP is selected for persistent native analysis and annotations, subject to an end-to-end proof. IDA MCP requires IDA 9.4+ with idalib; no reason yet to add a second native disassembler. ILSpy targets managed assemblies and Cpp2IL targets Unity IL2CPP; neither has a proven target here, so neither is installed or run.

### Design implications (INFERRED; provisional)

Build fingerprint -> replaceable discovery -> validated native handles -> safe reflection/dispatch -> Python bridge -> tiny API -> lifecycle-managed mods. First probe should be external/read-only if sufficient, to limit crash coupling; later invocation/hooks may justify in-process components. Python hosting remains undecided until runtime evidence and thread requirements are known.
