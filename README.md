# Clair Obscur: Expedition 33 — independent Python SDK

Private v0.1 release candidate for the verified Windows Steam build. Our native
runtime independently identifies live Unreal objects and executes supported
engine operations on the game thread. Python runs in a persistent external
controller. No Borderlands offsets or layouts are used as Expedition 33 facts.

The current integrated path is **`launch.cmd management --keybinds`**. It enables
the native Unreal console, persistent Python, the supported Introspection Harness,
mod management, the native UMG menu and configurable mod keys.

## Install and start

1. Extract the complete SDK archive into a writable folder. Keep its directory
   structure intact. Do not copy SDK DLLs into the game's binary directory.
2. Launch Expedition 33 normally through Steam or `Expedition33_Steam.exe`.
3. From the extracted SDK folder run `launch.cmd management --keybinds`.
4. Wait for the console-management-ready message. Press **backtick (`)** without
   Shift on a US keyboard. Unreal calls this key Tilde.
5. Enter `py print("Hello World")`, `mods`, or `mods ui`.

The archive includes CPython 3.13.15 x64 and its license. No separately installed
Python, compiler, pip or developer drive is required. Keep one persistent SDK
controller per game process. The launcher verifies bundled file checksums before
loading the SDK. An optional additional console key can be selected with
`--console-key F10`; backtick remains the normal console key.

To stop the SDK cooperatively, enter:

```text
py my_mod.registry.request_shutdown()
```

Normal game exit also closes the controller. Restart the launcher after restarting
the game. Python variables live for one controller session; key preferences live
across launches. The SDK deliberately does not auto-execute arbitrary saved mods.

## Console and mods

Native commands use Unreal's normal command path. Shipping-disabled commands stay
unavailable. Python output, expression results and tracebacks go to the console
and `logs/sdk.log` beside the launcher.

```text
stat fps
py sdk.console.execute("stat fps")
py counter = 33
py counter += 1; counter
py help()
mods help
mods load KeybindExample
mods select keybind-example
mods enable
mods keys
mods bind count F7
mods unbind count
mods resetkey count
mods disable
mods unload
```

`stat fps` toggles the native FPS display. The example counts physical key presses
in the SDK log; its default is F6. The native menu's Keybinds page provides a key
selector. Conflicting active bindings are reported and suppressed. Key callbacks
are suppressed while the console or SDK menu owns input; they do not consume the
ordinary game key. Single keys are supported, not chords or controller buttons.

Install trusted Python mods as `mods/YourMod/mod.py`, following the bundled
examples. Load/enable explicitly through `mods` or the native menu. Bundled SDK and
example files are checksum-protected; add a new mod folder instead of editing
those files in an immutable release. Settings are in `settings/management.json`.
Boolean/choice options can be changed in the native menu. Use `mods options`,
`mods set OPTION_ID JSON`, and `mods action ACTION_ID [JSON]` for the console path.
Digest-checked reload and staged installation APIs are documented in
[DEVELOPMENT.md](DEVELOPMENT.md) and the [port inventory](research/INTROSPECTION_PORT.md).

## Introspection and agents

The Harness retains the original BL4 Explorer core with Expedition 33 adapters.
It exposes real roots, search, schemas, bounded supported property inspection,
snapshots/diffs, supported calls and retained values. Native scalar POST tracing
is limited to the verified codecs and specimens; full BL4 parity is not claimed.

```text
e33i.status
e33i.roots
py introspection.request({"op": "status"})
```

The controller serves the bounded local-file protocol under
`settings/E33Introspection`. Read its current `status.json` for the session ID and
operations. Requests must include that session and a future expiry. The bundled
`scripts/e33_agent.py` and `scripts/e33_introspect.py` are the client entry points;
run them using the bundled interpreter with `-I -S -B` and `--help` for syntax.
No generic execute-code endpoint is exposed through that file protocol.

## What is verified

The representative integrated acceptance ran from a portable S: extraction in two
fresh game processes, not just the development checkout:

| Capability | Evidence and boundary |
| --- | --- |
| Independent objects/reflection/invocation | Live objects, verified metadata and supported schema/identity-checked calls; arbitrary ABI marshalling is unsupported. |
| Native console and persistent Python | Backtick, native `stat fps`, variables/imports, mod calls, output and contained errors passed. Native Python Up/Tab integration is unavailable. |
| UMG management | Discovery/details/actions/navigation/close passed; first open 4.94s, navigation execution 0.49s on the test machine. First-open margin is narrow. |
| Configurable keys | Physical dispatch, API/UI remapping, conflicts, unbind/unload cleanup, error containment and preference persistence across relaunch passed. |
| Harness | Native-menu live roots action and file-transport PlayerController property inspection passed in the fresh package; broader supported operations have earlier recorded live evidence. |
| Lifecycle | Reload into a fresh mod instance, alias/resource removal, cooperative shutdown, normal game exit and relaunch passed. |
| Portable runtime | Bundled interpreter ran from outside checkout. Game-exit cleanup regression suite: 418 passing tests. |

All integrated live acceptance above was at the **main menu**. Gameplay and map
transitions, arbitrary third-party mods, additional builds, controller input,
native text/numeric/JSON editors, advanced Blueprint traces and exhaustive BL4
feature parity remain unverified or deferred. Trusted mods share a Python process;
lifecycle ownership is not a security sandbox. Do not treat object observations
as GC-pinned engine handles. Use scoped SDK resources and explicit cleanup.

Verified target: UE 5.4.4, Steam app1903340/build23765773,
`SandFall-Win64-Shipping.exe` SHA256:
`218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618`.
Unknown executable fingerprints are rejected rather than tried with stock offsets.

## Development and provenance

[Release convergence](research/RELEASE_CONVERGENCE.md) records the frozen v0.1
scope, exact acceptance artifacts, remaining release gates and deferred v0.2 work.
[DEVELOPMENT.md](DEVELOPMENT.md) contains API and historical runtime notes.
Older `--reflected` through `--traces` modes and native research fixtures are
retained for reproducibility; they are not the recommended integrated launcher.
Historical archive results do not certify newer runtime modes.

The Harness port preserves its upstream MIT license in
`src/expedition33/introspection/LICENSE`. The repository and release artifacts must
remain private. No public publication is authorized.
