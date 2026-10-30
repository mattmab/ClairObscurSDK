# Prioritized capability expansion roadmap and integration record

Companion to [the capability gap report](UNREAL_CAPABILITY_GAP_REPORT_2026-10-24.md).
All estimates are engineering judgments based on current code, not promises of
live compatibility or implementation duration.

## Consistent scoring

Each dimension is scored 1–5, with **higher always more favorable**:

- U: usefulness to existing mods.
- N: potential to unlock new mod categories.
- G: general applicability.
- F: technical feasibility with current evidence.
- S: native safety (5 means no new mutation/ownership risk).
- L: lifecycle compatibility.
- P: low performance cost.
- M: low maintenance burden.
- B: breadth of additional functionality enabled.

Total is the unweighted sum, maximum 45. Evidence quality remains a separate
decision gate: a high benefit score cannot authorize an unproved native operation.
Completed items stay in the inventory to explain the selection. Component work
ranks above some completed small items, but needs additional ownership/schema
proof; the completed items could be independently verified offline now.

| Priority/candidate | U | N | G | F | S | L | P | M | B | /45 | State / decisive next proof |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Selected schema/type closure | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 43 | Implemented; live selected metadata acceptance outstanding |
| Protocol advertisement diagnostics | 4 | 2 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 40 | Implemented; does not replace operation prerequisites |
| Spatial query facade | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 4 | 4 | 40 | Implemented; exact wire/native packet fixtures pass, live check outstanding |
| Component discovery/read-only snapshots | 5 | 4 | 5 | 4 | 4 | 4 | 4 | 4 | 5 | 39 | Next foundational target: explicit selected component/owner closure and retained material results |
| Map struct metadata validation | 4 | 1 | 5 | 5 | 5 | 5 | 5 | 5 | 3 | 38 | Implemented identity-check omission fix |
| Copied map combination expansion | 4 | 4 | 5 | 3 | 4 | 4 | 4 | 3 | 4 | 35 | Native value/schema fixtures for each new pair, not Python whitelist edits alone |
| Owned render capture service | 4 | 5 | 4 | 4 | 3 | 3 | 3 | 3 | 5 | 34 | Extract existing preview ingredients; prove allocation/export/release/retirement |
| Reusable owned audio service | 4 | 4 | 4 | 4 | 3 | 3 | 4 | 3 | 4 | 33 | Extract cinematic owner with admission, acknowledgement and travel tests |
| Copied set reader | 3 | 4 | 4 | 3 | 3 | 4 | 4 | 3 | 4 | 32 | Exact sparse-set storage/occupancy/hashing and adversarial bounds fixtures |
| Scoped physics query facade | 5 | 5 | 5 | 3 | 2 | 3 | 3 | 2 | 4 | 32 | HitResult construction/output codecs, collision channel/world semantics |
| Owned light/material editor | 4 | 4 | 4 | 4 | 3 | 3 | 3 | 3 | 4 | 32 | Retained resources and restoration after ownership loss/travel |
| Recursive schema graph explorer | 3 | 3 | 4 | 3 | 4 | 4 | 3 | 3 | 4 | 31 | Depth/query/byte budgets and cycle/partial-result policy |
| General component factory | 4 | 4 | 4 | 2 | 2 | 2 | 3 | 2 | 4 | 27 | Outer/registration/attachment/GC/destroy acknowledgement contract |
| Skeletal animation preview owner | 4 | 5 | 4 | 2 | 1 | 2 | 2 | 2 | 4 | 26 | Skeleton/anim-instance/physics/tick compatibility on isolated preview actor |
| Pair cinematic/portable original presentation | 5 | 3 | 2 | 2 | 2 | 2 | 3 | 2 | 3 | 24 | Exact original binding/camera/completion graph at original location |
| Arbitrary container writes | 4 | 4 | 5 | 1 | 1 | 1 | 2 | 1 | 5 | 24 | Native allocation/destruction/hash/exception safety; defer |
| Broad delegate mutation | 2 | 4 | 4 | 1 | 1 | 1 | 2 | 1 | 4 | 20 | Engine-owned callable lifetime and dispatch threading; defer |

The pair has explicit user value despite lower generality. It should receive a
targeted original-arena observation session alongside foundational work. It is
not an excuse to weaken ownership or substitute a different cinematic.

## Concrete next investigations

1. Component snapshot: start from an exact observed actor/root identity, select
   bounded attached component identities and their owner reciprocity. Reuse the
   new schema closure and existing copied-value reader. Return copied metadata,
   never accidental ownership; test stale/duplicate/foreign-world components.
2. Render capture: isolate WorldBuilder's admitted preview path into a resource
   owner. Define render-target allocation limits, canonical output locations,
   export completion, shutdown and travel retirement before making it public.
3. Pair cinematic: preserve a disposable save/config set, observe the exact
   original CleasTower sequence and binding graph, identify camera/streaming
   dependencies and compare phase transition with the existing portable fight.
   No outer autosaving campaign action on an original save.
4. Simon route: decode original ordering and completion/abort callbacks between
   the two already working direct battle selectors. A timer is not a cinematic
   handoff. Keep direct combat and full presentation acceptance distinct.
5. Physics: determine the narrowest useful read-only query and exact HitResult
   codec. Do not broaden actor mutation merely to expose a trace convenience API.

## Integration and validation record

Development changes are isolated from the installed RC18. The only native source
change adds two JSON fields in the read-only metadata emitter. No runtime DLL
dispatch implementation, profile allowlist, handshake version, source-capture
hash, save/config file or installation script is changed.

Validation completed before final commit:

- Initial existing suite: 2160 tests, 8 skips; 9 local-loopback permission errors
  in sandbox. These were environmental, not source assertions.
- Combined suite with loopback access: 2181 tests, 8 skips, all passing in 15.236s
  before the additional spatial planning tests. Final result follows below.
- **Final combined suite: 2185 tests, 6 skipped, zero failures/errors in 15.482s.**
  Native invocation fixtures built during this investigation enabled two
  previously skipped tests. The six remaining skips are five optional native
  button/menu/text fixture checks and the installed-game manifest check; these
  artifacts are absent from this isolated source checkout.
- Reflection/value/enum/planner focused suite: 94 passing.
- Encounter/cinematic/lifecycle focused suite: 91 passing.
- Spatial real-planner/POD/retained/native-packet suite: 47 passing, no skips.
- Capability snapshot suite: 5 passing.
- Standalone read-only reader compiled successfully with MSVC `/W4`.
- Enum schema, POD schema and metadata-stabilization native fixtures compiled
  `/W4 /WX` and passed.
- Four spatial packets passed the existing native invocation packet validator
  with POD admission. This validates packet structure, not live game identity.
- Full `build-early-lifecycle-runtime.cmd`: all 15 regression fixture programs
  passed; native v213 DLL and full-feature reader compiled with `/W4 /WX`.
  Outputs remain in this worktree's ignored build directory; nothing installed.
- `git diff --check` passed.

The full native fixture list is lease release batch, builder retirement, retired
world, menu open pipeline, keybind, stable identity, stable lease, menu focus
controls, metadata stabilization, console colors layout/adapter/callback, console
spawn resolution, map runtime readiness and string call. The string fixture also
passed 10,000 bounded-frame cycles, rejection, scrub and unknown quarantine.

Skipped tests are explicit existing optional artifact/platform requirements;
final results must be reported with skips rather than described as live coverage.
No runtime speedup measurement or new live functionality acceptance occurred.

## Review and release boundary

Review the public APIs, native additive metadata and reports on the development
branch first. A later authorized integration session can install the new reader
and Python modules into a disposable setup, exercise current-world identities,
travel invalidation and closed scopes, then decide release version/packaging.
This session creates no release archive and performs no push or publication.
Private/personal installed artifacts remain outside all source inputs.
