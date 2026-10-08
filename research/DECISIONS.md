# DECISIONS

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Current decisions: retain a build-gated independent runtime, external persistent Python, copied event/command transport, explicit GameThread engine operations and narrowly validated object lifetimes. Private source control and D: placement remain mandatory. Earlier entries below preserve the chronological decisions and superseded setup state.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Architecture decision 001

USER REQUIREMENT: Keep discovery replaceable, addresses out of the public API, and all unknown builds closed to unsafe operations. PROVISIONAL: begin with read-only external observation if practical; defer embedded Python and injection until justified by target evidence. No public SDK API is implemented yet.

OBSERVED: Nine reference repositories cloned and pinned in evidence/reference-revisions.json. No reference code has been copied into the SDK implementation.

USER AUTHORIZATION UPDATE: User requests a private GitHub repository under their account. GitHub integration is not yet connected. Local commit attempt failed because Git author identity is unset; no identity was invented.

## GitHub infrastructure

PROVEN: Connected account mattmab. Created mattmab/ClairObscurSDK with Private selected; post-create GitHub UI displays Private. Git push succeeded and ls-remote main equals local 3c2b2d6e75c99d9cb5dd613afd424c186582e98b. Existing Git credentials worked without exposing secrets. Connector get_repo initially returned 404 for the new private repo; browser and Git transport independently verified creation/push.

Repository-local author uses confirmed GitHub login and ID-based noreply address. No global identity was changed. No game binary, asset, dump, database, local evidence or credential is tracked.

## Validated architecture decisions

External CPython is retained for v0.1: ordinary Python errors cannot unwind through the game's native stack, and the game loop does not execute Python. Engine operations use the independently tested GameThread transport. Bounded copied queues expose overflow rather than silently retaining unlimited events.

Native callback code remains pinned until process exit to protect late-fetched function pointers. Uninstall means restoring the function/vtable entry and detaching session-owned state; it does not falsely promise safe DLL unloading while another thread may retain a code pointer. Fixtures and live close/disconnect/shutdown tests support this distinction.

Public calls/hooks remain restricted to the verified permanent-prefix default Actor getter. Console ownership is a separate validated lifecycle with viewport attachment, identity checks and engine state transitions. Neither path establishes arbitrary GC-safe UObject ownership. Read-only property descriptors are expanded only after static and live corroboration.

Private release packaging requires a clean committed source tree, records its exact revision and file hashes, and excludes game data and local research evidence. This is a reproducibility check, not a security signature. The source audit found all17 requested journals and no forbidden binary/asset/database outputs in tracked files (evidence/release-source-audit.json).
