# Expanded v0.1 progress assessment

Historical scope baseline: the user's subsequent release-convergence instruction
explicitly defers exhaustive parity. See RELEASE_CONVERGENCE.md for the frozen
release denominator, mandatory gates and execution order. Do not use this report's
expanded-scope workload estimate as the reduced release ETA.

Assessment date: 2026-10-09. Implementation baseline: 6c0cfc8.
This assesses the expanded user goal: independent SDK, original BL4 Harness,
native management workspace, console fallback, configurable keybinds and a
production-ready private package. The earlier bootstrap release is not evidence
that this expanded release is complete. No release approval is implied.

## Scoring method

Scores are conservative engineering estimates of requirement coverage, not
measured code coverage, probabilities of success or percentages of elapsed work.
Uncertainty in the overall estimate is approximately +/-10 percentage points.
Completed, tested subcapabilities earn credit; names, scaffolding, pending code
and an unfinished feature's mere existence do not. A subsystem may contain both
completed primitives and an incomplete end-to-end feature. For example, native
button lifecycle has evidence, but a three-minute menu is not a completed UI.

F = functional coverage supported by implementation and appropriate tests.
L = coverage of the full requested behavior with actual game evidence, including
its required contexts. It is not the fraction of existing tests that passed.
R = production/release acceptance coverage: usability, lifecycle, distribution
and validation completeness. A fixture pass alone cannot satisfy a live gate.
C = 0.50F + 0.30L + 0.20R. Overall = sum(weight * C) / 100.
These are planning scores, rounded only for display. No score overrides a failed
mandatory release gate. Unknown requirements remain uncredited.

| Subsystem | Weight | F | L | R | C (unrounded) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Independent foundation | 15% | 80 | 70 | 60 | 73 |
| Persistent Python and console | 10% | 85 | 75 | 65 | 78 |
| Original Introspection Harness | 18% | 65 | 50 | 40 | 55.5 |
| Native UMG Mods Menu | 12% | 35 | 25 | 15 | 28 |
| Configurable keybind system | 10% | 0 | 0 | 0 | 0 |
| Console fallback menu | 5% | 70 | 55 | 45 | 60.5 |
| Mod compatibility and lifecycle | 10% | 70 | 55 | 50 | 61.5 |
| Reliability and performance | 10% | 45 | 30 | 20 | 35.5 |
| Packaging and distribution | 5% | 50 | 40 | 30 | 43 |
| Live validation and release gates | 5% | 45 | 30 | 20 | 35.5 |

Weights total100%. Foundation/Harness receive33% because they are the independent
runtime and original port objective. Menu/keybind/fallback receive27% because
they are explicit user-facing requirements. Console/lifecycle receive20% and
cross-cutting reliability/distribution/final validation receive20%. Cross-cutting
rows assess integration and acceptance, not another count of individual APIs.

Weighted F=56.15%, L=44.75%, R=36.25%.
Weighted C=0.50*56.15+0.30*44.75+0.20*36.25=48.75%.

**Overall v0.1 completion:49%. Functional completion:56%.
Live validation coverage:45%. Release readiness:36%.**

## Evidence and subsystem gaps

1. **Independent foundation.** Independently derived UObject/FName registry,
   reflected metadata, bounded property reads, game-thread invocation and Python
   integration work on the fingerprinted build. Object identities, selected POD,
   enum/text and leased object results have tests and live specimens. This is a
   real SDK foundation, not a simulation. Unknown builds are rejected. Remaining:
   broader property/container codecs and mutations, arbitrary callable schemas,
   travel/GC validation and a stable documented public API. Read observations do
   not themselves pin engine objects. Evidence: OBJECT_SYSTEM.md, REFLECTION.md,
   OBJECT_LEASES.md, invocation/value code and tests, WIDGET_LAYOUT_VALUES.md.

2. **Console/runtime.** Native backtick console, Unreal commands, persistent
   external Python, output/errors, mod commands and SDK calls are live proven.
   Older console/observer runtimes have controller-death and relaunch evidence;
   those results do not automatically validate v18 combined with active menu and
   trace resources. Python history/completion APIs exist, but native Up/Tab for
   intercepted commands is unsupported. Long Python/actions can stall controller
   polling. Remaining: current-runtime integrated disconnect/reconnect/relaunch,
   input/context coverage and history/completion integration where feasible.
   Evidence: DEVELOPMENT.md console matrix, _console_dispatch.py, _console.py,
   evidence/console-v3-after-disconnect.json (viewport_console restored to null),
   console-game-exit.json, logs/trace-v18-host.log (live Python output).

3. **Harness.** Direct comparison against the preserved original core.py found
   identical normalized SHA256:
   6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543.
   Explorer roots/search/schema, selected inspection, snapshots/diffs, typed
   arguments, retained values, limited mutation, file protocol, agent aliases,
   actions and CLI have implementation and varying live coverage. Actual trace
   input/out/return specimens and hooked schema inspection passed; this is scalar
   native POST support, not the original SDK's broad hook/value semantics.
   Original core set uses generic reflected assignment; our supported set is
   scalar ObjectProperty. Four selected struct profiles, bounded containers and
   copied text do not equal arbitrary struct/container ownership. Blueprint and
   pointer-bearing trace values, broader writes, travel/expiry, and all original
   encodable types remain incomplete. Gearbox GameData/Kart is game-specific and
   unsupported, not silently counted as ported or assumed to exist in E33.
   Evidence: original/core comparison; INTROSPECTION_PORT.md; current adapter
   status still parity_complete=false; trace-getter-live.json,
   trace-locals-live.json, trace-out-harness-live.json all passed=true;
   trace-schema-live.log; agent-v17-package-bridge.json.

4. **UMG menu.** Runtime-created 12-control panel, shared Registry, navigation,
   actions, bool/choice editing paths and owned widgets exist. Live source and
   packaged main-menu open/Close returned holders and viewport focus to baseline.
   Those are bounded lifecycle proofs, not production acceptance. Source open
   took169.085 seconds; packaged open plus verification about175 seconds.
   Original MattsBL4ModsMenu1.3.3 provides search/filter/inspector, scrolling,
   editors, keys, reload, text scale and launcher placement. The current bounded
   E33 presenter is not interface parity: numeric/text/JSON editors, slider/key
   capture, workspace UX, reload controls and general focus contexts remain open.
   Evidence: actual archived README/workspace.py/__init__.py; management_native.py,
   management_view.py, MANAGEMENT_PORT.md; management-selected-{before,open,after}
   and package-management-{before,open,after}.json. The packaged before/after
   holder dictionaries compare exactly equal and after focus matches viewport.

5. **Keybinds.** No general E33 registration/remapping/conflict/input service was
   found in current src/mods/tests. Settings schema accepts keybind strings, but
   storage is not dispatch. Console F-key toggle is a separate narrow feature.
   Consequently this subsystem earns0%, including live coverage. Need native
   input discovery, stable action IDs, scoped registrations, keyboard/mouse
   handling, context/conflict rules, persistence, both editors and recovery.
   Compare original keybinds.pyi/register_keybind/deregister_keybind and menu
   key screens; no borrowed BL4 input ABI is acceptable.

6. **Fallback.** UMG-independent mods command uses the shared Registry for
   discovery/load/select/enable/disable/options/set/reset/actions/unload/back/quit.
   Native/py commands coexist and the working core has live evidence. No bind/
   unbind UI exists. Reload/install exist through separate agent/API routes but
   are not present in ConsoleMenu's command dispatcher/help. Grouped/nested
   presentation and full native-unavailable acceptance remain incomplete.
   Evidence: management_console.py, tests/test_management.py,
   MANAGEMENT_PORT.md live management sections and shared Registry probes.

7. **Lifecycle.** Mod scopes, generation checks, command/action cleanup,
   controlled digest reload, package-owned imports, staged install, root locking
   and recovery have tests; selected source/package live checks exercise real
   native calls and zero residual hooks. This is trusted Python ownership
   isolation, not a security sandbox or transparent compatibility with arbitrary
   BL4 mods. Core/global-dependency reload, broad multi-mod mixed-resource stress,
   new trace controller loss, gameplay/travel and recovered-install relaunch
   remain open. Evidence: mods.py, _scope.py, mod_install.py, tests/test_mod_*,
   evidence/staged-live-01c992a4f1aa4d059488e61f9af4e367 and corresponding journal,
   result/action records. Intentional failed import is a recovery specimen, not
   an unresolved production incident.

8. **Reliability/performance.** Game-thread gates, bounded transport, identity
   checks, owned cleanup and native fault fixtures are substantive. They cannot
   prove general memory/thread safety. Late-entry callbacks keep bounded native
   storage mapped until game exit; repeated session resource exhaustion needs
   testing. Full reads still create major latency. Menu construction and cleanup
   remain too slow. Need actual latency budgets, per-operation profiling,
   repeated cycles, GC/travel/context stress and nonblocking controller behavior.
   Evidence: native trace/menu ownership headers, their fixtures, prepared
   invocation/selected result implementation, MANAGEMENT_PORT.md timings.

9. **Packaging.** Has versioned immutable candidates, manifests, hashes,
   launcher, docs and previous isolated candidate game tests. Latest candidate
   20261009T211610Z references ee5913df4fda67b3ba8ccd902a6fe6a9dd9a1401 and393
   manifest entries; it contains no v18 binaries. Current package_dev.py also
   stops its backend list atv17. launch.cmd hardcodes
   D:\HobbyDevelopment\Python\expedition33-tools\Scripts\python.exe; Python is
   not bundled. Therefore this is not a self-contained clean-machine install.
   Need portable runtime/setup, current feature bundle, clean environment proof,
   reconciled docs, public API/version compatibility rules and final manifest.
   Only the tested game fingerprint is supported; multi-build support is unknown.

10. **Validation/release.** Latest inspected source suite:375/375 passing
    (evidence/trace-locals-regression.log); this audit did not rerun unchanged
    tests. Native fixtures have separate logs and package suites skip some
    unbundled fixtures. Existing latest live trace evidence proves only its
    specimens. Most recent broad UI tests are at the title screen, with no save
    loaded. No complete current-version17-item management acceptance run exists.
    World travel/GC, menu reopen stress, simultaneous mod resources, current v18
    disconnect/relaunch and clean-machine installation remain required.

Historical journals contain superseded status paragraphs; their newest entries,
current implementation and raw evidence take precedence. README/DEVELOPMENT and
MILESTONES must be reconciled before release. This assessment is the current
cross-subsystem baseline, not a replacement for the detailed journals.

## Release blockers and next five priorities

1. **Usable menu performance and focus lifecycle.** Profile actual construction,
   rendering and cleanup; remove redundant catalog/reflection/process work while
   preserving identity/schema gates. Establish measured responsiveness targets
   and prove repeated open/close plus return to the original input context.
2. **Complete general keybind service.** Derive the E33 native route; implement
   owner-scoped dispatch, remap/unbind/reset, deterministic conflicts, persistence
   and console recovery. Validate a real mod action and cleanup after relaunch.
3. **Finish unified management frontends.** Native numeric/text/JSON/slider/key
   editors and missing navigation/reload workflows; expose full management in
   console and prove both interfaces edit the same state. Preserve BL4 workspace
   requirements rather than treating the current12buttons as final parity.
4. **Close Harness and integrated lifecycle gaps.** Broader required value/write/
   trace coverage with target-derived ownership; v18 disconnect restoration,
   fresh-game relaunch, multi-mod cleanup, GC/travel and stale-event stress. Keep
   unsupported Gearbox-specific semantics explicit. Tests must cover the actual
   retained owners, not just copied return values.
5. **Build one portable release candidate and execute the complete matrix.**
   Include current runtime, clean-machine Python/setup, reconciled docs, manifest
   and compatibility checks. Run all17 management acceptance requirements and
   console/Harness regressions outside the checkout. Resolve failures before
   labeling it production-ready.

Next milestone: a responsive native management panel and first complete scoped
keybind flow, with shared console recovery and repeated input/focus restoration.
The already-planned v18 disconnect probe remains a short prerequisite lifecycle
check, not a reason to defer these larger missing user-facing capabilities.

## Work estimate and maintenance

Planning range: roughly160-320 focused engineering/validation hours (about4-8
full-time work weeks). This is not a promised elapsed ETA or a projection from
tokens. It assumes access to the current game build and no major new native
ownership/input blocker. Reverse engineering, gameplay bugs or broader parity
requirements could push it beyond that range; a calibrated schedule needs the
next input and performance milestones. Rough buckets: input/keybinds35-70h,
menu/performance/editors45-90h, Harness/lifecycle45-90h, packaging/docs/full-system
validation35-70h. These are judgment ranges, not measured task durations.

Update this file and the score table only when a significant capability gains
evidence, a mandatory gate passes/fails, or scope changes. Keep the same weights
and definitions unless the user changes scope; record score changes and evidence.
No percent increase for commit count, test count or another narrow specimen alone.
This status review does not pause the development goal.
