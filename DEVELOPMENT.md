# Private development SDK

## Interactive native console

Run `launch.cmd console` after the game reaches its main menu. Press the existing
Tilde/grave key once for the prompt, twice for expanded output, and again to close.
The controller remains external and must stay running; Ctrl+C closes its session.
`launch.cmd console --seconds 120` is a bounded example run.

Try `stat fps` (repeat to turn it off), `py print("Hello World")`, `py help()`,
`py count = 1`, `py count += 1; count`, `py sdk.console.execute("stat fps")`,
`py my_mod.some_function()`, or `sdk.hello your text`. Variables, imports and the
loaded ConsoleExample instance persist until the controller session ends.
Output, expression values and tracebacks appear in the native console and SDK log.

Mods can register a callback with `session.console.register("mod.command", callback,
owner=self)`; it receives the argument string. Remove the returned handle during
disable, or use `remove_owner(self)`. Session close clears every registration.
Choose a mod-specific command name: registered names intentionally intercept that
name before Unreal. Updating registrations discards already-queued SDK commands
so they cannot reach a replacement owner. `ModLoader.enable(name, console=True)`
exposes the enabled mod instance as `my_mod` and `ModLoader.poll(name)` services
its console and existing observer callbacks. Standalone sessions call
`session.console.poll()` explicitly on their owning Python thread.

Limits: one controller/session and one enabled mod; one-line Python,4096 UTF-16
units per input,16 queued commands,32768 output characters. Long Python work can
block the controller (not the game loop); queue overflow rejects new SDK commands.
Only native commands included and enabled by this shipping build can work.
Native history remains available for Unreal commands. Python/custom history is
available through `sdk.console.history` and lexical suggestions through
`sdk.console.complete(prefix)`; native Up/Tab integration for these is unsupported.
The game's existing Tilde mapping is verified. Add an SDK toggle with
`launch.cmd console --console-key F10`, or call
`session.console.set_toggle_key("F10")` after enabling the console. F1 through F12
are accepted; `None` removes the additional toggle. F10 opening, closing and
reopening were tested live. Tilde remains available. Modified key chords are
ignored, and the extra binding ends on console detach/session close.
No arbitrary stock Unreal layouts or missing shipping commands are supplied.
See research/CONSOLE.md for target-specific evidence and remaining validation.

This is an independently implemented, build-specific Windows x64 research SDK.
It supports Steam build 23765773, shipping SHA256
`218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618`.
An unknown executable fails before native attachment. No game files are installed
or replaced. Use the locally owned offline game, launched normally through Steam.

## Run a development bundle

Extract the zip into a new directory under `D:\HobbyDevelopment`. Keep its `src`,
`build`, `mods`, `scripts` and manifest together. The bundle contains our native
binaries and source, not the game, Ghidra databases, dumps, credentials or Python.

This machine's interpreter is pinned to CPython 3.13.15 at
`D:\HobbyDevelopment\Python\expedition33-tools\Scripts\python.exe`.
`launch.cmd` verifies that version and uses `-I -S -B`: no user site, startup site
hooks, environment search-path overrides or bytecode writes. It inserts only this
bundle's source path and verifies the import came from the bundle. Standard
library modules are the only Python runtime dependencies.

Launch the game and wait for its main menu. From a terminal in the extracted folder:

```bat
launch.cmd objects
launch.cmd example
launch.cmd smoke
```

`objects` enumerates live objects and prints the first twenty. `example` loads,
enables, disables and unloads ExampleMod. `smoke` additionally reads Actor
reflection and stored bools. Logs rotate under the extracted folder's `logs`.
The manifest detects accidental bundle changes; it is not a signed trust boundary.
For editing mods or source, use a source checkout rather than modifying a verified
bundle. The launcher also works from the checkout, which has no manifest.

## Public API and ownership

```python
import expedition33
from expedition33 import sdk

for obj in expedition33.objects():
    print(obj.name, obj.class_name)

with sdk.Session() as session:
    actor = session.find_object('Default__Actor')
    with session.hook(actor, 'Actor.IsActorBeingDestroyed', print):
        print(session.call(actor, 'Actor.IsActorBeingDestroyed'))
        session.poll()
```

Snapshots do not own Unreal objects. The session validates the fixed target's
index/serial, class/name, permanent registry prefix, dispatch code and GameThread.
Only this getter/default object is supported for calls/hooks. General parameters,
arbitrary objects, property writes, and synchronous event cancellation are absent.
Class metadata and stored bool reads have their separate read-only APIs.

Callbacks run on the external Python owner thread during `poll`, after the native
call returned. A failing callback is disabled and its text diagnostic retained in
`session.failures`; another subscriber continues. Buffers hold 64 native events
and report overflow through `session.dropped_events`. Manage each session/loader
on its creating Python thread. Close explicitly or use context managers.

The native observer DLL remains pinned until the game exits to protect a callback
pointer fetched just before removal. Removal restores the entry and detaches event
storage; it does not unload that code. Exit the game before rebuilding/replacing
the same loaded DLL. Controller death requests cleanup on the GameThread. Normal
game exit with an active observer and subsequent relaunch have been tested.

Mods are trusted local Python, not sandboxed. `ModLoader` discovers `Name/mod.py`;
the module defines `Mod.enable(session)` and `Mod.disable()`. The loader closes its
owned session even when lifecycle code raises. One enabled mod is supported at a
time. Imports or threads created by a mod are its own responsibility.

## Rebuild on this machine

Use the existing x64 MSVC toolchain at `D:\HobbyDevelopment\Tools\VSBuildTools`.
Build scripts keep outputs/temp on D:. Windows SDK 10.0.26100.0 is the documented
system-installed dependency; no extra instrumentation framework is required.
The existing isolated Python environment is 3.13.15. To recreate it, use an
installed CPython 3.13.15 to run `python -m venv D:\HobbyDevelopment\Python\expedition33-tools`;
the bundle launcher itself needs no pip packages. Ghidra research tooling has
separate dependencies recorded in `research/GHIDRA_MCP.md`.

```powershell
. .\scripts\project-environment.ps1
cmd /c scripts\build-research-probe.cmd
cmd /c scripts\build-runtime-session.cmd
cmd /c scripts\build-scheduling-fixture.cmd
cmd /c scripts\build-fixed-observer.cmd
python -m pip install --no-build-isolation -e .
python -m unittest discover -s tests -v
python scripts\verify_compatibility.py
python scripts\verify_live_enumeration.py
python scripts\verify_live_reflection.py
python scripts\verify_live_bools.py
python scripts\verify_live_sdk.py
python scripts\verify_live_mod.py
python scripts\package_dev.py
```

The compatibility verifier uses the preserved analysis input on D: and alters only
a build fixture copy. Live verifiers require the supported running game and do not
fall back to saved dumps. `verify_game_exit.py` arms a hook and waits for normal
GUI quit; run it only when deliberately testing shutdown. Research scripts write
local ignored evidence. Ghidra autoanalysis completion and broader research remain
tracked separately; a development candidate is not a completed v0.1 release.
