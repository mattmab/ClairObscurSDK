# Engine services audit — 2026-10-24

Scope: source audit and offline implementation in the isolated capability-expansion checkout. No game state changes, native replacement, installation, publishing, or live dispatch occurred. Existing native support is distinct from an admitted, currently callable operation. Tests below prove the Python facade contract, not live compatibility with every engine context.

## Evidence and categories

| Area | Evidence in current source | Classification and remaining boundary |
|---|---|---|
| Rendering and materials | `native/engine_profiles.h` entries 35–39, 41–46, 48–60; `mods/E33WorldBuilder/catalog_menu.py` preview/catalog UI | Verified-build fixed profiles include material access, scene capture, render-target creation/release/export, texture import, lighting and mesh assignment. These are ingredients used by owned workflows, not permission for arbitrary actors/components. A general render service needs explicit ownership and export-path policies. |
| Spatial queries | Same header entries 24, 25, 32, 40, 64; `mods/E33WorldBuilder/catalog_menu.py:bounds` already uses retained `GetActorBounds` | Bounds and screen/world conversion had reusable transport support but no small dedicated public facade. Added `spatial_queries.py`; no native expansion. |
| Assets | `src/expedition33/assets.py:load_asset`, `load_generated_world`, `_load_asset`; `map_asset_preparation.py` | Existing retained loader requires canonical names and a negotiated protocol. Generated Worlds are inspection-only: exact export/class verification and unchanged player context. Loading is not streaming activation or playback admission. |
| Audio | `cinematics/owned_audio_timeline.py:OwnedAudioTimelineDispatcher.prepare`; `_music_audio_owner.py:NativeMusicAudioOwner`; `cinematics/media_audio_adapter.py:MediaAudioAdapter` | Owned audio component creation and acknowledged play/stop/volume timelines already exist. Preflight resolves exact sounds and component functions before allocation. Generic world audio, attenuation overrides, cross-world reuse, and arbitrary sound-event replay need separate ownership/context contracts. |
| Sequences and animation | `sequences.py:OwnedLevelSequence.build`; `_sequence_binding_query.py`; `_owned_component_pose.py`; `enemy_metadata.py` | Sequence ownership and specific pose workflows exist. Binding counters are observations, not proof of safe bindings. Enemy metadata explicitly does not establish animation playback or skeleton compatibility. No evidence here supports a general skeletal montage/blend/retarget API. |
| Physics | Header entries 14–15, 47, 59, 63–66; `enemy_spawning.py` clearance inspection; `owned_battle_arena.py` | Trace/bounds/collision/simulation/teleport primitives are present in exact workflows. A sampled clearance volume does not prove all channels, future animation envelopes, navigation or Chaos safety. Physics enablement should remain owned and restoration-aware. |
| Components | Header entries 16–20, 35–39, 46, 59–60; `_owned_component_pose.py` | Owner/root/component transforms and material/mesh primitives exist. Existing pose operation is one-shot, tied to an inert owned helper and preserves scale; it is not general component lifecycle authority. Attach/create/register/destroy deserves a dedicated owner rather than generic reflection sugar. |
| Events | `tracing.py:prepare_trace`, `ObservedObject`; `_traces.py:start`, lease read/renew/stop/close | Bounded observation-only tracing already exists with native identity/schema validation. Event-time object copies are not retained references. Arbitrary delegate injection, callback replacement, RPC, or unbounded trace capture is not established. |
| Generic invocation | `invocation.py:prepare`, `_parameter_schema`; `_pod_values.py:PROFILES`; `prepared_invocation.py:InvocationPlanner`; `_scope.py:SessionScope.invocation_planner` | Same-call retained outcomes and exact supported POD codecs provide a useful base. Unsupported owned containers and arbitrary reflected functions do not become safe just because their names are discovered. Explicit catalogs avoid registry scans. Metadata cache bounds and native revalidation remain intact. |

The 67 rows in `native/engine_profiles.h` are an exact-build profile inventory, not 67 generic public services. `native/validated_engine_profile_call.h` and `native/engine_profile_invocation_policy.h` enforce contextual validation on their users. Historical `research/KNOWN_UNKNOWNS.md` predates current POD/retained invocation and must not be used as a current capability matrix.

## Implemented extension

`from expedition33.spatial_queries import SpatialQueries, Bounds, WorldRay`

Construct `SpatialQueries(scope, catalog=catalog)` with an explicit catalog containing the target observations and reflected function/type dependency closure. It does not capture the full registry. The scope-bound retained planner supplies the existing validation and outcome behavior. Unsupported runtime capabilities fail through the existing planner; the facade does not enable experimental flags or bypass native admission.

* `actor_bounds(actor, only_colliding=False, include_children=True)` copies world-space origin and half-extents.
* `viewport_size(controller)` returns nonnegative integer width/height.
* `project(controller, world_position, viewport_relative=False)` returns a copied pixel pair or `None` when Unreal reports failure. Projection success is not visibility or occlusion evidence.
* `deproject(controller, screen_position)` returns a copied world ray or `None`. It performs no trace.

Every call closes its retained result even when output validation fails. Results contain only immutable Python number tuples. Inputs reject booleans masquerading as numbers, nonfinite coordinates and invalid dimensions. Failed projection does not read unspecified output storage. Native errors propagate without retry. Closing releases planning metadata, not caller-owned actors. Recreate with a current catalog after world travel; observations do not pin targets.

Epic's [APlayerController::DeprojectScreenPositionToWorld documentation](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/APlayerController/DeprojectScreenPositionToWorld) supports the general ray/false-result semantics. It does not prove the shipping game's signature or dispatch permission; the target profiles and runtime validator provide those checks. No code was copied from external SDKs.

## Prioritized roadmap

Scores are 1–5; high value/confidence is favorable, high effort/risk is costly. Estimates reflect this source audit, not benchmarked implementation durations.

| Candidate | Value | Evidence confidence | Effort | Risk | Next proof required |
|---|---:|---:|---:|---:|---|
| Spatial query facade (implemented, offline) | 4 | 4 | 1 | 1 | Live scoped calls on the verified candidate, including travel invalidation and split-screen/DPI behavior |
| Bounded public component discovery and read-only bounds/material snapshots | 5 | 4 | 2 | 2 | Selected dependency closure, exact component owner and material result retention; avoid full scans |
| Owned render capture service extracted from WorldBuilder preview | 4 | 4 | 3 | 3 | Resource allocation/release acknowledgement, filesystem export policy, failure cleanup, world transition tests |
| General reusable audio owner extracted from cinematic code | 4 | 4 | 3 | 3 | Exact sound admission, stop/destroy completion, travel retirement, no borrowed gameplay audio mutation |
| Scoped physics query facade | 5 | 3 | 3 | 3 | HitResult codec/native-owned output constraints, collision-channel semantics, trace recipient/world checks |
| Owned light/material editor adapters | 4 | 4 | 3 | 3 | Before/after restoration and ownership loss, material resource lease, save/travel behavior |
| General actor component factory | 4 | 2 | 4 | 4 | Registration/outer/attachment/GC and destroy ordering, no arbitrary component class admission |
| Skeletal animation preview owner | 5 | 2 | 5 | 5 | Skeleton compatibility, anim instance/physics interaction, original tick restoration, isolated actor preview |
| Broad delegate/event mutation API | 2 | 1 | 5 | 5 | Callable lifetime and engine-owned delegate construction/destruction; observation trace already covers many needs |

## Validation

Seven focused offline tests in `tests/test_spatial_queries.py` passed under the installed embedded Python: exact function paths and arguments, explicit-catalog/no-scan construction, copied outputs, failed projection, invalid-input rejection, output failure lease cleanup, context close and native error propagation. Existing planner/retained tests remain the integration boundary; no live success or performance claim is made by this change.

Additional validation uses `tests/test_spatial_query_planning.py`: a real `Catalog`, `Session`, `SessionScope`, `InvocationPlanner`, `prepare_call`, wire encoder, retained acknowledgement decoder and POD decoder, with only the external descriptor reader and transport replaced by fixtures. It checks all four actual shipping layouts below, closed-query and retired-scope rejection before transport, absent POD capability rejection, and no full catalog capture. The native `invocation_fixture.exe` was compiled locally with `/W4 /WX` and accepts the resulting four ordinary packet prefixes through `validate_call_packet(..., true)`. This fixture validates packet shapes, not real UObject identities, game-thread context or game execution. The focused suite plus retained/planner/POD regressions totals 47 passing tests with no skips.

| Operation | Params / extent / return offset | Function flags | Entry RVA | Output layout |
|---|---|---|---|---|
| GetActorBounds | 57 / 64 / 65535 | 0x54c20402 | 0x33398d0 | Origin Vector at 8, BoxExtent Vector at 32 |
| ProjectWorldLocationToScreen | 42 / 48 / 41 | 0x54c20403 | 0x3b27f10 | ScreenLocation Vector2D at 24, bool at 41 |
| GetViewportSize | 8 / 8 / 65535 | 0x54420403 | 0x3b26b70 | SizeX int32 at 0, SizeY int32 at 4 |
| DeprojectScreenPositionToWorld | 57 / 64 / 56 | 0x54c20403 | 0x3b23d30 | WorldLocation Vector at 8, WorldDirection Vector at 32, bool at 56 |

All four flags contain native bit 0x400. `native/reflected_invocation.h` accepts ordinary native functions after target/owner/current function metadata and dispatch-entry checks; it does not require Blueprint admission for these calls. `native/pod_schema.h` verifies CoreUObject.Vector as three doubles (24 bytes), Vector2D as two doubles (16 bytes); `native/invocation_protocol.h` admits `CallVector` in POD packets. Python `_pod_values.py` and `invocation.py` encode/decode those exact shapes. The required Python runtime selection is retained invocation plus negotiated POD support (`Session(pod_values=True)` supplies this chain); viewport size needs retained support alone. The facade does not require or enable Blueprint, asset, sequence, mutation, or arbitrary-struct flags. This establishes source-supported dispatchability when the native validator admits the live target/context, rather than claiming live execution was observed.
