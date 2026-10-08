# Expedition 33 independent Python SDK research

Status: **live Python object enumeration works**. Native class metadata, stored boolean reads, a fixed harmless reflected invocation, and scoped native function observation with Python callbacks also work. Persistent hook sessions, general calls, broader reflection, and the complete SDK remain in development.

Primary goal: independently discover the local game's Unreal runtime and build a
Python-facing SDK, culminating in a private v0.1 with verified live object queries,
reflection reads, harmless invocation, removable hooks, and a trivial mod.

See `research/GOAL.md`, `research/MILESTONES.md`, and the topic journals.
Evidence is labeled OBSERVED, PROVEN, INFERRED, HYPOTHESIS, or STALE/DISPROVEN.
No Borderlands offsets or layouts are accepted as Expedition 33 facts.

All new tools, repositories, environments, caches, databases, and outputs live
under `D:\HobbyDevelopment`. Existing installed runtimes may be reused.
Game files are read-only research inputs. No public publishing is authorized.

## Reproduce the first capstone

For the fingerprint in `research/OBJECT_SYSTEM.md`, launch the game normally with Steam, then run from this repository:

```powershell
. .\scripts\project-environment.ps1
cmd /c scripts\build-research-probe.cmd
D:\HobbyDevelopment\Python\expedition33-tools\Scripts\python.exe -m pip install --no-build-isolation -e .
D:\HobbyDevelopment\Python\expedition33-tools\Scripts\python.exe scripts\verify_live_enumeration.py
```

`import expedition33; expedition33.objects()` returns immutable observations of live objects. These are snapshots, not GC-pinned engine handles. The reader rejects an unknown executable fingerprint. Evidence outputs remain local and ignored by Git.

Additional live checks: `scripts/verify_live_reflection.py` and `scripts/verify_live_bools.py`. Python entry points are `reflect_class("HUD")` and `stored_bools("Default__Actor")`.

For the actual invocation proof, build `scripts/build-scheduling-fixture.cmd` as well as the research probe, then run `scripts/verify_live_invocation.py`. `expedition33.invoke_proof()` temporarily attaches the scheduling DLL on the verified game thread, calls the fixed native Actor getter through reflection, and verifies hook removal and DLL unload. This is not an arbitrary invocation API.

For scoped native function observation, also build `scripts/build-fixed-observer.cmd`, then run `scripts/verify_live_observer.py`. `expedition33.observe_proof(callback)` observes two real getter calls, restores the UFunction entry, and delivers copied context to Python. Callback exceptions are recorded and isolated. The observer DLL intentionally remains mapped until game exit to keep late-fetched callback pointers valid; event storage is detached and the engine entry restored before success. Restart the game before rebuilding that loaded DLL, or use a new reviewed module version. This is not yet a persistent `sdk.hook` session.
