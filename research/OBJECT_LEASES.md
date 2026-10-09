# Experimental native object leases — 2026-10-09

The v7 transport implements target-derived strong UObject leases for existing
objects. v8 adds public retained invocation, scope ownership and original Explorer
retained values, with live proof recorded below. The first new-widget viewport
test exposed lazy serial assignment. v9 now stabilizes retained output serials
through the verified engine allocator; base UserWidget create/add/remove/release
passed live with exact native holder cleanup. Other lifecycle gates remain. See
WIDGET_OWNERSHIP.md. Target: Steam23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.

## Implementation

- A maximum of128 independent native holders per session; duplicate object
  acquisitions own separate references. No shared UObject root bits are changed.
- Opaque nonzero tokens increase monotonically across sessions in the pinned
  runtime. Slots can be reused, tokens cannot. Session nonce and token checks
  reject cross-session or stale release requests.
- Creation revalidates index/address/serial, game thread, GC and exit guards.
  Allocation, registration, collector vtable, write barrier and deletion use
  the exact target paths recorded in WIDGET_OWNERSHIP.md.
- The complete generic collector vtable and object slot are initialized BEFORE
  registration. This deliberately changes the observed constructor ordering:
  registration reads only holder flags and appends its pointer. Publishing a
  complete collector avoids leaving a pure-virtual base vtable in the registry
  if registration is interrupted. Live registration confirmed this sequence.
- Explicit release and session close use the engine deleting destructor.
  Controller exit asks the existing target-owned watcher to clean up on the
  game thread. A GC-deferred normal close keeps the cleanup hook until a later
  message can complete it; it does not acknowledge successful cleanup early.
- Ambiguous registration/destruction faults remain tracked and prevent runtime
  session reuse. There is no blind retry, pointer reuse or unconditional free.
  This is containment, not arbitrary native-fault recovery. Engine allocation or
  registration faults can compromise internal state/locks; automatic repair is
  not claimed. Terminal teardown may leave bounded native holder storage for
  process exit. Such holders use engine vtables, not SDK callback addresses.

v7 has separate message/mapping/DLL/reader names. Build with
`scripts/build-lease-candidate.cmd`; do not overwrite its now-pinned DLL in the
running game. Default v5 and opt-in persistent v6 remain available. The internal
Python transport recognizes the v7 handshake and40-byte lease packet; it rejects
lease commands before I/O when connected to an older backend.

## Live evidence

`scripts/verify_live_leases.py` passed on game PID34604 at the main menu:

1. A stale controller serial was rejected (404), with zero active leases.
2. Two independent leases for the live PlayerController returned distinct tokens.
   A separate read-only probe found both holders in the engine's normal GC list,
   with matching object index236646/serial83421. Generic-holder count rose3→5.
3. Explicit release removed one lease. Releasing that token again returned402.
4. Normal close released the remaining holder; the count returned to3.
5. A new session rejected the previous token and allocated a newer token.
6. Deliberately exiting only the candidate controller subprocess released its
   holder through the watcher. The count returned to3; reconnect reported zero
   leases and a successful ping, then closed normally.

Evidence: `evidence/leases-live.json` and the identity-checked
`evidence/gc-owners-live.json`. The specimen retained an object already owned by
the game. **Survival of a newly created object across collection is not proven.**
No widget was created, GC forced, input mode changed or gameplay command run.

The persistent v6 management host36068 exited cooperatively through
`mods action shutdown`. Host5964 was restored afterward, session
a5625d3b1840402d89c941843dd8caaa. Live roots returned through the file service and
`py print("Console restored after lease validation")` executed through the
native console. Evidence: `leases-host-restored-roots.json` and
`logs/management-host-v6-restored.stderr.log`. This proves same-game reconnect,
not game relaunch.

## Validation and remaining work

Both candidate binaries compile /W4 /WX. Native fixtures cover capacity,
independent duplicate ownership, stale/session tokens, deferred close, rejection
rollback and uncertain registration/destruction. The18 invocation packet checks
and default v5 compilation pass; all97 Python tests pass.

Next: retain object-valued invocation outputs inside the SAME game-thread request
and connect ownership to the original Harness lifecycle.
Separate acquire after returning Create's result would still leave a GC gap.
Then validate a bounded widget create/add/remove/release specimen, collection
survival, focus restoration, game relaunch and isolated packaging. Full Harness
parity, native UMG and key dispatch remain unfinished.

## Public and mod-scoped Python ownership — subsequent milestone

The initial internal-only boundary above is superseded for existing objects:
`Session(leases=True).retain(observation)` now returns an `ObjectLease`. It also
enables reflected invocation. `launch.cmd management --leases` selects this
backend for the persistent mod host; default and `--reflected` remain available.

```python
# Use the session supplied to your mod; do not open a second native owner.
with session.retain(existing_object) as lease:
    result = session.invoke(lease.object, verified_function)
```

`lease.object` is an identity observation accessible while the lease is active,
not permission to dereference native memory or bypass future identity checks.
`release()` returns True after acknowledgement. A confirmed GC deferral returns
False, revokes access immediately and queues cleanup on the session's owner-thread
poll path. `release_pending` reports that state. Unknown acknowledgements abort
the controller for native watcher cleanup and never trigger automatic retries.
`LeaseError` exposes outcome and native_error. A failed/unknown close does not
pretend that individual releases were acknowledged.

ModLoader-provided scopes track their own leases. Closing one scope releases or
queues only that scope's holders, blocks subsequent access, and keeps the shared
session/other mods usable. Dropping a Python lease does not invoke native code:
the root session retains bookkeeping until explicit release or shutdown. Use a
context manager or release explicitly to avoid exhausting the128-holder bound.

Live test `scripts/verify_live_python_leases.py` observed both mod holders in the
engine list, closed one scope, and invoked IsLocalController through the other
scope's leased observation. It also passed context-manager cleanup, stale-serial
rejection and session cleanup. The exact baseline set of holder addresses and
object identities was restored, not only its count. Evidence:
`evidence/python-leases-live.json`. All106 Python tests pass, including deferred
scope cleanup, malformed acknowledgements, wrong-thread rejection and failed
close state handling.

Persistent v7 host20776/session7d916f8d7f91485c8d80c76d86a7cbe1 was started after
the controlled test. File-service roots work. In-game Python executed
`with sdk.retain(sdk.find_object("Default__Actor")) as lease: print("lease active:", lease.active)`
and printed True; the subsequent native probe found only the three baseline
generic holders. Logs: `logs/management-host-v7.stderr.log`.

Still pending: atomic retention of object-valued invocation outputs, original
Explorer retain/release semantics, new-widget collection survival and relaunch
validation. This existing-object API cannot close the gap between Create's return
and a later Python retain command. It must not be used to claim that gap is solved.

## Retention inside native invocation — isolated v8, 2026-10-09

Implemented and live-tested: a separate `retained-invoke` operation acquires an
engine holder for each non-null object/class return or out slot before the
game-thread invocation returns. Input-only references are captured and scrubbed
but do not acquire leases. Null outputs require no holder. A preflight checks
the maximum output-slot count against the session's available holder/token
capacity before calling the target dispatcher. It does not reserve or allocate
anything; commands run synchronously on the single game thread.

The new26192-byte envelope wraps the unchanged24648-byte CallPacket plus a
version, count and128 offset/token records. v8 uses its own DLL, message and
mapping names; the loaded v5/v6/v7 binaries are untouched. Each holder is published
in the persistent native session pool before registration. Partial failure after
dispatch remains `unknown`; the test client aborts its controller without retry,
allowing existing target-owned watcher cleanup. A partial result is never a
usable returned value. Fault quarantine and GC deferral retain the v7 rules.

Live evidence: `evidence/retained-call-live.json`, test
`scripts/verify_live_retained_call.py`. The observed GameplayStatics getter has
WorldContextObject at0, PlayerIndex at8 and ReturnValue at16, extent24. Ghidra
thunk14373a480 calls143715460, which searches existing controllers and returns
null when none matches. Source evidence is in `evidence/retained-getter*.json`.

In gamePID34604, the returned controller236646/83421 gained one engine holder
at0x2b40b603980 before acknowledgement. The input reference at0 acquired none.
Release restored the exact baseline holder set. Index-1 returned null with zero
leases. A stale target was rejected before dispatch(error202). A repeated call's
unreleased holder was removed by normal session close, again restoring baseline.

Validation:111 Python tests,18 existing native packet checks, retained envelope
layout/output-selection checks, native ownership fixtures and default v5 compile
checks pass. v8 builds with /W4 /WX. No forced GC, newly created object, widget,
partial native fault, live fixed-array out parameter or game relaunch is claimed.

This is still an internal native/transport capability. The public retained-result
wrapper, mod-scope adoption, original Explorer retain/release/expiry contract and
v8 launcher/package deployment are next. Existing `Session.invoke` and v7 leases
retain their previous behavior. Persistent v7 host24516/session
3f57abac7e494be0acd3236d4fa20ca6 was restored after the controlled test; both mods
report ready. Logs: `logs/management-host-v7-restored.stderr.log`.
At01:39:53 the restored in-game console executed Python and logged
`Persistent v7 console restored after retained-call validation`. The console
closed normally after submission. The private GitHub remote was reverified.

## Public retained results and original Harness lifecycle — 2026-10-09

The internal-only limitation above is superseded: `Session(retained=True)` and
mod scopes expose `invoke_retained`. Its `RetainedInvocation` owns output leases,
provides return_value/outputs/active/release and supports a context manager.
Every token is adopted before result catalog/decoding; conversion failure cleans
up that call's holders. A malformed/unknown acknowledgement or aliased existing
session token aborts ownership without retry. Scope close revokes scalar/null
results too. No finalizer calls native code; abandoned handles retain resources
until explicit scope/session cleanup.

The unchanged original Explorer core now supports retain/release_value/$value
through the v8 adapter. Each native result owner lives beside the core's retained
value. Replacement, expiry and close release owners; unretained results release
after encoding. Failed encoding of an explicitly retained value keeps its owner.
The original16-name,64-character and60-second limits remain. Expiry runs from the
mod pump and before requests. v6/v7 Harness retain stays gated before dispatch.

Live proof: `scripts/verify_live_retained_results.py`, gamePID34604, evidence in
`evidence/retained-results-live.json`. Two independent mod scopes held the same
controller; closing one preserved the other. Public context-manager cleanup
passed. Through the actual original Explorer, retain, `$value` reuse as an
argument, same-name replacement and release_value passed. The original timer
expired after60.09748 seconds. Expiry, Harness close and session close restored
the exact three baseline holder addresses and object identities.

All123 Python tests pass: conversion failure, deferred cleanup, malformed/partial
acknowledgements, token alias rejection, scope isolation, original retention
limits/replacement/expiry and retained encoding failure. Core SHA256 remains
6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543.
The launcher adds `management --retained`; packaging includes the v8 binary pair.
Newly created widgets, forced-GC survival, v8 game relaunch, opaque native values
and full Harness parity remain pending. Next is a bounded verified widget
create/add/remove/release specimen, then focus and key dispatch integration.

Packaging checkpoint: source0aaa437 produced
`dist/expedition33-0.1.0-candidate-20261009T055047Z.zip`, SHA256
2034b2017f5b97218226f3b17eeead15553d35b7c5432ce132f44daa240a6057.
All182 manifest entries match disk and ZIP bytes; the ZIP has no extra files.
Logs/settings/evidence are excluded. An isolated `-I -S -B` packaged v8 management
host returned live roots, invoked/retained the controller through the original
Harness, released it, then completed its bounded50-second run with clean detach
and disabled heartbeat. Evidence: retained-results-package-check.json and
retained-package-host.log. This tests the current game process; a fresh game
relaunch loading v8 solely from the package is still pending.

Persistent checkout host39652/sessionbb387428440b4f12b6527e7cf600e070 now runs
`management --retained`. SDKManagement and IntrospectionHarness are enabled.
At01:53:48, in-game Python printed retained calls=True and argument types including
`$value`; the console closed normally after submission. Log:
`logs/management-host-v8.stderr.log`. The GitHub remote was verified private.
