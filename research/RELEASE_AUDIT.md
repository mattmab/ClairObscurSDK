# Private v0.1 requirement audit

Updated: 2026-10-08. This audit preserves the requested scope. A passing narrow
specimen does not establish support for arbitrary Unreal objects or functions.

| Requirement | Inspected evidence / boundary | Result |
| --- | --- | --- |
| D: workspace, dependencies and research journal | Source, builds, Python environment, reference clones and Ghidra project on D:. Reused Java/Python base and installer-managed Windows SDK exceptions documented in GHIDRA_MCP.md. All requested journal files exist. | Proven |
| Game inventory and fingerprint | GAME_BUILD.md; binary-fingerprints.json, shipping-pe-independent.json, all-pe-module-inventory.json; normal Steam launch. No game assets or binaries tracked. | Proven |
| Reference architecture study | Nine pinned clones; REFERENCE_SDK_ARCHITECTURE.md and BL4_VS_EXPEDITION33.md cite inspected paths and distinguish reference behavior from target evidence. | Proven |
| Operational Ghidra MCP | Fixture imported, queried, decompiled, annotated, saved, closed and reopened; exact comment persisted. GHIDRA_MCP.md records versions and evidence. | Proven |
| Appropriate shipping analysis completes and persists | Recovered baseline saved; reduced pass currently running. Catalog, strings, rejected RTTI lead and startup/tick/exit path recorded. Final pass completion and reopen verification pending. | Pending |
| Independent object/name runtime | OBJECT_SYSTEM.md; native research_probe.cpp performs live registry/name reads after hash/signature validation. Fresh isolated bundle enumerated 96,053 real objects in PID34604. | Proven |
| Runtime relationships | Live reflection and inspect_runtime_relationships.py corroborate viewport/game-instance/local-player/controller/component chain at main menu. No gameplay transition claim. | Observed |
| Reflection and safe reads | verify_live_reflection.py, verify_live_bools.py, verify_live_functions.py passed against live game; hierarchy, bounds, 33 Actor/39 HUD booleans, nested type descriptors. General value conversion remains unsupported. | Proven |
| Harmless reflected invocation | Fixed Default__Actor.IsActorBeingDestroyed through verified dispatcher on GameThread; return false, sentinel detects skipped calls. Live fixture, session and package smoke evidence. | Proven |
| Python event hook and removal | verify_live_sdk.py: ten install/remove cycles, copied identity/result, exception isolation and restored entry. Observer fixture: concurrent removal and late-fetched callback safety. | Proven |
| Trivial public-API mod | ExampleMod source uses only Session lookup/call/hook/poll and handle.remove; three live lifecycle cycles plus isolated package smoke. No addresses or signatures in the mod. | Proven |
| Unknown-build rejection | compatibility.json and verifier exercise normal startup's supported_image gate: supported image accepted; same-size changed hash, wrong size and missing file rejected before attachment. | Proven |
| Deterministic external Python and logging | Isolated -I -S -B launcher pins 3.13.15, verifies bundle import/manifest, rotates logs; native events copied to owning Python thread. | Proven |
| Python/mod exception containment | Twenty unit tests; live callback SystemExit containment; in-game Python traceback returned without game crash. Trusted mod side effects/threads are not sandboxed. | Proven within documented scope |
| Native console UI and Unreal path | UConsole construction/viewport attachment and native command path derived from target; Tilde opening/closing, stat fps/CVar behavior tested live. | Proven |
| Persistent in-game Python control | Native input intercepted into bounded transport; external persistent namespace executes print, variables/imports, SDK and loaded-mod calls; output/repr/tracebacks returned to UI/log. CONSOLE.md records live experiments. | Proven |
| Configurable key and custom commands | F1-F12 implemented; F10 open/close/reopen/removal/relaunch tested. Mod command registration/removal tested; ownership replacement drops stale queued SDK commands. | Proven for F10; other keys untested |
| Console history/completion | Dispatcher history/lexical completion APIs exist. Native Up/Tab integration for intercepted commands is unsupported and explicitly documented. | Optional feature partially implemented |
| Disconnect, shutdown and relaunch | Controller-death console detachment; game exit0 with observer/console/F10 active; SESSION_TARGET_EXITED clears namespace; isolated v5 console/mod run after normal Steam relaunch. | Proven |
| Private Git infrastructure | Repository created with Private selected and post-create UI verification recorded in DECISIONS.md; authenticated Git pushes continue. Connector lacks access; no visibility mutation performed. | Proven creation; Git transport working |
| Installation, education and checklist | README.md, DEVELOPMENT.md, SDK_API.md and research journals describe usage, why primitives work, source references, failure history, supported/unsupported behavior. | Implemented |
| Private v0.1 development release | Candidate c204cbb archive and manifest passed isolated live smoke. Version0.1.0 source is prepared; final archive verification is next. The separate completed-analysis requirement remains pending. No public publishing authorized. | Ready for packaging |

The evidence supports a small build-specific SDK, not BL-SDK feature parity.
Arbitrary function marshalling, object GC ownership, writes, synchronous event
cancellation, multiple enabled mods and gameplay/map-transition validation remain
unsupported. These are explicit API boundaries, not substitutes for the required
five demonstrated capstones or console lifecycle acceptance tests.
