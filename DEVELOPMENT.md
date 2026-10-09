# Private development SDK

## v0.1 feature checklist

All live results below apply only to the recorded executable fingerprint.

| Capability | Implementation and validation |
| --- | --- |
| Live Unreal object/name enumeration | Implemented; repeatedly tested in the real game and isolated bundles. |
| Native class/property/function metadata | Implemented and live-tested; nested struct/enum names and array element descriptors included. |
| Property values | v0.1 stored booleans live-tested. Current checkout adds bounded stored scalars/strings/references, selected dynamic arrays and reflected structs. Scalar/array reader deployed; newer struct/inner-schema candidate live-tested separately. Writes and native value ownership remain unsupported. See research/INTROSPECTION_PORT.md. |
| Reflected calls and persistent observation | Implemented and live-tested for the fixed default Actor getter; arbitrary functions unsupported. |
| Python mod lifecycle | Original single-mod lifecycle live-tested. Shared scopes, console load/enable/action/unload/reload, integrated startup and orderly controller restart tested live. Game relaunch with the integrated host remains pending. |
| Native Unreal console UI | Constructed and attached through verified engine paths; Tilde open/close/reopen tested. |
| Unreal commands | Normal engine path preserved; supported diagnostic commands and CVars tested. Shipping-disabled commands remain unavailable. |
| In-game persistent Python | `py` dispatch, imports/variables, SDK/mod calls, output, expression results and tracebacks implemented and live-tested. |
| Mod console commands | Registration, dispatch, explicit removal and owner/session cleanup implemented and live-tested. |
| Configurable toggle | Additional F1-F12 binding implemented; F10 tested, including removal, shutdown and relaunch. |
| History/autocomplete | Python dispatcher history and lexical completion APIs implemented; native Up/Tab integration for intercepted commands unsupported. |
| Disconnect/relaunch | Normal close, controller death, game shutdown and packaged operation after relaunch tested. |
| Gameplay/map transitions | Not validated; current live console/relationship evidence is from the main menu. |
| Private v0.1 | Functional release criteria passed; package verification is recorded in research/MILESTONES.md. The recovered Ghidra research pass is tracked separately. |
| Unified management (current checkout) | Registry, typed settings/actions and console menu implemented; console lifecycle/setting restoration live-tested. Native UMG and general keybinds pending. Not included in the existing v0.1 archive. |

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
exposes the first available mod instance as `my_mod` without overwriting an existing
binding. Use mod-specific `console.expose` names for additional mods.
`ModLoader.poll()` drains the shared transport once and polls all enabled mods;
`poll(name)` selects one mod's optional pump. Standalone sessions call
`session.console.poll()` explicitly on their owning Python thread.

Current checkout: one controller/session shared by enabled mod resource scopes.
The immutable v0.1 archive retains its original one-enabled-mod limit.
Console limits: one-line Python,4096 UTF-16
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

In the current loader, `enable(session)` receives a mod-owned resource scope with
find_object/call/hook/poll and scoped console registration/output methods. Disabling
the mod removes its hooks, commands and unchanged exposed namespace bindings even
if the mod forgets cleanup. A closed scope rejects calls; it does not close other
mods' shared transport. The last enabled mod's cleanup closes the underlying
session. Console attachment and toggle-key configuration belong to the controller,
not individual mod scopes. Trusted Python references copied by a user are not
revocable sandbox handles. Full multi-mod reload/relaunch validation is pending.

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
owned session even when lifecycle code raises. The original v0.1 archive supports
one enabled mod; the current checkout shares one session across mod scopes.
Imports or threads created by a mod are its own responsibility.

## Shared management API (current checkout)

`launch.cmd management` starts SDKManagement and IntrospectionHarness on one
loader. Integrated startup, console actions, orderly shutdown and controller
restart have been tested in the same live game process. Game relaunch is pending.
Do not start a second controller while one already owns the game attachment.

To stop this host cleanly, enter `mods select sdk.management`, then
`mods action shutdown`. The callback returns before the launcher exits its loop
and closes mod scopes and transport. Custom hosts must honor
`ModLoader.stop_requested`; requesting a stop alone does not close resources.

The menu uses `mods` to list loaded mods and installed folders. Every navigation
command starts with `mods`, so normal Unreal and `py` input keeps its routing:

```text
mods select sdk.introspection
mods actions
mods action status
mods action request {"op":"roots"}
mods back
mods load ManagementExample
mods select example.management
mods enable
mods set label "My observation"
mods action observe
mods disable
mods unload
mods quit
```

`mods help` lists commands; `mods options` shows values, types, bounds and defaults.
Use `mods reset OPTION_ID` to restore a default. `load` imports trusted local
Python to register metadata; it does not enable the mod. SDKManagement is protected
from menu disable/unload so recovery remains available. UMG and keybind registration,
capture, conflict handling and remapping are not implemented yet.

A mod can supply one definition for all management frontends:

```python
from expedition33.management import ModDefinition, Option, Action

class Mod:
    def management(self):
        return ModDefinition(
            'my_mod', 'My Mod', description='Example metadata', version='1.0',
            options=(Option('verbose', 'Verbose logging', 'bool', False,
                            on_change=self.set_verbose),),
            actions=(Action('status', 'Show status', self.status),))

    def enable(self, session):
        self.session = session

    def set_verbose(self, value):
        self.verbose = value

    def status(self, argument):
        return {'verbose': self.verbose}

    def disable(self):
        self.session = None
```

Options support `bool`, `int`, `float`, `choice` and `text`; numeric options accept
minimum/maximum and choices use a tuple of scalar values. IDs must be stable
lowercase identifiers. Saved option callbacks run after `enable`. Actions take
one JSON-compatible argument (`None` when omitted), require an enabled mod and run
on the external controller thread. Use the supplied session for engine operations.
Grouped/hidden options and UI widgets are pending.

Management preferences use `settings/management.json`, a versioned store with
atomic replacement and previous-generation recovery. Edits persist before runtime
application. If a callback fails, the error reports that the preference was saved
but could not be applied; there is no automatic retry or rollback claim. Disk
failure prevents the callback. Disabled mods receive their saved settings on next
enable. Enabled preferences are not automatically restored at startup yet.

Other frontends use `session.mods` (or `loader.registry`), obtain a selection with
`select(mod_id)`, then call `view`, `option`, `set_option`, `invoke` or `set_enabled`.
Views are copies. Lifecycle changes invalidate old selections; refresh them rather
than retrying an old queued action. Unload removes definitions/callbacks. Resource
scopes remove native hooks and console registrations; trusted mods must still stop
their own threads and external work. See `research/MANAGEMENT_PORT.md` for the live
evidence and remaining acceptance gates.

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
local ignored evidence. The reduced Ghidra pass completed and passed save/reopen checks; broader research remains
tracked separately. The private v0.1 release covers the validated functionality
and explicit boundaries above; it does not claim exhaustive binary analysis.
# Experimental invocation candidate (2026-10-09)

`scripts/build-invocation-candidate.cmd` builds a separate v6 controller/DLL;
it never overwrites the default v5 host. `scripts/test-invocation-packet.cmd`
runs18 native packet checks and compiles default v5 paths with /W4 /WX without
replacing their deployed files. The Python suite contains87 passing tests.
`scripts/verify_live_reflected_call.py` passed the live read-only getter and two
pre-dispatch rejection cases; only run it after cooperative shutdown of any
existing SDK host, and restore the persistent host afterward. The v6 DLL is
pinned until game exit, so do not rebuild over it while that game is running.

The candidate is not enabled by the public Session.call/Harness invoke APIs and
is not in the existing private v0.1 ZIP. Native UMG, arbitrary key dispatch,
native value ownership, full harness parity and game-relaunch validation remain
open. Details and evidence references are in research/INTROSPECTION_PORT.md.
