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
