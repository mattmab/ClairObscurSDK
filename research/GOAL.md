# GOAL

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: our native reader and Python API enumerate live objects in Steam build 23765773. Native reflection and nested type descriptors, stored booleans, fixed reflected invocation, persistent getter observation, mod lifecycle and native-console persistent Python have live proof. Broader APIs and final research validation remain unfinished.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Active goal and scope

USER REQUIREMENT: Build an independent Python SDK for locally owned/offline Expedition 33. First capstone: our Python code enumerates real live objects through our independently validated native runtime layer. Static dumps, asset lists, and hard-coded names cannot satisfy it.

USER REQUIREMENT: Follow stages 0-12 in MILESTONES.md; no gameplay features first; no DRM/anti-cheat/authentication bypass; no public push or release. All new project material lives on D:. Existing installed tools may be reused.

The complete request is preserved locally in USER_REQUEST.txt and USER_REQUEST_CONTINUED.txt (excluded from Git).

PROVEN checkpoint (2026-10-08): independent Python live enumeration, useful reflection/bool reads, reflected getter invocation, persistent getter hooks, copied Python callbacks and a trivial mod lifecycle now work against the fingerprinted build. Stage 11/12 frontier; whole-image Ghidra analysis and release validation/packaging remain unfinished. See MILESTONES.md for limits rather than interpreting this checkpoint as project completion.
