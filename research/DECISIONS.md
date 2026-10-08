# DECISIONS

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Architecture decision 001

USER REQUIREMENT: Keep discovery replaceable, addresses out of the public API, and all unknown builds closed to unsafe operations. PROVISIONAL: begin with read-only external observation if practical; defer embedded Python and injection until justified by target evidence. No public SDK API is implemented yet.

OBSERVED: Nine reference repositories cloned and pinned in evidence/reference-revisions.json. No reference code has been copied into the SDK implementation.

USER AUTHORIZATION UPDATE: User requests a private GitHub repository under their account. GitHub integration is not yet connected. Local commit attempt failed because Git author identity is unset; no identity was invented.

## GitHub infrastructure

PROVEN: Connected account mattmab. Created mattmab/ClairObscurSDK with Private selected; post-create GitHub UI displays Private. Git push succeeded and ls-remote main equals local 3c2b2d6e75c99d9cb5dd613afd424c186582e98b. Existing Git credentials worked without exposing secrets. Connector get_repo initially returned 404 for the new private repo; browser and Git transport independently verified creation/push.

Repository-local author uses confirmed GitHub login and ID-based noreply address. No global identity was changed. No game binary, asset, dump, database, local evidence or credential is tracked.
