# Clair Obscur: Expedition 33 — independent Python SDK

Private v0.1 release candidate for the verified Windows Steam build. Our native
runtime independently identifies live Unreal objects and executes supported
engine operations on the game thread. Python runs in a persistent external
controller. No Borderlands offsets or layouts are used as Expedition 33 facts.

The installable release candidate is built with `scripts/package_release_candidate.py`.
Extract its game-root ZIP beside `Sandfall`; normal game launch starts the SDK
and restores saved mod choices after loading a save. All eleven mods are packaged
under `SDK_Mods`. See [installation and restart instructions](docs/INSTALLABLE_RELEASE.md).
The checkout's `launch-sdk.cmd` delegates to the installed SDK using `SDK_GAME_DIR`
or the local, untracked `settings/install-path.txt`.

## Install and start

1. Close the game and any old SDK controller.
2. Extract the release ZIP into the Expedition 33 install folder containing
   `Sandfall`. It adds `SDK`, `SDK_Mods` and the bootstrap DLL under
   `Sandfall/Binaries/Win64`. Resolve any existing loader there before replacing it.
3. Launch the game normally through Steam or `Expedition33_Steam.exe` and load a save.
   The bundled controller starts automatically and restores saved mod choices.
4. Open Pause and select **Mods**. The native console is also available with
   **backtick (`)** on a US keyboard; enter `mods` or `mods ui`.

No separately installed Python, compiler, pip, developer drive or terminal startup
command is required. Keep one SDK controller per game process. User preferences
live under `SDK/settings`; release archives never contain these files.

Use `mods shutdown` in the native console for orderly cleanup. Normal game exit
also closes the controller, and the next normal game launch starts it again.
For a deliberate controller-only restart, run `SDK/launch-sdk.cmd` after shutdown.
Create `SDK/autostart.disabled` to opt out of automatic startup. Never force-unload
the runtime DLL. See [installation details](docs/INSTALLABLE_RELEASE.md).

## Console and mods

Native commands use Unreal's normal command path. Shipping-disabled commands stay
unavailable. Python output, expression results and tracebacks go to the console
and logs under `SDK/logs`.

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

Install trusted `.sdkmod` archives in `SDK_Mods` while the controller is stopped.
At startup the SDK validates them and rebuilds a private `SDK/mods` cache. Do not
edit that cache. Enable or disable mods through the menu or console; choices are
stored in `SDK/settings/management.json` and survive game/SDK restarts. Build an
archive from a source folder containing root `mod.py` with
`scripts/mod_archive.py build SOURCE OUTPUT.sdkmod` in a development checkout.
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
`SDK/settings/E33Introspection`. Read its current `status.json` for the session ID and
operations. Requests must include that session and a future expiry. The development checkout
`scripts/e33_agent.py` and `scripts/e33_introspect.py` provide research clients;
run them using the bundled interpreter with `-I -S -B` and `--help` for syntax.
No generic execute-code endpoint is exposed through that file protocol.

## What is verified

Installable RC3 passed a normal Steam launch with automatic controller startup,
restored all seven previously enabled mods without activation errors, and attached
the native Mods pause entry. Eleven archives passed independent relocation and
integrity checks using the bundled Python. The final visual Pause/Picto check was
stopped by the user's Escape key and remains pending; no visual pass is claimed.

The following table records **earlier v0.1 acceptance**, not exhaustive RC3 coverage.
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

The current release combines Picto editing, Cinematics, Flight, Statistics,
Introspection and SDK Management in one controller. Older numbered native build
scripts remain research history. Use `scripts/build-release-runtime.cmd` and
`scripts/package_release_candidate.py` for the installable release.

### Persistent mod toggles

Enabling or disabling a mod saves its stable identity and desired state in
`SDK/settings/management.json`. Automatic startup waits for a loaded gameplay
context before restoring saved choices. Mounted startup leaves Flight enabled but
waiting for a supported dismounted character. Shutdown and temporary unload do not
erase saved choices; use Disable to stop automatic activation. Activation failures
are logged and retain their preference. Management is protected; Introspection,
Cinematics and Picto Editor default to enabled on a fresh install, while other mods
default to disabled. An explicit saved false overrides optional defaults.

Automated tests cover fresh-loader restoration, explicit disable, archive refresh,
missing folders and identity mismatch. RC3 also restored seven saved enabled mods
in a new game process without manual controller startup.
