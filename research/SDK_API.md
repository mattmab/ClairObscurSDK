# SDK_API

## Experimental v10 object assignment

Live proof: an SDK-created WidgetTree.RootWidget was assigned to an SDK-created
CanvasPanel, read back, added/removed through its UserWidget viewport lifecycle,
then restored to null. A stale expected value was rejected before mutation;
all temporary/scoped holders returned to the exact baseline. This proves that
specimen, not all ObjectProperty variants or general Harness `set` parity.

`Session(object_assignment=True)` or `launch.cmd management --object-assignment`
selects the isolated backend. Root and mod scopes expose
`supports_object_assignment` and the following explicit mutation API:

```python
result = sdk.assign_object(tree, widget_tree_class, "RootWidget", canvas,
                           expected=None, allow_mutation=True)
# Restore deliberately while the tree and canvas identities remain valid:
sdk.assign_object(tree, widget_tree_class, "RootWidget", None,
                  expected=canvas, allow_mutation=True)
```

Arguments are observed SDK objects; the declaring class resolves the property
without ambiguous inherited names. Only the verified ObjectProperty layout is
currently supported, with optional fixed-array `element`. The native game thread
compares the current reference with `expected`, checks metadata and identities,
and uses the build's engine setter. Temporary leases span the operation.
`AssignmentResult.before/after` are non-owning observations. Scope close does not
undo mutations; mods must restore state in their explicit lifecycle. Failures
report dispatch outcome and must not be automatically retried. The v10 Harness
adapter supports scalar ObjectProperty `set`, preserving the original literal
`allow_mutation:true` gate and before/after JSON. Status reports `write_types`;
other property types, visible controls and focus/keybind acceptance remain pending.

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: live enumeration, native reflection/bool reads, fixed reflected invocation, persistent observer/session and local mod lifecycle in Steam build23765773. Native console commands and persistent external Python/mod commands are live-tested, including shutdown and relaunch. General reflection values, arbitrary calls/handles, and broader research remain unfinished; see KNOWN_UNKNOWNS.md.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Current research API

`expedition33.objects(*, limit: int = 0) -> list[ObjectSnapshot]` queries a running game. Zero means all occupied slots; positive limits bound returned objects. Each immutable record contains pid, index, serial, address, name, class_name, metaclass_name, and class_index. `RuntimeQueryError` reports native/protocol failure. Addresses and index/serial pairs are observations, not persistent validated handles.

PROVEN by live integration check: 96,053 objects including `/Script/CoreUObject` (Package), `Object` (Class), and the self-metaclass `Class`. Stored BoolProperty values, fixed calls and scoped hooks are supported below; general calls and other property value types remain pending.

## Native class metadata

`expedition33.reflect_class(name) -> ClassMetadata` queries a uniquely named native Class. It returns the class hierarchy, instance sizes, and inherited property metadata (owner/name/type/offset/element_size/dimension plus optional struct_name, enum_name, inner_type and inner_element_size). It rejects duplicate native class names; BlueprintGeneratedClass is outside this initial API. This metadata query returns no property values or persistent pointers.

PROVEN: Actor -> Object, sizes656/40, 80 properties; HUD -> Actor -> Object, sizes896/656/40, 96 properties. Object has no fields. Live check compares all inherited metadata and verifies bounds; unknown class fails explicitly. Reproduce with scripts/verify_live_reflection.py.

## Stored boolean observations

`expedition33.stored_bools(object_name) -> BoolSnapshot` resolves a uniquely named live native object and reads its inherited BoolProperty backing storage. It returns object identity observations and immutable values with owner/name/array element/raw byte/mask/byte offset. It does not invoke custom getters, pin objects, or create an atomic multi-property snapshot. Blueprint classes, other value types and writes remain unsupported.

PROVEN: Default__Actor index28233 exposes33 booleans; Default__HUD index29206 exposes39 including Actor fields. Repeated Actor snapshots matched. The live specimen has bHidden=false and bCallPreReplication=true in the same byte, with distinct reflected masks. scripts/verify_live_bools.py reproduces this build-scoped specimen check.

## Function metadata

`reflect_function("Actor.IsActorBeingDestroyed") -> FunctionMetadata` returns owner/name/index, process and game-thread IDs, flags, parameter buffer size, return offset, build-scoped entry RVA and reflected parameters. Owner/name ambiguity fails. This is a read-only inspection API; entry RVAs are research evidence, not externally callable pointers. The fixed invocation proof below is available; this metadata API itself remains read-only. scripts/verify_live_functions.py checks two independently decompiled boolean thunks, a24-byte struct return, and wrong-owner rejection.

## Fixed invocation proof

`invoke_proof() -> InvocationProof` performs the actual reflected call Default__Actor.IsActorBeingDestroyed on the game thread, returning process/thread IDs, live registry indices, boolean result and verified hook-removal/module-unload status. It accepts no target/function arguments. This is a controlled invocation experiment, not a general call API or gameplay feature. A skipped dispatcher leaves a0xcc sentinel and fails rather than returning a fabricated result.

## Scoped observer proof

`observe_proof(callback) -> ObserverProof` captures two real native getter hook events, restores the entry, then delivers immutable ObserverContext values to Python. Each includes sequence, qualified target, observed object pid/index/serial/name/class, GameThread ID and bool return. Callback exceptions disable that callback and appear in callback_failures without unwinding into the game. The native observer module remains resident until game exit; successful entry restoration and storage detachment are separate from code unloading. This is not a persistent subscription or GC-pinned object handle. scripts/verify_live_observer.py proves live delivery, contained failure, repeated operation, unchanged metadata/storage, and subsequent ordinary invocation.

## Persistent-session API

PROVEN on the supported build: `from expedition33 import sdk`, then `with sdk.Session() as session`. Resolve `actor = session.find_object('Default__Actor')`; call `session.call(actor, 'Actor.IsActorBeingDestroyed')`; subscribe with `session.hook(actor, 'Actor.IsActorBeingDestroyed', callback)` and explicitly `session.poll()` to deliver copied events. Hook handles have active/remove and context-manager support. Session.close restores the native entry and releases callbacks. Keep the session on its creating Python thread. A callback failure disables that subscription and records a bounded diagnostic in session.failures. Game calls are already complete before Python delivery.

The target restriction is intentional and enforced. This is not a general UObject call surface. An ObjectSnapshot owns no engine memory. Getter parameters are empty; the observed result is bool. Runtime checks validate the recorded build, target identity and permanent-prefix membership. The DLL stays pinned until the game exits, even after clean hook removal; stop the game before rebuilding the same DLL filename.

## Session-owned native console

`session.console.enable()` constructs and attaches the build-verified native console on the GameThread. `execute("stat fps")` follows its native command path; `write(text)` emits native console output. `poll()` dispatches copied `py` and registered command input in the external controller's persistent namespace and returns command results. In-game `sdk` names that session; `py sdk.console.execute("stat fps")` schedules the engine operation through the existing transport. Call `poll()` regularly on the owner thread, or use `ModLoader.poll(name)` when the loader owns the session. Python exceptions become bounded output, never native exceptions.

`set_toggle_key("F10")` adds an F1-F12 toggle after enable; `None` removes it. F10 close/open/reopen has live evidence, while Unreal's Tilde mapping stays intact. `disable()` detaches the native console but preserves Python state and registrations for re-enable. Closing the owning session clears both. The key must be configured again after re-enable.

`register("my_mod.command", callback, owner=mod)` returns a removable registration; the callback receives the remaining argument string. `remove_owner(mod)` removes that owner's commands. `expose("my_mod", instance)` adds a non-reserved Python identifier. `history` returns copied dispatcher history and `complete(prefix)` returns lexical suggestions; native Up/Tab navigation for intercepted commands is unsupported. Registration changes discard queued SDK commands to prevent delivering old input to a replacement owner.

`ModLoader.enable(name, console=True, console_key="F10")` enables the console before the mod and exposes its instance as `my_mod`. Shared sessions support multiple enabled mods with separate resource scopes. Trusted Python code can block its controller; the GameThread only queues input and executes scheduled native work. See DEVELOPMENT.md and CONSOLE.md for bounded queues, lifecycle evidence and shipping-build limitations.

## Explicit native ownership (experimental v7)

`Session(leases=True)` supports `retain(existing_observation)` as well as reflected
invocation. A mod receives the same API through its resource scope. Check
`supports_object_leases` before using it. `ObjectLease` exposes `object`, `active`,
`release_pending`, `release()` and context-manager cleanup. Closing a mod scope
revokes its leases without closing peers. Only confirmed GC-deferred releases
are queued for a later owner-thread poll; unknown operations are never retried.

Snapshots alone remain non-owning. No finalizer performs engine calls. Release
explicitly or use `with session.retain(obj) as lease:`; the native128-holder bound
applies across all mods in the session. See OBJECT_LEASES.md for tested behavior,
errors and limitations. A separate v8 path below retains invocation outputs;
the standalone v7 acquire API still cannot bridge a creation-to-retain gap.

## Owned invocation results (experimental v8)

`Session(retained=True)` enables `invoke_retained(obj, function, **arguments)`
and the v7/v6 capabilities. Mod scopes expose the same method and
`supports_retained_invocation`. The returned `RetainedInvocation` owns every
non-null object/class output before the native request returns. Its
`return_value` and `outputs` have the same shapes as ordinary `invoke`; `active`,
`release()` and context-manager cleanup control ownership. Access is revoked on
release, scope close or session close, including scalar/null-only results.

```python
# obj and function are verified observations; use your existing mod session.
with session.invoke_retained(obj, function, **arguments) as owned:
    result = owned.return_value
    # Use result while its owner remains active. It is still an observation.
```

No finalizer calls the engine. Dropping the result leaves its native leases owned
by the session/scope until shutdown; release explicitly to avoid exhausting the
shared128-holder limit. Result-conversion failures release acquired holders.
Unknown acknowledgements abort the controller for native cleanup without retry.
Deferred releases are revoked immediately and retried on session polling.
Ordinary `invoke` retains its non-owning behavior.

The Harness on v8 uses retained invocation internally, preserving the original
`retain`, `$value`, `release_value`,16-name limit and60-second expiry. Unretained
results release after encoding. `Harness.poll()` expires values on the owner
thread; the IntrospectionHarness mod calls it from its regular pump. Closing the
Harness releases its owners without closing the shared transport. Opaque native
values, additional argument types and full Harness parity remain unsupported.

### Stable retained returns (experimental v9)

`Session(stable_returns=True)` selects v9 and includes the retained/lease/reflected
capabilities. `supports_stable_returns` is available on root and mod sessions.
Only retained output identities receive serial assignment while held on the game
thread; ordinary input/target observations still require an exact identity match.
Native serial allocation is not an identity wildcard or a license to reuse stale
observations. The base UserWidget viewport lifecycle passed live; visible menu
contents, focus handling and full Harness parity are not established by that test.

### Numeric struct invocation (experimental v11)

`Session(pod_values=True)` selects v11 and includes the v10 capability chain.
`supports_pod_values` is exposed on both root and mod-scoped sessions. On the
integrated launcher use `launch.cmd management --pod-values`.

Only the target-derived Vector2D, LinearColor, Margin and Anchors profiles are
accepted. Pass plain dictionaries containing every reflected field; Anchors has
nested Minimum/Maximum dictionaries. No default components are guessed.
Results are immutable copied mappings. All components must be finite and within
float range because the verified UMG setters may narrow doubles to floats.
The native dispatcher revalidates exact struct identity and schema on the game
thread. Older backends reject these packets before dispatch.

Live SDK-owned CanvasPanelSlot position/size round trips and margin effects
passed with scoped cleanup. Anchor/color dispatch returned without a rendered
or independent-readback claim. This does not support arbitrary structs, FText,
font state, FKey, enum parameters or the original Harness's typed `$struct`
adapter yet. See WIDGET_LAYOUT_VALUES.md for evidence and boundaries.

### Confirmed target exit

The rebuilt v10 controller reports `TargetExitedError.exit_code` only after its
original game-process handle signals termination and Windows supplies the exit
code. A timeout, failed wait, or closed transport alone is not an exit report.
Pending engine operations still have unknown outcomes and are never replayed.
The management launcher treats exit code zero during polling as normal shutdown;
nonzero codes remain failures. No automatic attach to another game PID occurs.

After confirmed target exit, leases become inaccessible with state
`target_exited`. `release()` returns False: OS process teardown removed resources,
but no engine release acknowledgement was received. Scoped cleanup revokes local
callbacks without sending commands to the dead transport. Existing older native
binaries do not provide this typed report until rebuilt. Native fixture and
142 Python tests pass. The repaired isolated v10 package passed fresh-game widget
root/viewport lifecycle and normal game exit with an outstanding object lease;
game, Python host and controller all exited zero without cleanup tracebacks.
Already-acknowledged releases remain acknowledged after subsequent game exit.
This does not prove cleanup before an abnormal crash or completion of a request
that was pending at exit.
