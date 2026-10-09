# Reflected native invocation

Status on 2026-10-09: experimental public API with a live-validated boolean getter.
Full BL4 invocation/value-ownership parity remains incomplete. All layouts and
dispatch paths are specific to Steam build23765773 and its fingerprint.

## Start and use

Build the separate v6 pair with `scripts/build-invocation-candidate.cmd` while
that DLL is not pinned in a running game. Stop any existing SDK host through
`mods select sdk.management`, then `mods action shutdown`. Start the persistent
host with `launch.cmd management --reflected`. Do not attach a second session
alongside an existing v5 or v6 owner. The default launcher still selects v5.

In the native backtick console, the following was executed successfully:

```python
py introspection.request({"op":"invoke","target":introspection.request({"op":"roots"})["PlayerController"][0],"member":"IsLocalController","allow_mutation":True})
```

It displayed `True`. The target is resolved from live roots, not a cached pointer.
The existing `py`, native Unreal command path and `mods` fallback share the host.

For a standalone controller, `with Session(reflected=True) as session` enables
`session.invoke(target_observation, function_observation, **named_arguments)`.
Both observations come from the independent live catalog. It returns an
`InvocationResult` containing `return_value`, immutable named `outputs`, and
`outcome='dispatch_returned'`. Mod scopes forward the same method and never
create another transport. `Session.call` retains its fixed-getter behavior.

`Harness(session=session_or_scope)` advertises `invoke` only when that session
supports it. Closing the Harness does not close its borrowed session. Requests
retain the original Explorer mutation gate: `allow_mutation` must be exactly
true. No-out calls preserve the original scalar/object return shape. Calls with
out parameters currently encode `{"return": ..., "out": {"Parameter": ...}}`;
this named shape is an explicit adapter difference, not full BL4 tuple parity.
Original Explorer source remains verbatim.

## Contract and limits

Implemented codecs: bool, byte, uint16, int32, float, double, object/class
observations, and bounded static arrays of these. All named input arguments are
required; no guessed default values. Native validation rechecks identities,
ownership, type constraints, layout, game-thread/GC state and the dispatcher.
Native-only functions are accepted; Blueprint frames and owned native argument
types are not supported. This is not a promise that every native function with
a supported signature is suitable to call in every game state.

No raw pointer arguments, native strings/names, structs/FKey, containers or
retained results. The Harness rejects `retain` before any call. Object returns
are checked against a fresh catalog; they do not root objects or protect them
from later collection. Widget creation, retention, focus changes and key
construction remain separate validation gates. Primitive out parameters and
object return validation have fixture coverage, not live functional proof yet.

`InvocationError.outcome` distinguishes pre-dispatch rejection, unknown outcome,
and dispatch-returned/result-validation failure. Error text includes that outcome
for console/file clients. Never retry automatically: a timeout or failed result
observation may follow an already completed side effect. A dispatcher returning
does not prove an RPC or native function body executed. Calls wait on the external
controller thread; native dispatch is scheduled on the game's owning thread.

## Evidence

- `evidence/reflected-call-live.json`: getter twice, stale-serial and changed-
  layout rejection without session disconnect, normal close.
- `evidence/harness-invoke-live.json`: public SDK getter, original Harness invoke
  twice, mutation/retain gates, scope close followed by working fixed getter.
- `logs/management-host-v6.stderr.log`: persistent console result `True` at
  00:43:13 local time. Host36068, game34604, session7a2f21707bb543c58819280c284cf95b.
- 93 Python tests, including single-attempt rejection/timeout handling; native
  packet/compile checks from the preceding milestone.

This evidence covers same-game session handover and reconnect. Full game relaunch,
broader invocation specimens, native UMG and general keybind behavior remain open.
The earlier private ZIP is immutable and does not contain this feature.
