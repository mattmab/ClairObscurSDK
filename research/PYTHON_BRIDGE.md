# PYTHON_BRIDGE

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: our native reader and Python API enumerate live objects in Steam build 23765773. Reflection, invocation, hooks, and the full SDK remain unfinished.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Python hosting is not selected yet

OBSERVED reference: pyunrealsdk embeds CPython with pybind11, runs a startup script, acquires the GIL for callbacks and logs caught Python exceptions. See REFERENCE_SDK_ARCHITECTURE.md for exact source paths and limitations.

DECIDED: D:/HobbyDevelopment/Python/expedition33-tools (Python 3.13.15) is the analysis environment, not a commitment to the eventual SDK interpreter ABI. It contains Ghidra's MCP bridge and PE tooling. Native game memory ownership and callback shutdown must be explicit regardless of hosting choice.

The first game-facing module now works through read-only native IPC; embedded Python hosting remains undecided.

## First working bridge

PROVEN: `src/expedition33` calls our native `research_probe.exe` via JSONL IPC. It requires successful process exit, matching begin/end records, matching counts, and unique indices before returning immutable snapshots. It has no static-dump fallback. Native access uses only process query and memory-read rights. The process executable SHA256 and runtime signature windows must match before enumeration.

This external reader minimizes the first experiment's lifecycle requirements. It is not yet an invocation or callback bridge; game-thread execution, GC lifetime, interpreter shutdown, and mod unloading remain open work.

## First game-thread execution path

PROVEN: external CPython -> native controller subprocess -> Windows thread-specific scheduling DLL -> validated reflected dispatcher -> shared-memory response -> Python InvocationProof. Python stays outside the game. The temporary bridge closes after each fixed call and verifies remote DLL unload. This is an execution bridge now, but persistent callback delivery and mod teardown remain unimplemented.

## First public-API mod: 2026-10-08

PROVEN: mods/ExampleMod/mod.py uses only sdk.Session.find_object/call/hook/poll and the public handle.remove method. It identifies Default__Actor, invokes the harmless getter, observes its native hook result, logs the copied context, then removes its subscription on disable. It contains no offsets, addresses, signatures or native layout knowledge.

PROVEN: scripts/verify_live_mod.py performed three load/enable/disable/unload cycles against PID25988. Each cycle produced one invocation log and one observed native event; duplicate lifecycle calls did not duplicate callbacks. Independent function metadata matched the baseline after every unload. Evidence: evidence/python-live-mod.json.

The loader imports only explicitly selected local root/Name/mod.py entries, assigns unique module names, makes no sys.path modifications, and removes its own sys.modules entry on unload. Mods define Mod.enable(session) and Mod.disable(). Each enabled mod owns a Session which the loader closes even if disable raises. Callback failures are already isolated by the session dispatcher. Unit tests additionally prove import SystemExit cleanup, enable SystemExit plus disable RuntimeError cleanup, and weak-reference release of the unloaded instance. Ten total Python tests pass.

LIMITS: this is trusted Python execution, not a security sandbox. A malicious or runaway mod cannot be contained by lifecycle exception handling. Arbitrary import side effects and threads spawned by mod code cannot be automatically rolled back. Only one enabled mod is currently supported because the native transport owns one fixed getter session. Startup/runtime packaging, a documented launcher and process-shutdown/relaunch integration remain pending; no v0.1 release claimed yet.
