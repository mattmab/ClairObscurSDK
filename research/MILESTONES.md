# MILESTONES

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Stages 0-12 are established within the documented private v0.1 scope, including live Python objects, console/mod control, packaging and completed analysis persistence.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Current state: private v0.1 scope complete

0. Environment inventoried — D: tree and installed apps inspected; MSVC 14.44.35207 and Windows SDK 10.0.26100.0 installed; x64 fixture compilation and execution proven.
1. Target game/build fingerprinted — SHA256, x64 PE headers, local Steam build identified.
2. Ghidra MCP operational — proven by fixture import, metadata/function queries, decompilation, and exact annotation persistence after save/close/reopen. See GHIDRA_MCP.md.
3. Expedition 33 binary analyzed: reduced pass completed at18:23:16 after3437.01 seconds, following recovery from two failed passes. Saved successfully; close/reopen returned306134 functions and2182806 symbols with all7 new annotations exact. Missing matching PDB, localized demangler/exception/decompiler warnings and disabled analyzers remain documented in GHIDRA_MCP.md.
4. Unreal runtime anchors: object registry and name pool proven; dispatcher and GameThread ID corroborated; engine/viewport/world/game-instance relationships observed by console runtime probes. Main-menu LocalPlayer/viewport/controller reciprocal links, GameInstance.LocalPlayers membership, and controller/root-component/Outer links are observed by a bounded read-only probe. Gameplay/map transitions remain unvalidated.
5. Name/object infrastructure: chunk traversal, identity fields, name decoding proven; GC lifetime and broader reflection remain pending.
6. Native live enumeration: PROVEN with our read-only external process reader.
7. Python live queries: PROVEN, 96,053 objects across two registry chunks in 1.967 seconds.
8. Reflection/property reads: native class inheritance, property metadata and nested struct/enum/array type descriptors PROVEN; stored BoolProperty reads PROVEN; other value types and GC-safe handles pending.
9. Safe invocation: PROVEN Python -> native -> game-thread reflected dispatch -> boolean return on Default__Actor; general marshalling remains pending.
10. Hooks/callbacks — persistent UFunction observer and public sdk.Session handles PROVEN on the harmless getter, including Python SystemExit containment, ten enable/disable cycles, normal close, controller death cleanup and reopen. Independent native fixture proves concurrent removal/late-entry lifetime. Normal game shutdown with observer and console active exited0; a relaunched game passed isolated package smoke validation.
11. Minimal mod loader — PROVEN through three live ExampleMod load/enable/disable/unload cycles; import and lifecycle failure cleanup and module/instance release covered by unit tests. Explicit trusted local mods only; one enabled mod at a time.
12. Private SDK package/docs/trivial mod — isolated v4 candidate smoke and native console Python/mod execution passed after normal game relaunch. Native commands, persistent external Python output/state/errors/SDK calls, custom command registration/removal and console-specific controller-death cleanup are live-proven. Working v5 adds F1-F12 configuration; F10 opening/closing/reopening and retained Python state are live-proven. The isolated v5 package passed smoke and console/Python/mod execution after relaunch; F10 removal and normal-close cleanup passed. Game exit with console/F10/observer active returned0 and cleared Python state. Native Python history/completion navigation remains unsupported; dispatcher APIs exist. See CONSOLE.md for boundaries.

Offsets are scoped to the recorded SHA256, checked against unique code signatures and live identity invariants. Private v0.1 is packaged and validated below; the reduced Ghidra pass has now completed and passed save/close/reopen verification.



## Nested-metadata candidate validation

PROVEN 2026-10-08: expedition33-0.1.0-candidate-20261008T213251Z.zip (SHA256 b716dd34742ab73149e6c826ba63701862f468c22aca479b661394b1ca8d179d, source c204cbb) was extracted to a fresh D: package-validation directory and launched with CPython -I -S -B. Manifest checks passed. PID34604 returned96053 live objects,80 Actor fields and33 stored booleans; ExampleMod made the fixed game-thread call, received its observer callback, and unloaded normally. Native session/console DLL is unchanged from the earlier v5 lifecycle tests. This candidate adds the validated nested descriptors in the external reader/Python API; later documentation-only edits are in the repository.


## Private v0.1 development release

PROVEN: dist/expedition33-0.1.0-private-20261008T221641Z.zip, SHA256 72765fe1d896762b67a7454f1da3665479f540a42ccbfa4082c4512e7cbaf717, clean source commit e82dd8e6e3946d9e00a14f21def778fd8d0c1ccf. Fresh extraction under D:/HobbyDevelopment/Analysis/ClairObscurSDK/private-v0.1-validation-20261008T221641Z passed all98 file hashes and archive CRC checks. No game assets, databases, dumps or local evidence are packaged.

Isolated -I -S -B smoke in PID34604 enumerated96053 objects, read80 Actor fields/33 booleans, invoked the fixed reflected getter, delivered its observer callback and unloaded ExampleMod. A separate bounded console launch with F10 loaded ConsoleExample, attached the native console and detached normally, exit0. This release uses the exact native v5 DLL already validated visually for native/Python/mod commands, F10/Tilde, cleanup and relaunch; hash equality was verified. The final Python output escaping fix additionally has unit and live transport/session-continuity evidence. Local result: evidence/private-v0.1-package.json; logs are in the extracted bundle's logs/sdk.log.

This earns the user's functional private v0.1 release criteria. The subsequent reduced whole-image pass also completed and passed save/close/reopen verification. This does not claim exhaustive binary understanding, warning-free analysis or broader unsupported APIs. The immutable release archive predates that final research-only update; its runtime payload remains validated.
