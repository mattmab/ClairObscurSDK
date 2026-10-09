# Expedition 33 independent Python SDK research

Current development: porting the actual BL4 Introspection Harness. Live roots,
search, generated-class/function/struct schema, selected stored-value inspection,
and snapshot/diff are working through the original core and local-file protocol.
Recursive values and the remaining operations are still in progress.
The experimental `management --retained` host adds verified native calls and
owned object results with the original Harness retain/release/expiry protocol.
See [the port inventory](research/INTROSPECTION_PORT.md). This work does not change
the previously packaged private v0.1 archive.

Status: **live Python object enumeration and interactive in-game Python work**. The independently derived runtime also supports native class and nested type metadata, stored boolean reads, a fixed game-thread reflected invocation, persistent removable observation with Python callbacks, and a trivial mod lifecycle. General calls and object ownership remain limited; this is the private v0.1 development SDK. The reduced whole-image Ghidra pass completed, saved, and reopened successfully; known analyzer warnings are documented.

Primary goal: independently discover the local game's Unreal runtime and build a
Python-facing SDK, culminating in a private v0.1 with verified live object queries,
reflection reads, harmless invocation, removable hooks, and a trivial mod.

See `research/GOAL.md`, `research/MILESTONES.md`, and the topic journals.
Evidence is labeled OBSERVED, PROVEN, INFERRED, HYPOTHESIS, or STALE/DISPROVEN.
No Borderlands offsets or layouts are accepted as Expedition 33 facts.

All new tools, repositories, environments, caches, databases, and outputs live
under `D:\HobbyDevelopment`. Existing installed runtimes may be reused.
Game files are read-only research inputs. No public publishing is authorized.

## Interactive console

Launch the game normally, then run `launch.cmd console` from the checkout or a
verified development bundle. Press backtick (`), without Shift on a US keyboard,
to open the native Unreal console (the engine calls this key Tilde). An optional
additional toggle is available with `launch.cmd console --console-key F10`.
For the introspection harness, use `launch.cmd introspection` instead. Keep its
controller running; the default has no timeout. `--seconds N` is intended for
bounded validation and detaches the console when that interval ends.

Enter native commands such as `stat fps`, or Python commands such as:

```text
py print("Hello World")
py count = 1
py count += 1; count
py sdk.console.execute("stat fps")
py my_mod.some_function()
py help()
```

Python runs in the external controller's persistent session. Output and errors
appear in the native console and SDK log. Closing the controller detaches the
console and removes SDK command registrations. Native Up/Tab handling for
intercepted Python commands is currently unsupported. See DEVELOPMENT.md for
installation, mod commands, lifecycle rules and the tested feature boundaries.

The source checkout also has an experimental native Mods Menu. Start
`launch.cmd management --multi-controls`, then enter `mods ui` in the native
console. `mods ui close`, `mods ui refresh`, and `mods ui status` use the same
SDK Management owner and mod registry as the console commands. Construction
currently takes about five minutes and cleanup is also slow; this is not yet a
release-ready menu. Numeric/text/JSON editors and general keybinds remain pending.
The previously packaged private archive does not include this source feature.

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

For the earlier bounded observation proof, also build `scripts/build-fixed-observer.cmd`, then run `scripts/verify_live_observer.py`. `expedition33.observe_proof(callback)` observes two real getter calls, restores the UFunction entry, and delivers copied context to Python. The persistent API is `sdk.Session().hook(...)`, documented in DEVELOPMENT.md. Callback exceptions are contained. Native callback code intentionally remains mapped until game exit to keep late-fetched pointers valid; removal detaches event storage and restores the engine entry. Exit the game before rebuilding a loaded DLL under the same filename.
