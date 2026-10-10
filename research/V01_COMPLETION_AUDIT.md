# Frozen v0.1 completion audit

This closes the final audit left open at f153406. The denominator is the user's
release-convergence request, not exhaustive BL4 parity or unrestricted production
use. The private integrated prerelease satisfies the nine mandatory deliverables
within the documented, single-build, main-menu-tested boundaries. No additional
runtime changes or repeated live campaign were needed for this audit.

## Requirement-to-evidence dashboard

Percentages below mean completion of the **frozen deliverable**, including its
representative acceptance and documentation. They are not percentages of all
Unreal functionality, code paths, or possible gameplay states tested.

| Frozen deliverable | Weight | Completion | Live evidence | Remaining boundary |
| --- | ---: | ---: | --- | --- |
| Independent runtime, objects, reflection, supported calls | 15% | 100% | `introspection-values-live.json`, `introspection-strings-core-live.json`, `harness-invoke-live.json`; fresh controller inspection | Only supported codecs and fingerprint; observed objects are not automatically GC-pinned |
| Persistent Python console | 10% | 100% | `portable-fresh-sdk.log`, `portable-relaunch-sdk.log`: native commands, Python state, contained exception, new session | Native Python Up/Tab integration unavailable; shipping-disabled engine commands remain disabled |
| Currently supported Harness | 15% | 100% | Earlier invoke/set/POD/enum-value/agent evidence; fresh roots action and `portable-fresh-inspect.json` | Full parity, advanced traces and unsupported types remain deferred |
| Responsive native UMG management | 20% | 100% | Fresh first open 4.9394s, physical navigation/close; relaunch navigation execution 0.4926s | Narrow first-open margin; numeric/text/JSON editors and full BL4 workspace deferred |
| Minimal configurable keys | 15% | 100% | `keybind-existing-process-acceptance.log`, fresh and relaunch logs: physical dispatch, remap, conflict suppression, removal, persistence, native selector | Single supported keys; no chords/controller input; no exhaustive live key matrix |
| Essential console fallback | 5% | 100% | Management console acceptance and integrated load/enable/bind/unbind/unload path | Essential management scope, not every BL4 console screen |
| Mod lifecycle | 10% | 100% | Fresh reload/cleanup, relaunch unload and cooperative stop; normal target exit | Trusted mods share Python; arbitrary third-party compatibility unverified |
| Portable installation | 5% | 100% | Bundled interpreter outside checkout; `integrated-release-verification.json`, equivalence and startup evidence | Windows x64 verified game build only |
| Representative fresh acceptance | 5% | 100% | Game PIDs 6980 and 23204; fresh/relaunch logs and exit status | Main menu only; gameplay/map transitions not certified |

Weighted frozen deliverable completion: sum(weight * completion) / 100 = **100%**.
The previous 91.75% estimate explicitly reserved completion for this audit. This
increase records closure of that gate; it does not represent new engine features
or expanded test coverage. Representative mandatory acceptance: **9/9 checks**.
An overall percentage for unrestricted production readiness or exhaustive live
coverage remains **unknown**, and must not be inferred from this scoped score.

## Cross-checks performed

- Current key service checks session/map generations, validates drained batches,
  contains callback errors and removes mappings on normal close. An authoritative
  target-exit report permits cleanup without another engine query; an uncertain
  transport failure retains ownership. The recorded regression suite passed
  418 tests; this audit did not rerun unchanged tests.
- Current registry implements loading, enable/disable, digest-checked reload,
  unloading, atomic preferences, conflicts and stale-selection rejection. Native
  queue delivery and game-thread engine execution are separate from Python work.
- The preserved BL4 Explorer core and current core have the same SHA256:
  `6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543`.
  The management source inventory records inspection of MattsBL4ModsMenu 1.3.3,
  console_mod_menu, mods_base and input references. Their engine layouts and
  BL4-specific input resets are not treated as Expedition 33 facts.
- Earlier supported-operation evidence includes actual invocation return values,
  owned-object mutation with restored baseline, retained-value cleanup and agent
  actions. Historical evidence contains historical capability labels; the current
  README and adapters define the release support boundary.
- The fresh tested revision was 7624261. Changes through release source 20c8e0e
  are documentation/evidence, two UI wording updates and package-verifier checks;
  no native-runtime or key-service behavior changed. The final candidate had a
  separate existing-game startup check. This is not mislabeled fresh validation.
- The final release has 510 payload files matching that final candidate. The local
  archive hash was independently rechecked in this audit and matches the recorded
  GitHub asset digest. Privacy was verified during publication; the repository
  and prerelease remain required to be private.

## Delivered artifact and remaining work

[Private prerelease](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-integrated.1)
contains `expedition33-0.1.0-private-20261010T003240Z.zip` (24,237,698 bytes).
SHA256: `48eb38b8f6a1fb58179d7bbcd207bd5d2188d2654ae3cc3a79f6890467577cd2`.
Start with `launch.cmd management --keybinds`; open backtick, then `mods ui`.

No unresolved blocker was identified for the frozen private v0.1 deliverable.
Broader production deployment has not been certified. Next-version priorities
are gameplay/map-transition lifetime validation, more menu performance margin,
broader input coverage, additional editors, and expanded Harness codecs/traces.
These remain separate work, not silently completed or new gates for this release.
No precise remaining workload estimate for those unscoped efforts is justified.
