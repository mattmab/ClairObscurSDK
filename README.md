# Expedition 33 independent Python SDK research

Status: **live Python object enumeration works**. Native class metadata and stored boolean reads also work. Invocation, hooks, broader reflection, and the complete SDK remain in development.

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
