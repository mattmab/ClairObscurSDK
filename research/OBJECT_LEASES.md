# Experimental native object leases — 2026-10-09

The v7 transport implements target-derived strong UObject leases, exposed through
Session and mod scopes for existing objects. Full Explorer result retention is
unfinished. The initial native proof and subsequent public API proof are recorded
below. Target: Steam23765773, executable SHA256
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
