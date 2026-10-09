# Experimental native object leases — 2026-10-09

An isolated v7 transport now implements target-derived strong UObject leases.
This is an internal SDK primitive, not full Explorer retain or a public Python
ownership API. Target: Steam23765773, executable SHA256
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

Next: expose scoped Python leases, release them on mod/Harness lifecycle changes,
and retain object-valued invocation outputs inside the SAME game-thread request.
Separate acquire after returning Create's result would still leave a GC gap.
Then validate a bounded widget create/add/remove/release specimen, collection
survival, focus restoration, game relaunch and isolated packaging. Full Harness
parity, native UMG and key dispatch remain unfinished.
