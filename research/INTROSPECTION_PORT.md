# BL4 Introspection Harness port

Status: source audit complete; first catalog primitive validated. No Expedition 33
harness parity is claimed yet. Updated 2026-10-08.

## Original and provenance

Actual source: `S:/SteamLibrary/steamapps/common/Borderlands 4/sdk_mods/tools/introspection/package/BL4Introspection`.
Metadata and entry point identify version 1.3.0. The README's 1.1 heading is older
than the retained-result and agent additions. Preserved source, clients, tests,
documentation and installed/staged archives live under
`D:/HobbyDevelopment/Analysis/ClairObscurSDK/bl4-introspection-original-20261008`.
Local `evidence/introspection-source-manifest.json` records SHA256 for 23 files.
Original MIT copyright/license must accompany copied code.

Installed archive SHA256: `9ae0c08d9f2592df00cf109be94557524095608a1d44785fa22132d55aec45e2`.
Staged archive SHA256: `c6d6cabf0af6e17ebab7b89dd60f53cdc5c9be46729cbe771bee88094520d46e`.
Core and entry-point source match both archives. Source/staged agent.py adds a
bounded-output fix: stop appending empty strings after output capacity is reached.
That is the sole Python difference from the installed archive. Use source/staged
1.3.0 as the port baseline, preserving that fix.

## Architecture and complete feature inventory

| Component/capability | Original behavior | Expedition 33 requirement/status |
| --- | --- | --- |
| Explorer core | SDK-injected class; reflection, serialization, operations and lifetime stores | Preserve algorithms behind an adapter; not a replacement tool |
| status | SDK version, operation names, argument types, retained names, trace state | Add explicit backend capability limits; do not advertise absent primitives as working |
| roots | Up to 32 non-CDO World, GameInstance, LocalPlayer, PlayerController, Pawn objects | Inheritance-aware enumeration needed; native-name equality misses Blueprint instances |
| search | Class/subclass filter, path substring, offset/scan/limit, live pagination | Complete ownership paths and inheritance query needed |
| schema | Class or ScriptStruct, inherited properties/functions, parent list, parameter flags/directions, offsets, referenced struct/enum/object/container/delegate types | Current native-class properties and named function metadata are partial; bulk functions, generated classes, structs and reference descriptors needed |
| inspect | Re-resolve exact path/class; optional members; bounded reflected values; per-field errors | Identity-aware resolution and general stored-value reads needed; bool-only reads do not establish parity |
| snapshot/diff | 32 named inspection pages; changed/added/removed fields with presence flags | Preserve core logic and original page semantics |
| encode | Primitives, nonfinite floats, object refs, bounded structs/arrays/dicts, opaque summaries | Build verified SDK value wrappers; 64 elements, depth and shared node budgets preserved |
| decode | JSON primitives/arrays, $object, $struct, $value, $gamedata, $gbxdef | Reusable conversion and lifetime handling needed; Gearbox types are game-specific, not presumed present |
| set | Exact reflected property, explicit literal allow_mutation:true, before/after values | Verified game-thread property writes with type/lifetime validation needed |
| invoke | Reflected member lookup and named argument conversion; bounded result depth | General dispatch/marshalling needed; fixed Actor getter is only current proven specimen |
| retained results | Up to 16 named original SDK values, indexed $value paths, 60-second TTL, explicit release | Preserve allocation ownership and reject stale world/session references; snapshots are not native-owned values |
| traces | Exact reflected function POST observation, optional target, 16 slots, 300 seconds/1000 events maximum; copy args/result, stop/forget/cap/expiry | Reusable reflected event observation needed; current fixed getter hook is a limited starting point |
| agent registry | 128 named callbacks with owner, description, small argument schema, mutating default, duplicate rejection/unregister | Preserve ownership, schema and cleanup; callbacks execute on external Python owner thread, engine work routed to game thread |
| action aliases | action/call_debug_action/run_test_action; kart_* aliases | General action aliases portable; Kart aliases depend on a future port of that mod |
| dev_status | Adapters/actions/last diagnostics, raw exec disabled | Keep file protocol free of raw Python endpoints; existing trusted in-game py console remains separate |
| mod_list | Up to 128 mod names/enabled/version | Extend current loader integration; do not import mods_base |
| mod_enable/disable/reload/reload_changed_mod | Literal mutation gate; audited adapter only; staged digest check; cleanup before replacement; no retry after unknown outcome | Reusable loader lifecycle adapter needed; BL4 loaders cannot be run against Expedition 33 |
| audited adapters | Agent source contains BL4Kart only | Companion CLI offers ArcadeClassics/Platformer/CitizenScience too, but source bridge does not implement them; inventory discrepancy, not parity to invent |
| logs | Up to 100 matching lines from 32-KiB tail, bounded per-line text | Adapt to SDK log destination, preserving bounds |
| diagnostics | Outer ok plus inner success; elapsed/over-budget, 16-KiB stdout/stderr, 8-KiB traceback, plain JSON result <=128 KiB | Preserve and contain Python BaseException consistently with existing SDK |
| file protocol | UUID/session/expiry, atomic request publish/claim, .processing unknown outcomes, no sockets, one request/100 ms | Preserve protocol; external controller services it without copying the BL4 camera tick hook |
| heartbeat | Session renewal, enabled/PID/time, <=5-second freshness | Report target and controller separately; no heartbeat claim of game-thread execution |
| protocol bounds | Request 64 KiB, response 256 KiB; matching response identity; no mutation retries | Preserve; test malformed, stale, expired and oversized requests |
| lifecycle | Disable removes pump/traces, clears snapshots/results/actions; core reload renews session | Integrate with SDK mod unload, controller death, normal exit/relaunch |
| console | bl4i_status and SDK py/pyexec development workflow | Native E33 console command registration plus persistent Python API access |
| clients | stdlib bl4_introspect.py send/CLI (status/request/roots/search/schema); bl4_agent.py actions/reload/logs | Port clients and naming while preserving request/response shapes |
| packaging | Deterministic .sdkmod ZIP, AST validation, MIT license/docs | Use current independent SDK packaging; no BL4 mod-manager dependency |
| developer tools | reload_core/install_agent_bridge; historical debugpy hotfix client | Preserve safe reload capability through current architecture; debugpy socket/bootstrap mechanisms are not runtime harness dependencies |

The core depends on PyUnrealSDK object/class/function/property wrappers,
find_all/find_object/find_class/make_struct, POST hooks and logging. Entry point
depends on mods_base registration and CameraModifier:BlueprintModifyCamera POST.
Agent additionally depends on mods_base.get_pc/GetLevel, mod list, BL4Kart's fixed
loader and the OakGame log location. No ImGui, Jupyter or Live Object Viewer is
required. GameDataHandle and FGbxDefPtr are Gearbox-specific APIs. Construction of
a named handle never proves a loaded definition exists.

## Existing SDK audit and implementation sequence

Current v0.1 live evidence covers enumeration, native class/property metadata,
nested type names, stored booleans, fixed Default__Actor invocation/observation,
console transport and a single enabled mod. It does not prove arbitrary reads,
writes, generated-class reflection, function marshalling or general event hooks.

1. Build/prove reusable ownership and inheritance catalog, identity lookup and
   exact path semantics; then class/function/struct metadata without name ambiguity.
2. Preserve original Explorer and serializers through an SDK adapter. Validate
   roots/search/schema/inspect/snapshot/diff against live game, extending readers
   for scalar/object/name/string/struct/container types from target evidence.
3. Port file service, clients, action registry and console integration with bounded
   owner-thread polling and deterministic unload/reload/session cleanup.
4. Extend game-thread invocation, typed values, safe writes and general POST
   observation as independent SDK primitives, then integrate and validate traces,
   invoke/set and retained results. Do not claim arbitrary support from one call.
5. Validate normal exit/relaunch, mod reload, stale references/requests and errors;
   package the harness and publish the feature comparison with measured limits.

Original tests model fake SDK objects. Original runtime notes report BL4 camera
trace delivery, controller inspection/snapshots, and Kart action/reload smoke.
Neither establishes Expedition 33 behavior. New live evidence must name the
fingerprinted E33 process/build and each tested capability.

Priorities for later ecosystem ports follow these dependencies: general reflection
and safe value access; typed invocation; object lifetime and world-change detection;
general event observation; shared-session multi-mod ownership; only then game-
specific actor spawning, transforms, input, HUD/UI and custom gameplay adapters.

## First reusable primitive: ownership/inheritance catalog

PROVEN in PID 34604, supported Steam build 23765773: the new read-only native
`--catalog` query returned 96,053 objects and 6,453 class descriptors. Python
`expedition33.catalog.capture()` validates registered class/outer identities,
bounded superclass chains and ambiguity; `select('PlayerController')` includes
the live BP_jRPG_Controller_MainMenu_C instance. Its observed inheritance is
PlayerController -> Controller -> Actor -> Object. World, custom GameInstance
and LocalPlayer ownership chains are also recorded; no Pawn instance was present
at the main menu. Capture took approximately 2.6 seconds on this run.

The first strict size check rejected Default__Class (index 28155, size zero).
Metaclass default descriptors are now recorded with their observed size, not
treated as usable object storage. The Class metatype anchor requires both the
observed name and self-class identity; a same-named game class cannot activate it.
Ownership chains are returned as identities/names, without inventing Unreal path
punctuation. Path formatting and generated-class property access remain next work.

Validation: all 25 current Python tests passed, including five new identity/graph
regressions. `scripts/verify_live_catalog.py` reproduces live evidence in
`evidence/introspection-catalog-live.json`. Catalogs are external observations,
not GC-atomic snapshots or owning references; native operations must still
revalidate before access. No engine writes or new injected hooks were introduced.
