# SDK 0.1.0-rc5: bundled LiveObjectViewer and runtime notices

This prerelease bundles **SDKManagement**, **IntrospectionHarness** and
**LiveObjectViewer 0.2.0 candidate** in the SDK ZIP. ContinentFlight, Picto Editor,
Statistics and Cinematics remain optional downloads in the
[Mods catalog](https://github.com/mattmab/ClairObscurSDK/blob/main/mods/README.md).

Close the game and SDK controller before upgrading. Extract into the game root,
preserving `SDK/settings`. Start normally, enable LiveObjectViewer in **Pause →
Mods**, and select **Open Live Object Viewer**, or use `lov` in the native console.
Existing enabled/disabled choices are preserved; the viewer is not automatically
enabled on a fresh install.

The viewer adds focused live property monitoring, snapshots/comparison, bookmarks,
filters and guarded scalar editing. Boolean and float32 edits have recorded live
readback/restoration evidence, including a mounted Esquie session. Int32/float64
have protocol tests but no live write specimen; party-screen focus and travel need
additional live acceptance. Large reference-property batches can still be slow.
This is not a claim of complete Oak2 parity. See the
[viewer documentation](https://github.com/mattmab/ClairObscurSDK/blob/main/mods/LiveObjectViewer/README.md).

The rebuilt native runtime includes the viewer input/scalar protocols and
frame-aware menu dispatch through the existing message pump. The installed reader
path retains its Picto-compatible name; its payload is the viewer-enabled build,
which resolves `build/runtime-session-viewer-v2/runtime_session_viewer_v2.dll`.

Validation: native runtime and reader rebuilt with MSVC `/W4 /WX`; **1,017 Python
tests passed**. A fresh extraction passed the embedded controller's `--check` with
all three mod archives and regenerated hashes. No new RC5 whole-game test was
performed; existing candidate live evidence and its limitations are recorded in
`research/VIEWER_VALIDATION_2026-10-12.json`.

First-party SDK/mod source remains MIT. The unmodified CPython 3.13.15 runtime
retains its original license and now ships supplemental authentic notices,
component/source/hash inventory and fail-closed packaging checks. All 34 runtime
files and 20 notice/reference files passed verification. Microsoft redistribution
entitlement/downstream agreement questions remain unresolved; publication does
not claim legal clearance. See the
[remediation report](https://github.com/mattmab/ClairObscurSDK/blob/main/docs/audits/runtime-license-remediation.md).

Build: run `scripts/build-viewer-candidate.cmd`, prepare the existing bootstrap
with `scripts/build-bootstrap.cmd` if absent, then run
`python scripts/package_release_candidate.py dist/installable-rc5 --version 0.1.0-rc5`.
The destination must not already exist. The runtime notice manifest is checked
before staging and again against the final archive.

SHA256: `63bbc73e5e9e0d19aa7ea9fe5f0f907e57ccfcb4b3dc7bf7af376f439536a859`
