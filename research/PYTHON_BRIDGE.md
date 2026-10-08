# PYTHON_BRIDGE

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Python hosting is not selected yet

OBSERVED reference: pyunrealsdk embeds CPython with pybind11, runs a startup script, acquires the GIL for callbacks and logs caught Python exceptions. See REFERENCE_SDK_ARCHITECTURE.md for exact source paths and limitations.

DECIDED: D:/HobbyDevelopment/Python/expedition33-tools (Python 3.13.15) is the analysis environment, not a commitment to the eventual SDK interpreter ABI. It contains Ghidra's MCP bridge and PE tooling. Native game memory ownership and callback shutdown must be explicit regardless of hosting choice.

No game-facing Python module is implemented or claimed to work.
