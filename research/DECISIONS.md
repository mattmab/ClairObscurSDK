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
