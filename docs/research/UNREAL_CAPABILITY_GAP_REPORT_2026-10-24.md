# ClairObscurSDK Unreal Capability Gap Report

Date: 2026-10-24. Baseline: verified RC18 commit
`aa23eb7296475ea07c60cfc217ca8d23891ed3d5`. Development branch:
`research/unreal-capability-expansion-20261024`.

## Findings that change the development plan

RC18 already has substantially more capability than the early research documents
suggest. Arrays, selected maps, recursive stored structs, typed POD invocation,
retained results, owned audio, sequence adapters, rendering primitives and
observation tracing exist. Reimplementing these would add maintenance without
expanding the SDK. The best immediate opportunities are bounded metadata closure,
reusable facades over admitted primitives, and explicit support diagnostics.

This branch implements those three improvements and strengthens map metadata
identity checks. It also corrects encounter UI descriptions that predated live
acceptance. It does **not** claim the paired Duolliste cinematic is repaired:
historical evidence identifies the exact failure but cannot distinguish hidden
playback from incorrect camera/sequence binding.

## Baseline and evidence quality

The installed `SDK/scripts/run_release_sdk.py --check` returned
`release=0.1.0-rc18`, `mods=3`, `verified=true`. That is the curated release-mod
count, not a count of all optional/personal installed packages. The installed
runtime remains native v213. Source, native build scripts, shipped mod sources,
test fixtures and the RC17/RC18 acceptance documents were inspected. No original
save, settings, installed package, runtime or release asset was changed.

The game was closed during this investigation. There were no live calls, game
launches, travel operations, actor mutations or save operations. Offline tests
establish API/validation behavior; native compilation establishes build
compatibility. Neither establishes fresh live acceptance of a game function.
Historical user results are explicitly historical evidence.

Evidence levels used below:

- **S:** current source and validation-path inspection.
- **F:** deterministic offline fixture/test evidence.
- **H:** earlier documented live acceptance on the verified release lineage.
- **U:** unresolved; no positive feasibility or absence claim.

The older `research/SDK_API.md`, `REFLECTION.md`, `FUNCTION_INVOCATION.md` and
`KNOWN_UNKNOWNS.md` describe earlier stages. They remain historical records;
their negative claims must be checked against current source.

## Categorized capability inventory

“Exposed” means available as a Python API, often opt-in and build-specific. It
never means every reflected signature or arbitrary recipient is admitted.

| Subsystem | Current interfaces and evidence | Classification and frontier |
|---|---|---|
| Objects and identity | `catalog.Catalog`, `capture`, `capture_matching`, `capture_selected`, class/outer closure, `ObjectSnapshot` (S,F) | **Exposed.** Observations do not pin GC objects. Selected identity reads already avoid a full registry scan. No universal stable pointer abstraction is missing. |
| Reflection and inheritance | `reflection.describe`, `enums.describe_enums`, `introspection` (S,F) | **Exposed.** Native metadata includes inherited owner/function/parameter/type information. Exact selected property-type closure was inconvenient; implemented here. Arbitrary recursive schema graph traversal remains **unsupported** without explicit budgets/cycle policy. |
| Scalar/reference properties | `values.read_values_many`, selected/projected reads, `read_object_reference`, `assignment`, `scalar_assignment` (S,F) | **Exposed.** Mutation is explicit and validated; scalar compare-and-set covers bool/int32/float32/float64 with descriptor restrictions. Arbitrary writes, replicated-property edits and raw pointer writes are **unsupported**. |
| Structs | `StoredStruct`, `_pod_values.PROFILES`, typed numeric snapshots (S,F) | **Exposed** copied reflected fields and exact pointer-free invocation profiles: Guid, Vector2D, Vector, LinearColor, Margin, Anchors, Timespan and frame timing structs. Arbitrary native-owned structs are **reflected but unsupported** as generic invocation values. |
| Arrays | `StoredArray` and native copied-value readers (S,F) | **Exposed** bounded copied prefixes with observed full length. Generic allocating array arguments/mutation are **unsupported**; native construction/destruction and element policy are required. |
| Maps and sets | `StoredMap`, `StoredMapEntries`, `_map_value` whitelist (S,F) | **Exposed** nine map key/value combinations, including supported struct/object forms. Generic map combinations and sets are **unsupported**; sparse storage, hashing, occupancy and codecs need independent proofs. This branch validates map type identities previously omitted by the descriptor decoder. |
| Enums, strings and text | `EnumValue`, enum metadata, string/text wire helpers (S,F) | **Exposed** exact supported signatures and bounded copied values. Generic arbitrary enum widths and FName output construction are not implied. Existing native-owned string handling is not a generic native allocation API. |
| Function invocation | `Session.invoke`, retained calls, `InvocationPlanner`, typed Blueprint preparation, native profile policy (S,F) | **Exposed**, with exact signatures/identity/context/native dispatch checks. Discovery alone grants no authority. RPCs, ubergraphs, arbitrary delegate calls and complex owned parameters remain **unsupported** in generic Blueprint calls. |
| Object ownership | scope leases, retained same-call returns, lease policy quotas, stable leases, release batches (S,F,H) | **Exposed** in owned workflows. Borrowed observations and retained values deliberately differ. General ownership transfer of game actors is **unsupported**. |
| World/controller/pawn | `world_admission`, current player context, `world_lifecycle`, `ownership` (S,F,H) | **Exposed** through specific context/retirement workflows. Save flags alone are not gameplay readiness; world/controller/pawn reciprocity and exploration state matter. A universal world mutation context is **unsupported**. |
| Actors and components | procedural mesh, native visual staging, enemy spawning, component pose helpers; fixed engine profiles (S,F,H) | Mixed **exposed** workflows and **internal-only** engine ingredients. General component factories/attachment/registration/lifetime APIs are **discoverable but unvalidated** as reusable services. |
| Bounds and screen/world space | Exact Actor/PlayerController profiles; existing WorldBuilder bounds use (S,F) | Previously **internal ingredients** plus low-level invocation. Added `SpatialQueries` here. No collision, DPI or occlusion proof follows from projection success. |
| Assets and generated Worlds | `assets.load_asset`, `load_generated_world`, asset preparation (S,F,H) | **Exposed** retained loading with canonical names and export checks. Generated World inspection is not activation/streaming. Arbitrary streaming, BeginPlay and actor activation are **unsupported** as generic services. |
| Rendering/materials/lights | 67-row fixed engine profile inventory includes render capture/target/import/export/material/light operations; WorldBuilder preview (S,F) | **Internal-only** primitives plus **exposed** specialized workflows. Reusable owned render/material services need resource retirement, output-path policy and restoration semantics. Not all render functions are native-only or absent. |
| Audio | cinematic audio owners/timelines, media adapters, bounded sound-event diagnostics (S,F,H) | **Exposed** exact owned workflows. Generic audio owner extraction is promising; arbitrary game-owned sound mutation and unrestricted sound-event replay remain **unsupported**. |
| Sequences/cameras | `OwnedLevelSequence`, binding query, exact title/media/original-action adapters, owned arena camera (S,F,H) | **Exposed** owned/exact-profile workflows. Arbitrary sequence rebinding and portable original cinematic relocation are **discoverable but unvalidated**. Binding counts alone prove neither ownership nor correctness. |
| Skeletal animation | enemy metadata, scoped pose helpers, original actor assemblies (S,F) | **Exposed** limited metadata/pose workflows. Generic montage/blend/retarget preview is **unknown/unvalidated**: skeleton compatibility, anim instance and physics/tick restoration need proofs. |
| Physics and collision | exact trace/collision/simulation/bounds/teleport profiles and placement/grounding workflows (S,F,H) | **Internal-only** primitives plus **exposed** specific placement workflows. Generic HitResult invocation codec and arbitrary Chaos state editing are **unsupported**. Clearance samples do not prove camera visibility or future animation envelopes. |
| UI/widgets/input | owned menus, construction/layout batches, button references/actions, keybind capture, reusable process UI, pause/title attachment (S,F,H) | **Exposed** bounded services. Process UI must survive world turnover; gameplay service scopes retire. Native menu ownership/context checks remain required. Unrestricted manipulation of game-owned widgets is **unsupported**. |
| Events/hooks | `tracing`, observation hooks, bounded renew/stop/read with copied identities (S,F) | **Exposed** observation. Arbitrary delegate mutation, function replacement, network RPC and unbounded event interception are **unsupported**; no evidence supports treating discovery as callback ownership. |
| Mod lifecycle/startup | `core_startup`, `mod_lifecycle`, preparation/readiness/timing, process UI routes, map load gate/readiness (S,F,H) | **Exposed** lifecycle services with separate preparation, activation and usability. Protocol diagnostics were scattered in private transport; added public copied snapshot. No startup performance improvement is claimed by this research branch. |
| Encounter/campaign | original roster/direct routes, QA/EnemySpawner, arena/staging, exact action sources (S,F,H) | **Exposed** many verified direct fights; full original presentation remains partially **unvalidated**. Outer campaign actions may autosave/change party. See separate completion report. |
| Navigation/AI/network/save editing | no admitted general-purpose owner/codec found in inspected public source (U) | **Unknown** engine frontier, **currently unsupported** as general SDK APIs. This is not evidence that the game lacks reflected classes/functions. Further targeted discovery is required. |
| Renderer internals/allocator/engine task graph | no generic abstraction established by inspected source (U) | **Unknown/native-only candidates**; cannot label a specific unseen function unreflected. Native engine internals require independent build/thread/lifetime proofs. |

Detailed evidence and unusual lower-priority candidates are retained in
[reflection audit](reflection-capability-audit-20261024.md),
[engine services audit](engine-services-audit-20261024.md), and
[encounter completion report](encounter-completion-20261024.md).

## Implemented capability extensions

### Exact selected schema dependency closure

`reflection.describe_selected(pid, identities)` returns
`ReflectionSnapshot(catalog, descriptors)`. It captures exact root identities and
only missing referenced property types, then reuses the strict ordinary decoder.
There are no registry-wide scans, invocation, name-based substitution, GC pins or
metadata retries. Bounds: 1–1024 roots, batches of 128, at most 1024 additional
referenced types and 16384 combined catalog rows. This is a bounded observation,
not a GC-atomic snapshot and not recursive schema discovery.

The native reader adds `struct_address` and `enum_address` to already validated
top-level metadata. Older readers still support complete-catalog `describe`;
selected closure rejects missing addresses explicitly. Native session ABI and
runtime dispatch code are unchanged. Map key/value struct identity checks are
also applied in ordinary descriptors.

### Typed spatial observations

`SpatialQueries(scope, catalog=catalog)` supplies `actor_bounds`, `viewport_size`,
`project` and `deproject`, with copied `Bounds`/`WorldRay` results. It uses existing
retained planning and exact Engine function paths. Inputs reject invalid numeric
values, false projection ignores undefined outputs, and retained results close
even when decoding fails. Catalogs are explicit; no automatic scan is introduced.
Recreate after travel. Live candidate dispatch remains to be verified.

### Native protocol diagnostics

`Session.capabilities` and `SessionScope.capabilities` return a copied immutable
`CapabilitySnapshot`. `snapshot.protocol('mesh_protocol')` reports `advertised`,
`disabled`, `invalid` or `missing`, with a sanitized version.
`snapshot.matches('mesh_protocol', 3)` compares an explicit exact version;
booleans, negative/oversized values and implicit newer-version compatibility are
rejected. Snapshots contain only public-shaped stored protocol fields, not tokens,
handles, descriptors or arbitrary transport properties.

```python
snapshot = scope.capabilities
entry = snapshot.protocol('runtime_scene_protocol')
print(entry.name, entry.state, entry.version)
```

Obtaining a snapshot checks owner thread, session/scope and parent lifetime.
Retaining the copy after retirement is safe. Advertisements do not prove full
feature prerequisites, current-world admission or permission to call an operation.
Existing `supports_*` helpers and native preflight remain authoritative. This API
is separate from controller RPC `sdk.capabilities`, which lists allowed commands.

## Native safety and lifecycle review

- Only four additive lines change the read-only reader metadata emitter. The
  existing validated reference address is serialized; no new dereference policy,
  native call, write, allocation owner or game-thread operation is added.
- Selected metadata retains exact index/serial/address/type matching. Changed
  identities reject; a newly discovered object with the same name is not adopted.
- Spatial queries delegate to existing retained invocation, same-call result
  leases, native schema/recipient checks and scope ownership. No native errors or
  uncertain outcomes are replayed. Numeric copies own no game resources.
- Protocol diagnostics invoke no native operations and grant no authority.
- Encounter changes describe the actual evidence; they change neither immutable
  source profiles nor native gates. Campaign actions are not executed to obtain
  a convenient preview.
- No original saves/configuration/private mods were read into reports or changed.
  No installation, archive, upload, push or release was performed.

## Regression results

Initial sandbox baseline: 2160 tests, 8 skipped, 9 socket-permission errors
(`WinError 10013` on local loopback). A separate TEMP location fixed the earlier
temporary-directory restriction. With loopback access, the combined suite passed
2181 tests with 8 skipped in 15.236 seconds. The final run, including the added
real-planner integration tests and built invocation fixture, passed **2185 tests
with 6 skipped in 15.482 seconds**, zero failures/errors.

Focused validation: 94 reflection/value/planner tests; 91 encounter/cinematic
tests; 47 spatial/planner/retained/POD tests; 5 protocol diagnostics tests. These
overlap the full suite and must not be summed. Reader compilation and native
enum/POD/schema/metadata fixtures passed. Final full native build and integration
results are recorded in the [companion roadmap/validation document](CAPABILITY_ROADMAP_AND_VALIDATION_2026-10-24.md).

No live acceptance or runtime speedup is claimed. Before integration, validate
selected descriptors against the exact newly built reader and spatial calls in a
disposable session, including travel/closed scope. Original cutscene research
requires copied saves and original arena/binding evidence.

## What became possible

An inspector can request a selected schema and its direct referenced-type closure
without discovering every live object. Mods can use a small typed spatial API
instead of duplicating invocation/decoding, and inspect native protocol versions
without private transport access. Map descriptor decoding now rejects stale map
struct identities. Full original encounter presentation is more accurately
described, but the unverified cinematic has not been relabeled as repaired.
