# BL4 Introspection Harness port

## Companion CLI — 2026-10-09

scripts/e33_agent.py ports the original bl4_agent.py command shapes for status,
mods, action NAME --args JSON, enable MOD, disable MOD and logs. Global options
include --allow-mutation, --data and --timeout. It uses the existing isolated
local-file client with no mutation retry. Exit status is zero only when both the
outer protocol ok and inner bridge success are true. Invalid local JSON arguments
are rejected before sending. BL4-specific choices and staged reload commands are
not exposed without an Expedition 33 lifecycle adapter.

LIVE PROVEN on game21568/controller31152: CLI status, example enable, the real
game-thread Actor getter action, disable and stale action rejection all passed.
The stale request returned outer ok=true, inner success=false and CLI exit1.
Evidence: evidence/agent-cli-{status,enable,action,disable,stale}.json.
All306 Python tests pass, including request shapes, both failure layers, local
argument validation and one-send-only timeout behavior. Packaging now includes
v17 runtime/controller binaries and verifies isolated launcher/client help;
candidate validation is separate from fresh-game package validation.

Example from the repository using the configured Python executable:

```text
python -I -S -B scripts/e33_agent.py status
python -I -S -B scripts/e33_agent.py --allow-mutation enable ManagementExample
python -I -S -B scripts/e33_agent.py action example.observe_actor
python -I -S -B scripts/e33_agent.py --allow-mutation disable ManagementExample
```

Load ManagementExample first with `mods load ManagementExample` in the native
console. Action failures include diagnostics in the JSON result, not just an
exit status. A timeout does not prove that a claimed mutation did not execute.

## Original action bridge port — 2026-10-09

The original agent.py's named-action registry, request aliases, small argument
schema checks and diagnostic envelope now run behind Harness.request and the
existing local-file protocol. This is an adaptation of Mattmab's MIT source;
the original Explorer core remains unchanged. Implemented operations are
dev_status, mod_list, mod_enable, mod_disable, action, call_debug_action,
run_test_action and logs. Only loaded mods can be enabled/disabled, using the
same Registry and ModLoader as the native/console frontends. The servicing core
mods cannot be disabled through their own requests. Lifecycle changes and
mutating actions require literal allow_mutation:true.

Enabled mods register through session.actions.register(name, callback,
description=..., schema=..., mutates=True). The loader supplies the owner;
session.actions.unregister(name) removes an individual registration. Scope close
revokes registrations even when disable raises. Tokens prevent a stale removal
from deleting a replacement. There are at most128 actions; duplicate names are
rejected. No module scan or implicit execution of register_agent_actions occurs.
Callbacks run on the external Python owner thread; their SDK engine operations
still use verified game-thread dispatch. Arguments/results are copied JSON,
with no returned UObject/native-wrapper retention. No raw Python file endpoint
or request-supplied log/loader path is provided.

The original outer protocol ok and inner action success remain separate.
Diagnostics include elapsed_ms, over_budget (above2000ms), bounded stdout/stderr,
and error type/message/traceback. Output capture now bounds UTF-8 bytes to16KiB
per stream before its truncation marker. Result JSON remains limited to128KiB
and depth12. BaseException, including SystemExit, is contained; no automatic
mutation retry occurs. Log reads use the configured bundle's logs/sdk.log,
at most32KiB from its tail,100 lines and2000 characters per line. Long actions
can still block controller polling; over_budget reports this, not cancellation.

LIVE PROVEN using scripts/verify_live_agent_bridge.py on game21568 and source
controller31152/session97e3d5e8ed2a4d98b945d1a02bfc414e: all three action aliases
called example.observe_actor, which uses the existing verified game-thread Actor
getter. Missing consent and unknown arguments were rejected. Disabling the real
ManagementExample removed its action; stale dispatch failed; re-enabling created
a working new registration; final disable succeeded. Mod listing and bounded log
retrieval also passed through the local-file protocol. Raw request/response
evidence: evidence/agent-bridge-live.json; controller log: logs/agent-bridge-host.log.

Unit coverage includes output/result limits, foreign-thread and nested dispatch,
schema-copy isolation, registry cap, stale removal, disable failure, original
aliases, consent, Harness routing and original core provenance. Source-only;
packaged release and fresh-game relaunch validation are pending. Staged digest
reload, companion agent CLI, world/travel expiry, general traces and BL4-specific
Kart/GameData adapters remain incomplete or game-specific and are not advertised
as supported. The independent menu/keybind/editor work also remains unfinished.

Example after loading and enabling ManagementExample in the console:

```python
py introspection.request({'op': 'action', 'name': 'example.observe_actor'})
```

Mod registration example inside enable(session):

```python
session.actions.register('my_mod.status', self.status, mutates=False)
```

Return plain JSON from self.status. The mod's scope owns cleanup; explicit
unregister is optional for normal disable and useful when replacing one action.

## Enum schema follow-up — 2026-10-09

The existing original `schema` request now includes copied enum members under
referenced `Enum` metadata, including nested array element enum references.
The adapter uses the independent reader in REFLECTION.md; the original core is
unchanged (normalized SHA256 remains
`6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543`).
Each enum includes `members`, `member_count` and `members_truncated`. Expansion
is bounded to128 entries; failures report `members_error` while preserving the
existing type reference. Duplicate references share only a request-local cache,
which is cleared on refresh, request completion and shutdown. Returned lists
are independent copies. Sentinel names remain visible, without invocation rights.

Read-only live proof on game21804: original `schema` for
`/Script/UMG.WidgetBlueprintLibrary:SetInputMode_GameAndUIEx` returned all five
EMouseLockMode entries, the verified byte underlying type, and current parameter
offsets. The request cache was empty afterward. Reproduce with
`scripts/verify_live_harness_enums.py`; raw evidence is
`evidence/harness-enum-live.json`. All179 source Python tests pass, including
bounded expansion, copy isolation, error metadata and preserved core provenance.
This is source-only; the running v12 package is unchanged. Enum arguments,
enum-valued property reads/writes and complete Harness parity remain pending.

Status: original roots/search/schema, selected stored-value inspection, snapshots
and diffs are live-validated; the local-file protocol is ported. Bounded native
invocation and explicit object leases are available. v8 integrates original
retained-value semantics; see the current ownership checkpoint below and
OBJECT_LEASES.md for validation. Full Expedition 33 Harness parity remains
incomplete. Updated 2026-10-09. Earlier dated sections describe prior boundaries.

## v12 copied text invocation — 2026-10-09

The existing primitive argument/result adaptation now carries Python strings
through scalar TextProperty invocation when the shared session enables
text_values. The preserved original core required no edits. Live validation on
an SDK-created TextBlock passed ASCII, Unicode and empty text, plus original
named retained-value reuse/release and rejection after release. Values retained
by the Harness are copied Python strings, not native localized FText handles.
Object outputs retain their existing native lease behavior.

Public use requires `Session(text_values=True)` and `invoke_retained`, or the
management launcher with `--text-values`. Plain invoke and direct TextProperty
writes remain unsupported. Arrays and arbitrary text-data/history types are not
enabled. All173 source tests pass, including the unchanged core's provenance.
See WIDGET_LAYOUT_VALUES.md for live identities, raw evidence and exact cleanup.

## v11 original typed struct integration — 2026-10-09

The adapter now supplies `make_struct` and WrappedStruct-compatible copied
results for Vector2D, LinearColor, Margin and Anchors. The original decoder,
encoder, invocation consent gate, retained `$value` lookup, 16-name limit,
60-second expiry and release operations remain unchanged. Status exposes
`$struct` only with v11 and lists the exact four full paths in `struct_types`.
Short names and those exact full paths are accepted; every field is required.
Nested values use nested `$struct` objects. This constructs Python numeric
copies, not arbitrary native values; the invocation gates still verify current
metadata and the game-thread schema before dispatch.

Example argument in an original `invoke` request with `allow_mutation:true`:

```json
{"InPosition":{"$struct":"/Script/CoreUObject.Vector2D","fields":{"X":144.25,"Y":72.5}}}
```

GetPosition returns `{"$struct":"Vector2D","fields":{"X":144.25,"Y":72.5}}`.
An invocation with `"retain":"position"` can supply a later argument as
`{"$value":{"name":"position"}}`, using the original retained-value machinery.
No native holder is needed for numeric copies. Object outputs retain their
existing native lease behavior. Unsupported owned/opaque structs (FKey, FText,
font state, game-data handles and arbitrary reflected structures) remain gated.

All 156 source tests pass, including nested original decode/encode, input copy
isolation, typed results/out parameters, retained reuse/expiry and capability
reporting. The original core's normalized SHA256 remains
`6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543`.
Live adapter validation passed at 03:50:34 local on game PID 25560, persistent
Python PID 28004/native controller PID 39856. Original `$struct` SetPosition
returned, GetPosition encoded `{X:144.25,Y:72.5}` as a typed Vector2D, and retained
`$value` restored that position after a second setter changed it. The post-reuse
getter matched. After release, reuse raised KeyError without dispatch; an FKey
construction request was rejected before dispatch. Nested Anchors dispatch
returned. The SDK-owned child was removed and the exact native holder baseline
restored. No viewport, focus or menu visibility behavior was exercised.

Evidence: `evidence/harness-pod-live.json`,
`logs/management-v11-harness.stderr.log`, `evidence/harness-pod-python-tests.log`.
The preceding host was closed through its existing management action before
loading the updated adapter. The native v11 DLL was reused, not rebuilt while
loaded. That source host subsequently exited normally with the game.

Packaging/relaunch follow-up at04:05:10: isolated candidate20261009T075928Z,
source3981117, loaded its own v11 DLL into fresh Steam-launched game12912.
Python36508/native35688 ran the packaged original-Harness specimen successfully:
typed values, retained reuse/release, rejection checks and exact holder cleanup
all passed again. The console confirmed the SDK import path inside the bundle.
The new persistent package host remains running. See DEVELOPMENT.md and
`evidence/visible-v11-package-harness-live.json` for the package/lifecycle record.

## v10 original set integration — 2026-10-09

The preserved Explorer core now reaches the reusable `assign_object` primitive
through the adapter's reflected-property lookup and object setter. Scalar
ObjectProperty writes require the original literal `allow_mutation:true`; the
adapter checks unique property declaration/type, supplies the observed old value
to the native compare-before-write check, and invalidates observations before
the core reads its after-value. Backend status reports `write_types` explicitly.
Other types, fixed-array writes through Harness, and custom accessors are not
advertised as supported. Root/session SDK assignment retains its separate
fixed-array element API. Original core SHA256 remains
6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543.

All138 Python tests pass, including original before/after/null restoration,
mutation opt-in rejection, unsupported type rejection, no retry after native
rejection, authorization cleanup and completed-dispatch reporting when the
post-write catalog fails. These tests alone do not prove engine behavior.

Live `scripts/verify_live_harness_set.py` passed at02:49:03 through native console
Python on game34604 and existing host21172/controller36320. A separate Harness
instance loaded the updated adapter in an isolated package namespace and shared
the existing v10 session; the host's existing Harness/wrappers were not hot-reloaded.
On a newly created UserWidget/tree/canvas, the original core rejected missing
consent, set RootWidget to the canvas and returned null/object before/after.
Restoration returned the same object/null pair. An independent stored-value
read confirmed null; exact generic-holder baseline was restored. No viewport,
focus/input or GC stress operation ran. Evidence: local
`evidence/harness-set-live.json` and `logs/management-host-v10.stderr.log`.

The normal persistent Harness now loads the updated adapter after controlled
handover. The rebuilt v10 package also passed fresh-game startup, widget-root/
viewport lifecycle and normal game shutdown, including a disabled service
heartbeat and zero host/controller exit codes. See DEVELOPMENT.md for the failed
exit-reporting case, repair and preserved evidence. Next continue visible menu
controls, broader value codecs, key/focus handling, traces and agent bridge.

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
| set | Exact reflected property, explicit literal allow_mutation:true, before/after values | v10 adapter supports scalar ObjectProperty via owned game-thread assignment; other types remain pending |
| invoke | Reflected member lookup and named argument conversion; bounded result depth | Native primitive/object/class calls supported through verified dispatcher; nontrivial native types and Blueprint frames pending |
| retained results | Up to 16 named original SDK values, indexed $value paths, 60-second TTL, explicit release | v8 owns object outputs within invocation and integrates original retain/release/expiry; opaque native values remain unsupported; snapshots alone do not own memory |
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

## Original core integration and initial schema

The original `core.py` is copied unchanged into `src/expedition33/introspection`,
with its MIT license. Normalized source SHA256 is
`6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543`.
`Harness` supplies a compatibility adapter, keeping the original roots/search/
schema logic, pagination, result keys and bounds. Status explicitly reports
supported operations separately from original operations and parity_complete=false.

PROVEN static target path semantics: live reflection identifies GetPathName thunk
14384f9c0, which calls 1413b2910 and recursive 1413b2aa0. Separator is ':' when the
outer is not Package and its outer is Package; otherwise '.'. Package getter
1413400c0 registers /Script/CoreUObject.Package. Ghidra outputs are preserved in
`evidence/introspection-path-*.json`. Paths were reconstructed from live ownership
chains and resolved back to their identities; direct engine-return comparison is
still untested. No stock offset/path implementation was imported.

The reusable `expedition33.reflection.describe(catalog, observations)` batches
identity-selected UStruct metadata. Native checks process, index/serial/address,
registered UStruct ancestry, property ownership/extents and stable headers. It
supports generated classes, ScriptStruct and Function observations. Properties
include flags, owner identity and verified struct/enum descriptor identities.
UserDefinedStruct/Enum subclasses required replacing exact native-class equality
with verified registered superclass membership. Return values remain metadata,
not callable pointers or owning native handles.

PROVEN initial live schema: BP_jRPG_Controller_MainMenu_C yielded 20 properties
and 20 functions with inherited owners and parameter flags, in approximately
3.3 seconds. Function candidates come from registered reflected Functions owned
by each class, ordered by registry identity; this differs from the original
SDK's UField linked-list order but retains deduplication and paging behavior.
Object-class, map/set and delegate reference descriptors are still missing.
The original native-class reflection verifier still passes (Actor 80 fields,
HUD 96, Object zero). Thirty Python regression tests pass.

Development use: `launch.cmd introspection --console-key F10`, then `e33i.status`,
`e33i.roots`, or `e33i.request {"op":"schema","class":"Actor","limit":10}`.
Persistent Python access: `py introspection.request({"op":"roots"})`.
Two live mod load/enable/disable/unload cycles passed with native console attached.
Actual typing of these new commands in the UI remains untested. This is source
development functionality, not a new parity-complete release. The existing v0.1
archive is unchanged. `scripts/verify_live_introspection.py` preserves live results.

Further live checks passed: follow the controller's Rotator reference into a
ScriptStruct schema (Pitch/Yaw/Roll, all DoubleProperty); reject an intentionally
wrong serial before metadata access; reject an ordinary controller object as a
UStruct. These tests do not imply any value-write capability. The unchanged
original core's game-thread docstring describes its BL4 host; the E33 adapter
executes on the external Python owner thread and only performs read-only queries
at this stage. Future engine-facing mutations must use the native game-thread
transport, not this external reader.

Next: finish type-reference metadata and safe reflected value reads, then adapt
inspect/snapshot/diff; file service and agent operations; writes/invocation/traces;
retained values, reload, full UI/exit/relaunch and packaging validation.

## Local-file protocol port

PROVEN 2026-10-08: the original client/protocol is now adapted to the external
SDK controller. Start `launch.cmd introspection`, then from a
second terminal use the existing D: Python environment:

```text
python scripts/e33_introspect.py status
python scripts/e33_introspect.py roots
python scripts/e33_introspect.py schema --class Actor --limit 20
python scripts/e33_introspect.py request request.json
```

The client remains standard-library-only and retains `send(request, data,
timeout)`, stdin request support, original response keys, UUIDs, session/expiry
checks and no automatic mutation retries. Default data is
`settings/E33Introspection`. Requests are atomically claimed as `.processing`;
crash leftovers are never replayed or overwritten by a duplicate ID. Responses
remain as local evidence. Request/response limits are 64/256 KiB, including the
final response envelope. Settings and logs are excluded from Git/package payloads.

`FileService` adapts the original entry-point pump. `ModLoader.poll` now supports
an optional mod-owned `poll()` on the Python owner thread, with BaseException
containment and existing deterministic session cleanup. No BL4 camera hook or new
socket is installed. Heartbeats identify controller and target PIDs separately;
they do not claim that Python runs on GameThread. Normal unload disables the
heartbeat; unexpected process death leaves it stale and clients reject it after
five seconds. Engine-facing work remains subject to existing native scheduling.

`scripts/verify_live_introspection_service.py` ran an isolated 25-second host
(PID12964) against game PID34604. A separate client completed status, roots,
Actor schema, invalid-operation rejection and a subsequent status in the same
session. Host exit was zero; enabled=false persisted and no claims remained.
Evidence: `evidence/introspection-file-service-live.json` and host log. An initial
verifier run incorrectly compared a Windows venv-launcher PID with its child
controller PID; it was corrected to launch the same installed base interpreter
directly. That failed verifier is not counted as a protocol pass.

38 Python tests pass, including seven protocol tests and mod-poll exception
cleanup. The protocol is working for currently ported read operations; mutations,
agent actions, retained values and full gameplay/relaunch parity are still pending.

## Stored values, original inspection and snapshots

PROVEN: `expedition33.values.read_values(catalog, observed)` now uses identity-
selected native reads on generated-class instances. It returns stored BoolProperty,
ByteProperty, IntProperty (signed32), UInt16Property, FloatProperty, NameProperty
and registered ObjectProperty references. Static-array elements are bounded to
1024; unsupported dynamic/container/struct types remain explicit per-field errors.
This is stored backing data, not custom getter execution. It neither pins objects
nor makes the external snapshot GC-atomic. Reference changes since the catalog
become field errors; native process/slot/header changes reject the observation.

Target evidence: numeric export 14136b3e0 adds the reflected offset and calls
vtable+0x200. Live property vtables lead to 141370ac0 (float load), 141370a60
(32-bit value, `%d` at146d9da10) and 141370a30 (16-bit value, `%u` at146da3090).
Byte export14136a290 loads an unsigned byte. Name export14136b200 copies the
8-byte name before the independently derived formatter. Object export14133c740
reads the stored reference; our reader accepts only null or a registered, stable
UObject identity. Existing BoolProperty export evidence remains applicable.
Vtable mappings/decompilations are preserved in evidence/introspection-property-
vtables.json, introspection-value-export*.json and introspection-scalar-conversion*.json.

The unchanged original Explorer now services inspect, snapshot and diff through
the adapter, including member selection, per-field errors, object references and
its existing snapshot limits. Live controller specimens include Player resolving
to the independently discovered LocalPlayer, bShowMouseCursor=true,
SmoothTargetViewRotationSpeed=20.0, LastCompletedSeamlessTravelCount=0,
RemoteRole=1, NetDriverName=GameNetDriver, NetTag=0 and NetUpdateFrequency=100.0.
These are observations at the main menu, not fixed SDK assumptions. Tags reports
an ArrayProperty conversion error until that decoder is implemented.

`scripts/verify_live_introspection_values.py` compares all33 legacy Actor boolean
observations, checks reference/name/numeric specimens and checks the original
snapshot diff against the returned pages. The repeated selected pages had no
changes. A large-float formatting regression (225000000. is invalid JSON) was
caught during verification and corrected; the formatter now preserves float type
and negative zero without a trailing decimal point. Four parser regression tests
cover element duplication, partial array failure, stale references and target
identity. This does not establish arbitrary property conversion or writing.

The updated file-client verifier also passed roots/schema/inspect through a
separate isolated host, including the live Player reference and boolean result,
error recovery and normal shutdown. Evidence remains in
evidence/introspection-file-service-live.json. All42 Python tests pass. Neither
this protocol check nor the read tests claim native UI typing, gameplay travel,
mutations or general retained-value ownership.

## Stored strings and doubles

PROVEN 2026-10-08: DoubleProperty and StrProperty stored reads now extend the
same identity-checked API and unchanged original Explorer. Target numeric vtable
slot +0x200 resolves to 141370af0 for DoubleProperty, which reads eight bytes.
StrProperty export 14136bd30 uses the reflected offset, reads a data pointer and
count at +8, subtracts the terminating character and copies two-byte code units.
Evidence: introspection-double-string-types.json and
introspection-double-string-decompile.json in the local evidence directory.

The reader validates the 16-byte string header and bounds count/capacity, checks
repeated header/content/property observations, requires the complete string's
terminator and strictly decodes UTF-16. Reads are capped at 8192 code units;
prefixes avoid split surrogate pairs and are marked in StoredValues.truncated.
The original Explorer retains its own 4096-character output bound. These checks
do not pin allocation lifetime or make external reads atomic. Custom getters are
not executed. The double formatter preserves round-trip precision, negative zero
and tagged nonfinite values.

`scripts/verify_live_introspection_strings.py` passed against PID34604, including
ProjectName="Expedition 33", ProjectVersion="1.5.6.0", an empty Description and
Blueprint default BPS_LookAtTarget_C.StartTime/RotationProgress (both 0.0). Those
are observed specimens, not universal expectations about gameplay values. The
verifier discovers a double-bearing class through loaded metadata. Evidence:
evidence/introspection-strings-double-live.json. All43 Python tests pass.

The persistent introspection controller was restored without --seconds or an
optional function-key binding. Default native backtick/Tilde remains the console
key; F10 was an extra validation binding. Its process and advancing heartbeat were
verified. No new physical keypress/UI validation is claimed by this milestone.
Future validation must preserve this user session instead of replacing it with a
bounded controller. Recursive types, writes, general calls/traces, agent actions,
retained native values and full harness relaunch/reload parity remain pending.

## Class and delegate schema references

PROVEN 2026-10-08 in a separate candidate reader: the unchanged original core
now exposes PropertyClass for ObjectProperty/WeakObjectProperty, MetaClass for
ClassProperty/SoftClassProperty, and SignatureFunction for multicast inline and
sparse delegate properties. This is metadata; it does not add weak-reference
value resolution, delegate invocation or binding.

The target vtables' +0x68 type-formatting slot resolves to 14136e440 (class
reference at +0x70), 14136ea40 (class constraint at +0x78), or 14136e730 calling
14136f160 (nullable multicast signature at +0x70). The reader validates each
reference's registry identity, Class/Function ancestry and repeated header/slot
observations. Python rejects name, serial or address changes since catalog
capture. Evidence is preserved in introspection-reference-vtable-slots.json,
introspection-reference-types-decompile.json and
introspection-delegate-types-decompile.json.

`scripts/verify_live_introspection_references.py --probe
build/research-probe-schema/research_probe.exe` passed actual reads through the
production catalog/parser and original schema algorithm. The launch substitution
selects a separate compiled executable; it does not supply mock game responses.
Observed references include Actor.RootComponent -> SceneComponent,
Actor.ParentComponent -> ChildActorComponent,
PlayerController.OverridePlayerInputClass -> PlayerInput,
InputSettings.DefaultInputComponentClass -> InputComponent, and both Actor and
Controller delegate signatures with complete paths. Evidence:
evidence/introspection-reference-schema-live.json. All44 Python tests pass,
including rejection of recycled descriptor references.

Deployment boundary: the running user's console controller still owns the prior
default research_probe.exe. It was not stopped, rebuilt in place or reloaded.
These additional descriptors are verified in the candidate build and source;
they become available to that persistent session only after a normal controller
restart with the newly built default reader. Map/set references, nested inner
descriptors and unverified property variants remain pending.

## Bounded dynamic-array observations

PROVEN2026-10-08 in the separate candidate reader: stored ArrayProperty values
now feed the unchanged original Explorer inspect/snapshot/diff algorithms.
Supported inner types are ByteProperty, IntProperty, UInt16Property, FloatProperty,
DoubleProperty, NameProperty and ObjectProperty. This is copied observation data,
not ownership of a native array, writable storage or a retained function result.

Target evidence: ArrayProperty export virtual +e0 resolves to14133c540. It reads
allocator flags at property+70, the inner descriptor at+78, the data at header+0
and count at+8. Its flags-bit0 branch decodes a relative/frozen pointer. Copy routine
14133a6f0 compares capacity at header+c and branches on the same allocator flag.
Export helper14133c010 strides by the inner property's ElementSize (+34). MCP
responses are preserved as evidence/introspection-array-export.json,
introspection-array-copy.json and introspection-array-helper.json. The additional
requested address14133f600 was not a defined Ghidra function; no layout conclusion
was drawn from that missing result.

The reader rejects the flagged allocator form and unsupported inner types,
validates the16-byte array header, count/capacity bounds, inner owner/type/extent,
then copies at most64 elements. It rechecks bytes, header, property and inner
descriptor before publishing the field. Object elements retain registry identity
and serial validation, then Python verifies them against the current catalog.
Any changing/invalid element rejects the entire property. External reads remain
non-atomic and do not pin GC or allocation lifetime.

StoredArray exposes an immutable copied prefix and the observed total length.
Iteration visits copied items; indexing beyond the prefix fails explicitly.
The original core therefore reports the true length and its normal64-item
truncation flag. Python validates array tags, element kinds, counts, truncation
and object identities. Tests cover a100-element observation with64 copied items,
stale references, invalid extents/types, unsupported empty types and nonfinite
floats. The large-array/truncation case is unit-tested, not yet a live specimen.

scripts/verify_live_introspection_arrays.py --probe
build/research-probe-schema/research_probe.exe passed on PID34604. Confirmed:

- Actual BP_jRPG_GI_Custom_C GameInstance.LocalPlayers contained the same one live
  LocalPlayer object identified independently by the original roots operation.
- Default__RadialForceComponent.ObjectTypesToAffect contained bytes[2,3,4,5].
- Default__Actor.Tags was an empty array; no nonempty NameProperty-array proof is
  claimed from this specimen.
- Original-core inspect and repeated snapshots/diff agreed on all three pages.

Evidence: evidence/introspection-arrays-live.json. The updated scalar regression
verifier also passed against the candidate: all33 legacy Actor bool observations
agree, PlayerController references/numerics/names remain valid, Tags now returns
an array, and snapshot/diff still agrees (introspection-values-arrays-live.json).
All67 Python tests pass and the native /W4 build has no warnings.

Deployment remains deferred to normal controller handover: the current user host
and its previous default reader were preserved; its heartbeat continued. The
candidate executable includes the earlier class/delegate schema improvements.
Bool/string/struct/nested-container array elements, map/set values, and general
retained native values remain unsupported. In particular, input key arrays whose
elements are reflected FKey structs still require the struct decoder; their
presence alone does not establish keybind dispatch or safe mutation.

Deployment follow-up2026-10-08: after the old controller and transport exited
normally, the candidate reader was installed as build/research-probe/research_probe.exe.
SHA256:7a53f78b2a5048678d941c5172df317b5752b0b357c7c8297651aeee11babc8e.
The integrated management host attached and served live roots before and after
a cooperative controller restart. The pinned native v5 DLL was not replaced.
The historical deployment deferral above is resolved; game relaunch remains pending.

## Inner property reference identities — 2026-10-08

The candidate native reader now follows the verified StructProperty/EnumProperty/
ByteProperty/ObjectProperty/WeakObjectProperty/ClassProperty/SoftClassProperty
type-reference contracts when those properties occur as ArrayProperty.Inner.
It checks the child owner/layout, registered reference identity and metatype,
then rereads reference, child and parent pointers. Python rejects references
changed since catalog capture. Size alone is never used to infer an element type.

The adapter extends Explorer.prop_schema via a subclass; original core.py remains
unchanged. Inner adds property_type, element_size and supported referenced object
paths. Existing schema fields remain present. This does not recursively describe
nested containers, implement struct value reads, or introduce native ownership.

PROVEN with scripts/verify_live_inner_schema.py and candidate
build/research-probe-inner/research_probe.exe on34604:
ConsoleKeys -> /Script/InputCore.Key; ActionMappings -> InputActionKeyMapping;
AxisMappings -> InputAxisKeyMapping; LocalPlayers -> /Script/Engine.LocalPlayer.
Both raw descriptors and original-core schema requests with the adapter extension
agree. Evidence: evidence/inner-schema-live.json. All69 Python tests pass, including
recycled child-reference rejection; native /W4 build has no warnings.

This candidate is not deployed to the persistent host yet. The existing console
and host were preserved. Deployment should use the tested cooperative handover;
no need to overwrite an executable held by the live transport or replace its DLL.

## Reflected struct observations and arrays of structs — 2026-10-08

IMPLEMENTED in the candidate: recursively copied stored StructProperty fields,
including structs in dynamic arrays. Reuses target-verified UStruct field chains,
property extents, subclass references and scalar/bool layouts. Bounds:64KiB per
struct,4 struct levels,64 distinct reflected fields per struct,4096 decode nodes
per top-level property and64 copied array elements. Descriptor owner/field chains
have cycle/length guards. Bytes, descriptor identities, reference pointers and
array headers are reread; this is still not an atomic observation or GC pin.

Supported struct members: bool, byte, int32, uint16, float, double, FName, stored
object references and nested structs. Unsupported member types and depth/node
limits produce explicit per-member errors. Container/string/enum members and
static arrays inside structs remain unsupported. Top-level static struct arrays
are bounded to64 elements. Native opaque fields are never emitted as raw pointers.

StoredStruct carries a catalog-checked ScriptStruct identity, immutable field/
type/error maps and a field-truncation indicator. Recycled nested references reject
the containing property. Even empty struct arrays require a matching type identity.
The adapter presents copies to the original Explorer encoder; snapshots/diffs use
the original core unchanged. Its500-node output budget still applies in addition
to native read bounds. Copied structs cannot be used as owned native arguments.

PROVEN on34604 using scripts/verify_live_struct_values.py:

- Default__InputSettings.ConsoleKeys: two reflected Key structs, names Tilde and².
- ActionMappings:154 total, first64 copied; action names, four modifier bools and
  nested Key.KeyName decoded. This is now a live large-array truncation specimen.
- AxisMappings:39 entries, including float scales and nested key names.
- Default__SceneComponent: RelativeLocation Vector(0,0,0), RelativeRotation
  Rotator(0,0,0), RelativeScale3D Vector(1,1,1).
- Direct SDK values and harness encoding agree on key identities and lengths;
  repeated original-core snapshots/diffs are stable for both targets.

Evidence: evidence/struct-values-live.json and introspection-values-struct-live.json.
All33 existing bool observations still agree; scalar/reference regression and
snapshot/diff passed. All74 Python tests pass, including nested type recycling,
empty-array type validation, duplicate fields, depth bounds, invalid scalars,
partial errors and encoding truncation. Native /W4 build passes without warnings.

Candidate: build/research-probe-struct/research_probe.exe. Persistent host31328
and the pinned DLL were preserved; deployment and bundle update remain pending.
These are default configuration observations, not proof that the active Enhanced
Input/CommonUI path consumes every mapping. No mapping or key state was changed.

## Invocation argument planning and dispatch contract — 2026-10-08

IMPLEMENTED: expedition33.invocation.prepare_call builds immutable CallPlan data
from the current catalog and freshly described UFunction. It checks target/function
identity, function metatype, declaring-class ancestry, parameter extent, return
offset, duplicate names and overlapping storage (including packed bool masks).
Arguments are named and explicit. Local fields are excluded; ParmsSize and total
allocation extent remain distinct. Ref/out/return direction follows the original
harness property flags. Return codecs are checked even when there are no inputs.

Current planning codecs: bool, byte, uint16, int32, float, double, object and class
references, including bounded static parameter arrays. Object slots remain zero
in the byte buffer; separate identity patches carry catalog observations with
verified class constraints. Integers cannot masquerade as object addresses.
Strings, names, enums, containers and structs need additional verified codecs and
lifetime contracts. This module DOES NOT dispatch, hold objects alive, decode
results or extend Harness.SUPPORTED. Session.call still has only its existing
fixed getter implementation. A plan is not permission to call a cached address.

PROVEN metadata-only against live34604 via scripts/verify_live_call_plans.py:
WidgetBlueprintLibrary.Create32-byte arguments with three symbolic object patches;
SetInputMode_GameOnly9-byte arguments versus16-byte allocation extent; actual
player-controller IsLocalController1-byte return. IsInputKeyDown was rejected for
unsupported FKey construction. No function was executed. Evidence:
evidence/invocation-plans-live.json. All82 tests pass, including stale references,
class constraints, overlapping bool bits, invalid sizes/returns, missing/extra
arguments, ref/out initialization and unsupported return ownership.

Ghidra evidence in invoke-dispatch-paths.json and invoke-lifetime-paths.json
corroborates dispatcher141393330: allocates using size+58/alignment+5c, copies
ParmsSize+b6, forms an FFrame, handles out properties, invokes through141280940,
and performs property cleanup. Helper141280940 calls UFunction+d8 with context,
frame and return pointer. Actor wrapper14332bb90 applies execution guards before
delegating. Future dispatch must preserve that route; a thunk is not a plain
buffer-taking function. Network/callspace paths exist, so successful transport
delivery alone cannot be reported as proof that the function body ran.

Next: native game-thread plan revalidation and a versioned command/result packet;
explicit outcome semantics and no retry after timeout; bounded result conversion;
engine-owned value construction/cleanup and retention for nontrivial types; then
wire the general call API into the unchanged original Explorer invoke operation.
# Reflected invocation candidate — 2026-10-09

Follow-up: the candidate is now exposed through opt-in `Session(reflected=True)`
and borrowed-session Harness `invoke`. Live SDK, Harness and in-game Python
console getter paths passed;93 tests pass. See INVOCATION.md for usage, named out
parameter differences, non-owning result limits and the remaining parity gates.
`launch.cmd management --reflected` selects this path; default v5 remains available.

The isolated v6 native session now accepts bounded, identity-bearing call plans
and revalidates them on the game thread. It compares target/function identities,
function ownership and metadata, parameter layout, native thunk RVA, primitive
storage and object/class constraints before using the target's own dispatcher.
It does not call a UFunction thunk with an invented ABI. The v5 transport remains
the default; v6 has distinct message, mapping, DLL and executable names.

Live proof on build23765773, game PID34604: Controller.IsLocalController on the
actual main-menu PlayerController returned true twice. A stale serial and changed
function flags were rejected before dispatch (202/204), with subsequent pings
working. The candidate session closed normally. Evidence:
`evidence/reflected-call-live.json`; reproducer:
`scripts/verify_live_reflected_call.py`. Stop the existing host cooperatively
before using that reproducer; do not run v5 and v6 owners concurrently.

Wire outcomes distinguish not_dispatched, dispatch_returned and unknown. A
dispatcher returning does not prove an RPC/body executed; faults/timeouts must
never trigger automatic retry. Object bytes are represented by separately
validated identity observations, not owned/retained native values. Public
Session.call was not expanded by the initial candidate. Native
strings, names, enums, structs/FKey, containers, Blueprint frames, retained
objects and widget creation remain unsupported or unvalidated.

Validation: 87 Python tests, including Python-to-C++ packet agreement and
capability gating;18 native malformed-packet/layout checks; v6 builds and default
v5 compilation pass /W4 /WX. The original Explorer core remains unchanged.
After the controlled test, persistent v5 host34788 was restored with fresh
session6c7548d8fdf54980a5dd6199fa9458c0. Live roots and Python console output
worked after restoration; this is same-game reconnect proof, not game relaunch.
The first restore launch used an incorrect script path and exited before attach;
the corrected scripts/run_sdk.py launch is the validated persistent host.

## Retained-object research — 2026-10-09

WIDGET_OWNERSHIP.md records target-specific GC holder registration, traversal and
unregistration paths, corroborated against live engine-owned widget holders.
These are prerequisites for reusable session-owned UObject leases, not an
implementation of Explorer retain. Retain remains rejected before invocation.
Verify the complete collector/lifetime contract before adding leases; ordinary
object observations and returned identities remain non-owning. Native FKey and
other owned value types require separate construction/destruction support.

Follow-up: the target's generic strong-reference collector is identified and
corroborated live. Native creation/release candidate logic and an isolated
fixture are implemented; public retain, session leases, invocation result
retention and live ownership validation remain pending. The original Explorer
core is unchanged. WIDGET_OWNERSHIP.md records exact evidence and limitations.

## Live lease transport — 2026-10-09

The isolated v7 lease primitive now passes live acquire/release, stale-token,
normal-close, controller-exit and reconnect checks. See OBJECT_LEASES.md. All97
Python tests and native ownership fixtures pass. The persistent v6 host is
restored and its console/file-service paths verified. Explorer retain remains
unavailable until scoped Python ownership and atomic invocation-output retention
are connected; the original Explorer core remains unchanged. This is progress
toward full parity, not a replacement of the retained-value requirement.

Public existing-object leases now work through Session and mod scopes, with live
peer-scope cleanup and invocation proof. The persistent host runs v7 via
`management --leases`. The original Explorer retain option is still rejected:
object-valued results must be retained inside their invocation request before
the original retain/release protocol can be enabled without a GC gap. The
Explorer core remains unchanged. See OBJECT_LEASES.md for API and106-test proof.

The isolated v8 native retained-call path now has live existing-object return,
null-return, stale-target and exact-holder cleanup proof (OBJECT_LEASES.md).
It closes the native round-trip ownership gap for its bounded supported types;
the original Explorer retain protocol remains gated until Python result owners,
scope adoption, replacement, expiry and release_value are connected and tested.
No original core changes were made.111 Python tests pass.

## Current retained-value checkpoint — 2026-10-09

The v8 Python owner and mod-scope integration is now implemented. Live original
Explorer retain, `$value` argument reuse, replacement, `release_value`,60.10-second
expiry and close passed against the real PlayerController. Each cleanup restored
the exact baseline engine-holder set. The core is byte-for-byte unchanged;123
Python tests pass. `management --retained` enables this capability, while v6/v7
continue rejecting retain. Supported copied primitives/object outputs are
covered; opaque native struct/container ownership is not. See OBJECT_LEASES.md
and evidence/retained-results-live.json. Traces, writes, agent/log/loader parity,
UMG and native key dispatch remain active work.

## Typed enum adapter — 2026-10-09

The independent adapter now accepts `$enum` arguments with a full reflected type
path and exact member name, for example:

```json
{"$enum":{"type":"/Script/UMG.ESlateVisibility","name":"ESlateVisibility::Hidden"}}
```

Use the exact names returned by the current enum schema. Encoded results include
the numeric `value` annotation; decoding checks that annotation against freshly
read membership rather than accepting it as authority. v13 retained invocation
is required. Invocation retains its existing identity, width, membership and
game-thread gates. Original `$value` storage, expiry and cleanup remain intact;
the preserved Explorer core is unchanged.

Validation: all 186 Python tests pass, including typed round trips, nested
arguments, numeric mismatches, malformed input, sentinels, capability gating,
encoding budgets and original retained-value lookup/close. The underlying v13
Widget visibility calls have separate live proof; this new Harness JSON adapter
has not yet been exercised in the live persistent host. No focus/input-mode or
key-dispatch validation is implied.

Live follow-up: `verify_live_harness_enum_values.py` passed at09:49:40 on
game PID21804, after cooperative v13 controller replacement (old Python8860 /
native12588 exited; new Python23916 / native19188). The source host uses the same
unchanged v13 DLL. An SDK-owned, undisplayed Button accepted named Hidden/Visible
arguments, returned typed JSON, accepted that JSON again, and reused an original
`$value` retained enum. Raw integers, mismatched numeric annotations and unknown
members were rejected while visibility remained unchanged. `release_value`
revoked reuse; Harness close cleared remaining result ownership. The shared
widget fixture removed the child and restored the exact native holder baseline.
Evidence: `harness-enum-values-progress.json`, `harness-enum-values-live.json`,
`enum-v13-first-disabled.json`, and `logs/enum-harness-v13.stderr.log`.
No viewport, input-mode, focus, forced-GC or gameplay-state change was exercised.

Packaged follow-up (2026-10-09): the same enum adapter specimen passed from
candidate20261009T165925Z in fresh Steam game16344, via the persistent native
console in the v16 management host. The imported SDK path was inside the bundle;
original core SHA256 remained6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543.
Named enum input, typed annotations, retained reuse/release, rejection and exact
holder cleanup passed. Output was visible in-game. See
`button-v16-package-harness-progress.json`, `button-v16-package-harness-live.json`
and `logs/button-v16-package.stderr.log`. This confirms the enum adapter after
relaunch, not full Harness parity or gameplay transition coverage.

## Reload prerequisite: failed-cleanup guard — 2026-10-09

Auditing the original agent's cleanup-before-replacement rule found that the
Expedition 33 loader previously allowed re-enable after disable/cleanup failure.
It also discarded the loaded record on unload, allowing load to bypass that
failure. The loader now remembers cleanup failures for its lifetime and rejects
both load and enable for that folder. Unload still releases Python module and
Registry references, but cannot erase the guard. A fresh controller is required
before another attempt; the preceding controller must finish normal shutdown.
A failed mod's callback is not automatically retried.

ModStatus, Registry views and agent mod_list expose cleanup_error. Scope close
now reports a deferred native-menu close as incomplete cleanup; its menu and
protected leases remain session-owned for existing transport draining/shutdown.
Revocation of mod actions/console registrations still runs on error. This does
not claim rollback of arbitrary mod side effects or that deferred cleanup is
permanent; the conservative guard avoids inferring safety from a later poll.

All308 source tests pass. Added cases cover disable failure, command revocation,
blocked enable and unload/load bypass, fresh-loader recovery, and deferred-menu
ownership. Existing menu tests still verify that pending leases stay protected.
The bridge test confirms failed enable reports inner success=false and includes
the cleanup error in mod_list. Evidence: evidence/reload-cleanup-tests.log.
This is source/test validation, not a live fault-injection claim; the running
immutable candidate remains on its previously validated code. Staged digest
reload, dependency replacement and original core reload are still pending.

## Digest-checked installed entry-point reload — 2026-10-09

Implemented ModLoader.reload and Registry.reload, plus original protocol names
mod_reload and reload_changed_mod. CLI commands are reload and reload-changed,
with required --expected-sha256 and global --allow-mutation. The digest covers
exact installed mod.py bytes (maximum 4 MiB), not an archive or dependency tree.
mod_list exposes the digest of the source actually loaded. The original staged
.sdkmod installer, dependency replacement and core reload are still pending;
dev_status explicitly describes this narrower adapter scope.

Reload requires an already-loaded, non-protected, non-servicing-core mod. It
captures and compiles source, checks the supplied lowercase SHA256, then cleans
up the old scope before executing the captured code under a new module identity.
No timestamp-based .pyc cache can replace verified source. Edits during cleanup
cannot change the captured replacement. reload_changed_mod skips only when the
captured digest matches loaded source. Enabled/disabled state is preserved;
Registry selections and old scoped actions become stale. The sole owned Session
and its persistent Python namespace survive successful replacement. There is no
automatic rollback or retry after cleanup/import/enable failure. Failed cleanup
blocks replacement through the previous milestone's loader-lifetime guard.
Import/enable failures after cleanup may leave the mod absent or disabled; inspect
mod_list before attempting recovery. No running core module is hot-reloaded.

All314 tests pass, covering bad hashes, syntax rejection before cleanup, same-size
and same-timestamp stale bytecode, edits during cleanup, cleanup failure, import
failure without rollback, stale actions/selections, disabled-state preservation,
protected-mod rejection, and sole-session/namespace preservation. CLI tests cover
both operations and local digest validation. Evidence: evidence/mod-reload-tests.log.

LIVE PROVEN on game39900 after normal package-controller shutdown (exit0): the
source controller's persistent native console ran scripts/verify_live_mod_reload.py
against a borrowed live Session. Two retained research sources produced different
labels while both called Actor.IsActorBeingDestroyed on the game thread. Consent
and wrong-digest rejection, old-scope revocation, one active replacement hook,
unchanged-source skip, final disable and stale action rejection passed. Hook count
returned from one to the original zero baseline. The original installed example
was not modified. Raw evidence and both sources:
evidence/mod-reload-545123a1205043a38e4823a0629c5158/.

The main Harness file transport also accepted CLI reload of disabled
ManagementExample and reload-changed then reported changed=false. Session was
2b610a0521904902a39949867b8fbb03. Evidence: evidence/mod-reload-cli.json,
evidence/mod-reload-cli-unchanged.json and logs/mod-reload-host.log. Borrowed-session
replacement is live-validated; sole-owned-session preservation is unit-tested.
No new release package or gameplay/travel validation is claimed.

Example (hash the installed file after editing; never reuse a pre-edit digest):

```text
python -I -S -B scripts/e33_agent.py --allow-mutation reload MyMod --expected-sha256 <64-lowercase-hex-digest>
python -I -S -B scripts/e33_agent.py --allow-mutation reload-changed MyMod --expected-sha256 <64-lowercase-hex-digest>
```

## Staged archive preflight and authoring — 2026-10-09

The original bridge delegates staged .sdkmod cleanup, backup and cache invalidation
to a fixed game-specific loader. That loader is not in the preserved Harness
subset and must not be assumed compatible with Expedition 33. The independent
adapter now has a reusable preparation layer in expedition33.mod_archive:
read_candidate verifies the expected archive SHA256, captures all files as an
immutable tuple of bytes, and compiles Python source without executing it.
Candidate preparation does not stop a mod, extract files, install code or change
the running controller. Installation/activation remain pending.

The current archive layout is root mod.py plus relative source/resources. Limits
are 32 MiB compressed archive, 64 MiB expanded total, 4 MiB per file and512 ZIP
entries. Preflight rejects missing entry point, digest mismatch, corrupt ZIP,
encryption, links/special files/reparse entries, path traversal, Windows device
names and stream syntax, trailing dots/spaces, duplicate/case-colliding paths,
file/directory conflicts, bytecode/VCS metadata, and invalid Python syntax.
Digest validation is byte identity, not a signature or execution sandbox.

scripts/mod_archive.py builds deterministic ZIP candidates and inspects them
with isolated -I -S -B Python. Build excludes .git/__pycache__ and .pyc/.pyo,
rejects source links/junctions, bounds reads, and preflights the resulting bytes.
It refuses to overwrite an existing output or place output inside the source.
The inventory reports the archive hash, file count, expanded size and individual
file hashes. No candidate is implicitly sent to or activated by the live game.

All321 tests pass. Archive tests cover immutable snapshots despite subsequent
file changes, no source execution, portable path/alias rejection, symbolic links,
size limits, corruption, deterministic builds, resource preservation, isolated
CLI round trips and overwrite refusal. Evidence: evidence/mod-archive-tests.log.
The isolated CLI also built and inspected the actual ManagementExample source:
evidence/ManagementExample-staged-preflight.zip,
evidence/mod-archive-build.json and evidence/mod-archive-inspect.json.
Archive SHA256: d9e0575ba44fc8d16f24fd8c0a23fda52f75f2eac86b920f9bb973088c73919c.

Usage:

```text
python -I -S -B scripts/mod_archive.py build mods/MyMod staging/MyMod.zip
python -I -S -B scripts/mod_archive.py inspect staging/MyMod.zip --expected-sha256 <archive-digest>
```

Remaining staged-adapter gates: package-local dependency isolation and eviction,
fixed configured staging paths, same-volume prepared installation with backup and
recovery journal, cleanup-before-swap, explicit failed-import state, and live
replacement/cleanup/relaunch verification. These are required before advertising
staged_archive_install support; installed-entry reload remains the only activated
reload path. General traces, keybind/editor work and full Harness parity remain
unfinished.

## Package-local Python ownership and helper reload — 2026-10-09

ModLoader now captures and compiles package-local .py sources before load/reload.
Each load owns a unique Python package namespace and a matching import finder.
Relative helpers (from .helper import value), nested packages and implicit package
directories import from the captured source. Empty package search paths prevent
fall-through to disk or stale .pyc files. Lazy imports use the same captured tree.
Absolute SDK/stdlib/third-party imports retain normal process ownership and are
not evicted. No sys.path modification occurs.

Import failure and unload remove the owner finder and all sys.modules entries
under that exact namespace, then release captured source references. Other mod
namespaces are preserved. Removing module-cache entries cannot revoke arbitrary
Python references held by user code; engine access still requires live SDK scopes.
Root mod.py remains the entry point; root __init__.py and ambiguous module/package
paths are rejected. Python helpers use identifier path components; native extension
reload and general importlib.resources integration are not implemented.

Reload requires expected_package_sha256 when the old or new tree contains helpers,
including helper removal. The digest is SHA256 of compact, key-sorted JSON mapping
relative Python paths to their file SHA256 values. It excludes non-Python resources;
archive SHA256 still covers the complete candidate. mod_list exposes loaded
package_sha256; archive build/inspect exposes the matching python_package_sha256.
The CLI accepts --expected-package-sha256. reload_changed_mod compares whole Python
trees, so helper-only edits no longer look unchanged. The original entry digest
remains required. Old scopes/selections still follow cleanup-before-replacement.

All327 source tests pass. New tests cover identical helper names in two mods,
namespace eviction, lazy capture and uncaptured-file rejection, helper-only reload,
required tree digest, import-failure cleanup, syntax preflight, nested/implicit
packages and module/package ambiguity. Archive and loader tree digests agree.
Evidence: evidence/package-import-tests.log. CLI request shape is also tested.

LIVE PROVEN with scripts/verify_live_package_reload.py on game39900 and source
controller15816/session434737dd9d8742a287a4980e64cf1f19. A research mod's mod.py
remained byte-identical while label.py changed from Helper version 1 to2. Both
versions successfully called the verified Actor.IsActorBeingDestroyed getter.
Missing/stale package digests were rejected; helper-only replacement removed the
old namespace and kept exactly one active hook; unchanged tree skipped reload.
Final cleanup restored the zero-hook baseline. Evidence includes both source ZIPs
and raw replies in evidence/package-reload-fc8014b97155436db01f6bace743c790/ and
logs/package-reload-host.log. The preceding controller exited normally with code0.

Staged folder installation, backup/recovery journal and live archive activation
remain the next adapter work. This validates installed Python-tree replacement,
not archive installation, global dependency/core reload, full Harness parity,
travel/GC, or a new release package.

## Prepared folder swap and recovery inspection — 2026-10-09

expedition33.mod_install adds PreparedInstall for the staged adapter. Preparation
verifies archive bytes, writes a fresh private transaction directory under
mods/.transactions/<random-id>/prepared, and checks package-source compatibility
without executing source or modifying the installed folder. The installed mod
must already exist. Prepared files are checked again before and after cleanup.
Links/junctions and resolved paths outside the configured mod root are rejected.

activate(cleanup) requires the lifecycle callback to return literal True before
moving anything. It renames the installed folder to the transaction's backup,
then renames the prepared candidate into the installed location. Both moves stay
inside the checked mod root; no folder/file is deleted and backups are retained.
Each step records a phase in an atomically replaced, file-flushed JSON journal.
The two folder renames are not one atomic filesystem transaction. A process or
I/O failure between them may leave the installed path absent; inspection and
explicit recovery are required. Full power-loss durability is not claimed.

Transactions cannot be replayed after activation starts, including cleanup failure.
There is no automatic rollback or automatic re-enable. inspect_transaction(root,
id) can read a prior process's journal and actual target/backup/prepared presence.
It derives paths from the configured root and transaction ID, verifies journal
paths match that layout, bounds journal input, and refuses redirected paths.
Reported folder presence is evidence, not a claim that a running mod was activated.

All333 tests pass. Filesystem tests exercise real Windows folder renames in temporary
roots, preserved backups/resources, cleanup-before-move, refusal of false/None/1
cleanup results, candidate changes before/during cleanup, a simulated sharing
violation at the second rename, replay refusal, fresh journal inspection, hostile
journal paths, invalid hashes/names and incompatible package preparation. Evidence:
evidence/mod-install-tests.log. No installed game mod was swapped by these tests.

This is a tested transaction primitive, not staged Harness support yet. The next
integration must use fixed staging paths, serialize lifecycle ownership, connect
cleanup/load/enable to the journal, refuse unresolved transactions on startup,
provide explicit recovery policy, and validate archive replacement live. The
running source controller remains on the earlier package-import milestone.

## Staged loader and Harness integration — 2026-10-09 (source-tested)

ModLoader.install_staged now connects the prepared transaction to scope cleanup,
namespace eviction, captured-source loading and preservation of enabled state.
Only already-loaded, unprotected, non-core mods outside active lifecycle/action
transitions qualify. The archive path is fixed to staging/<folder>.zip beside
the configured mods root. The caller supplies its complete archive SHA256.
Entry/tree digests are checked again after installation and before source runs.
The transaction records activating before import and committed after successful
load/enable. Old backups remain available; no automatic rollback/replay occurs.
The shared Session remains alive through replacement.

Load, enable, entry reload and staged install inspect prior transaction journals.
Incomplete cleanup/swap/activation blocks the affected folder even in a fresh
loader. Prepared-only transactions have not changed installed code and do not
block it. Invalid or redirected journal state stops inspection rather than being
silently ignored. Committed transactions with recorded errors also block loading.
History inspection is bounded to1024 transactions. Explicit recovery/maintenance
policy is still pending; manually treating a failed activation as committed is
not supported.

Registry and Harness expose mod_install_staged with literal allow_mutation:true.
The CLI command is install-staged MOD --expected-sha256 ARCHIVE_HASH, with global
--allow-mutation. It uses the same one-send transport and success/error envelope
as other lifecycle actions. A timeout is not authorization to retry.

All338 tests pass. Integration tests verify action replacement and old-scope
revocation, backup preservation, successful fresh-loader startup, failed-import
startup blocking, cleanup-failure blocking while old files remain intact,
bad-archive rejection before disable, bridge consent, and CLI request shape.
Evidence: evidence/staged-loader-tests.log. Existing archive/transaction fault
injection tests also pass. These are source and temporary-filesystem tests;
live staged installation has not yet been validated and no new bundle was made.
The current live controller still runs the previous package-import source.

Remaining gates before treating this as a finished staged-reload feature:
explicit recovery and concurrent-process policy, live archive replacement with
resources and helpers, controller/game relaunch checks, and packaged validation.
Full Introspection Harness parity, general tracing, menu performance and the
keybind/editor work remain incomplete.

### Live staged archive replacement — 2026-10-09

PROVEN in the live main-menu game session after cooperative source-controller
replacement: verify_live_staged_install.py created an isolated research mod,
installed its digest-verified ZIP through mod_install_staged, preserved the old
folder as a backup, and loaded the replacement helper module and JSON resource.
The operation without literal allow_mutation:true was rejected. Both versions
called the verified Actor.IsActorBeingDestroyed getter successfully. The old
scope closed, exactly one replacement hook remained while enabled, and closing
the test loader restored the zero-hook baseline. A fresh loader read the installed
version and called the same real getter; closing it again restored zero hooks.
The journal reached committed with the backup retained.

Raw requests, archive, sources, retained backup and result are under
 evidence/staged-live-6932be5b275d4f459b1142aa1db9a200/.
Controller log: logs/staged-install-host.log. Archive SHA256:
b7c1b09c8ed79c58369457fd71f2953213fe39bfce237e2ed477d38a885de8d1.
The install request took2414.99ms and correctly reported over_budget:true;
this is not a responsiveness guarantee. The external controller performed the
lifecycle operation using its borrowed shared Session. No native DLL was rebuilt.

This validates a fresh ModLoader within one live game/controller session, not
full controller/game relaunch of the installed archive. Explicit failure recovery,
concurrent-process policy, relaunch and updated packaged validation remain open.
The prior338 source tests remain the source baseline; this addition is the live
verification script and evidence, not a new SDK release or full parity claim.

### Exclusive mod-root ownership — 2026-10-09

ModLoader now owns an OS-backed exclusive lock on its resolved mod directory
until close. A competing loader in the same or another process fails before
loading mod code. Different roots remain usable with a shared live Session.
Windows uses a nonblocking byte-range lock; the fallback uses flock. The
.sdk-loader.lock file stays in place and is ignored by Git: deleting/replacing
it while a controller is alive would defeat cooperative ownership. Packaged
source selection excludes it. Process exit releases the OS handle without
requiring a stale PID/lock-file deletion heuristic. A closed loader cannot be
reused to perform lifecycle operations after relinquishing ownership.

All341 tests pass in evidence/mod-root-lock-tests.log. New tests use actual
separate Python processes to verify exclusion, normal release, and release
on os._exit without Python cleanup. Existing borrowed-session and fresh-loader
checks now close the previous loader first. This lock serializes cooperating
controllers; it is not protection against arbitrary external file edits, a
native hook-cleanup guarantee, or a lock adopted by older running SDK versions.

The currently resident source controller predates this change. No live or
packaged validation of this revision is claimed. Offline restore/recovery will
use the same root ownership boundary; that operation remains to be implemented.

### Explicit offline install recovery — 2026-10-09

Added recover_transaction and scripts/mod_recovery.py inspect/restore. Restore
requires the freshly inspected journal SHA256 and exclusive mod-root ownership.
It preserves the prepared/rejected candidate, restores the original installed
folder from its backup where needed, and records rolled_back without importing
or enabling any mod. The loader accepts that terminal recovery phase. Successful
committed installs and the servicing core mods are excluded. Multiple unresolved
transactions for one mod or ambiguous folder states are not guessed through.

Recovery journals each rename boundary. A newly authorized request with a fresh
digest can continue after a rename succeeded but its next journal write failed;
it observes source/destination presence rather than blindly repeating a rename.
Journal writes now also reject redirected temporary/journal files. The journal
digest identifies inspected state, not trusted integrity of externally edited
files, and filesystem recovery does not prove native cleanup. Controller stop
is required; uncertain native cleanup additionally requires game exit.

All348 tests pass in evidence/mod-recovery-tests.log. Coverage includes preserving
non-executed rejected code, pre-swap and post-backup restoration, competing-owner
and stale-digest rejection, fault injection at both recovery journal boundaries,
missing-backup/committed rejection, real isolated CLI inspection/restoration,
and a fresh loader enabling the old version after a failed replacement import.
No new live failure injection, controller/game relaunch or release archive was
performed for this revision. Those gates and full Harness/menu/keybind work remain.
