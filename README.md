# Clair Obscur: Expedition 33 — independent Python SDK

MIT-licensed SDK **0.1.0-rc23** (release candidate) for the verified Windows Steam build. Our native
runtime independently identifies live Unreal objects and executes supported
engine operations on the game thread. Python runs in a persistent external
controller. No Borderlands offsets or layouts are used as Expedition 33 facts.

The current qualified release is packaged with `scripts/package_rc23.py` from an explicit frozen manifest.
Extract its game-root ZIP beside `Sandfall`; normal game launch starts the SDK
and restores saved mod choices after loading a save. SDK Management,
Introspection Harness and LiveObjectViewer are bundled. Choose optional `.sdkmod` downloads from the
[Mods catalog](mods/README.md), including ContinentFlight, Picto Editor, Statistics,
and Cinematics, plus Asset Creator/Main Character Replacer. Each has its own release. See
[installation and restart instructions](docs/INSTALLABLE_RELEASE.md).
The checkout's `launch-sdk.cmd` delegates to the installed SDK using `SDK_GAME_DIR`
or the local, untracked `settings/install-path.txt`.

## RC23: independent flight playback and stall recovery

[RC23 downloads](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc23)
include native runtime 251 and matching Scene Editor, Cinematics and public mods.
Fly without holding right mouse, play scenes from your chosen flight angle,
and retain pending SDK commands across temporary game-thread stalls without replay.
See [release notes, validation and limits](docs/RELEASE_0.1.0_RC23.md).

## RC19: authored cinematics and scene placement

[RC19 downloads](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc19)
include the current Scene Editor timeline, flight view, whole-scene placement,
Blueprint NPC controls, drag seeking and native runtime 245. Backspace hides
the timeline; numpad movement and Alt fine control position the scene.
See [validation and experimental limits](docs/RELEASE_0.1.0_RC19.md), including
remaining scene-import and character-animation compatibility work.

## RC18: preparation before loading a save

[RC18 downloads and release notes](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc18)
pair the SDK with native runtime210. The title-screen Mods menu stages desired
mod states, options and keybinds before save activation. Gameplay activation
still waits for a loaded world. Keybind panels keep fixed row widgets while
scrolling; owned cleanup and exact object identities remain required.

WorldBuilderMapLoader replaces the legacy E33MapOverlays package. Install only
one map loader and preserve existing user settings/maps. Scene Editor and Enemy
Spawner remain optional packages; Enemy Spawner uses `-` to open its catalog.
See [validation and known limits](docs/RELEASE_0.1.0_RC18.md).

## RC14: keep freecam active when a held prop unloads

[RC14 release notes](docs/RELEASE_0.1.0_RC14.md) cover the verified level-streaming
selection fix. Install the matching SDK and World Builder **0.31.1** downloads.
When the game unloads a held built-in prop, World Builder releases the selection
without stopping freecam. Existing built-in edits may still reset on streaming;
custom-placed props do not participate in level streaming.

## RC13: live duplication and deletion history

[RC13 release notes](docs/RELEASE_0.1.0_RC13.md) cover World Builder **0.31.0**,
its required matching SDK, live duplication previews and compound XYZ offsets,
Delete selection with Alt+Z/Alt+Y history, and F7 returning to the prop catalog.
The prerelease includes separate SDK, mod, thumbnail and source downloads.

## RC12: startup improvements and World Builder recovery

[RC12 release notes](docs/RELEASE_0.1.0_RC12.md) describe the BL4-inspired Mods
layout with E33/World Builder styling: inline enable/disable toggles, search and
filters, bulk actions, a persisted text-size slider, separate settings and keybind
scroll panels, and press-a-key rebinding with conflict reporting. Open it through
**Pause → Mods**. During capture, Escape unbinds; Cancel keeps the existing key.
Text size ranges from 0.75 to 2.75; Reset restores 1.35.

World Builder **0.30.1** is a separate optional mod requiring RC12 or later.
It shares the SDK controller and native runtime. Its maps, camera preferences and
thumbnail cache stay under `SDK/settings/E33WorldBuilder`.

RC12 packages the startup fixes made after the published RC11 ZIP:
bounded widget-construction batches, attachment gated on gameplay and pause UI,
and menu preparation before saved optional mods restore. A fresh-game check measured
widget construction at **2.17 s** (previously 10.60 s) and SDK readiness at **9.06 s**
after the readiness check (previously 17.42 s). The starting gate changed; these
are individual observations, not a guarantee or an instant-start claim.
See [startup validation](docs/STARTUP_MENU_VALIDATION.md). The original RC11 archive remains unchanged. RC12 also improves surface
targeting; World Builder 0.30.1 recovers closed readers so F7/F8 remain usable.

Final RC12 clean-install checks passed for Pause → Mods, text size/reset, Keybinds,
press-a-key rebinding, F7/F8, foreground/rear targeting, drag and console access.
This run measured **2.27 s** construction and **9.29 s** readiness from the gameplay
gate. See [RC12 validation and limitations](docs/RC12_VALIDATION.md).

## Download optional mods

Install [SDK RC12](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc12)
first, then choose the mods you want. These are separate downloads, not bundled
with the SDK; each published Nexus listing declares the SDK requirement.
Older Nexus releases remain available; World Builder requires RC12.

| Mod | Features and limitations |
| --- | --- |
| [**World Builder — EXPERIMENTAL**](https://github.com/mattmab/ClairObscurSDK/releases/tag/world-builder-v0.30.1) | Standalone optional mod for free camera, prop placement, maps, catalog browsing and thumbnails. Requires RC12. |
| [Continent Flight](https://www.nexusmods.com/clairobscurexpedition33/mods/941) | Exploration flight for supported human characters. Dismount Esquie first; experimental traversal support. |
| [Picto Editor](https://www.nexusmods.com/clairobscurexpedition33/mods/942) | Edit supported Picto stats, levels, Lumina costs and mastery. Changes can affect saves. |
| [Statistics](https://www.nexusmods.com/clairobscurexpedition33/mods/943) | View captured damage events and supported battle counters. Not full third-party Statistics DLL parity. |
| [**Cinematics — EXPERIMENTAL**](https://www.nexusmods.com/clairobscurexpedition33/mods/944) | Browse and replay supported cinematics. Contains spoilers; native Travel and Play changes maps and can run story/save transitions, with no manual Stop on that path. Catalog entries are not all verified playable. |
| [**Asset Creator/Main Character Replacer — EXPERIMENTAL**](https://github.com/mattmab/ClairObscurSDK/releases/tag/asset-creator-v0.3.0) | Browse and spawn locally converted Ayane/2B models or replace the current character visually. Requires RC6. Animation is not 1:1; loading needs improvement and meshes may lag. No model assets included. Nexus publication is pending RC6 approval. |
| [**AssetConverter 0.3.0**](https://github.com/mattmab/ClairObscurSDK/releases/download/asset-creator-v0.3.0/AssetConverter-0.3.0.zip) | One-pass local conversion of the documented Ayane FBX and 2B Blender sources. Requires Python 3.13 x64; first run installs pinned dependencies from PyPI. Download models separately. |

The Asset Creator mod and converter are **MIT-licensed code**:
[mod license](mods/CatalogModels/LICENSE), [converter license](tools/asset_converter/LICENSE).
This does not license the separately downloaded models, textures or animations.
See [model sources, conversion commands and installation instructions](mods/CatalogModels/README.txt).

Close the game and controller, then extract each Nexus mod ZIP into the game root
containing `Sandfall`. Leave the inner `SDK_Mods/NAME.sdkmod` archive intact.
Launch the game, load a save, and enable your choices in **Pause → Mods**.
Preserve `SDK/settings` when updating and back up saves before using editors or
experimental replay. Read each mod's installation notes and limitations.
SDKManagement, IntrospectionHarness and LiveObjectViewer are already bundled;
the latter two are developer tools and do not need separate installation.

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
in the SDK log; its default is F6. The native menu's Keybinds page provides a press-a-key
capture prompt: click a binding and press the desired key. Conflicting active bindings are reported and suppressed. Key callbacks
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

RC11 clean-install acceptance covered automatic startup, standalone World Builder
installation, menu navigation, text sizing, independent scrolling with a temporary
20-option/25-keybind fixture, rebinding, catalog thumbnails, prop spawning and
cleanup. See [original RC11 package validation](docs/RC11_VALIDATION.md), including
its archive hashes and limits.

The subsequent startup/construction fixes on `main` passed **1,097 SDK tests and
79 standalone World Builder tests**, plus native fixtures and the release build.
A fresh automatic game launch passed pause → Mods using the held-Escape AutoHotkey
workaround, text resizing, Keybinds navigation/scrolling and console execution.
Press-a-key capture retained Flight's R descend binding. All nine saved enabled
mods restored. See [follow-up measurements and checks](docs/STARTUP_MENU_VALIDATION.md).

The original ZIP and follow-up installed source were tested separately; newer
source results do not recertify the original archive. The latest run did not
repeat the overflowing-options fixture. Other resolutions, controller input,
combat/map-travel coverage and exhaustive BL4 parity remain outside this pass.
Earlier loading-time GPU crashes were not conclusively diagnosed; the fresh
launch with the gameplay readiness gate completed successfully.

Trusted mods share a Python process; lifecycle ownership is not a security
sandbox. Object observations are not GC-pinned engine handles. Use scoped SDK
resources and explicit cleanup. Historical v0.1 evidence remains in
[release convergence](research/RELEASE_CONVERGENCE.md).

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
`src/expedition33/introspection/LICENSE`. Public SDK and optional mod downloads
are linked above; bundled runtime components retain their separate license notices.

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
are logged and retain their preference. Management is protected. Only SDK Management and Introspection Harness start
by default on a fresh installation. LiveObjectViewer is bundled but optional;
separately installed mods require an explicit enable choice. An explicit saved false overrides optional defaults.

Automated tests cover fresh-loader restoration, explicit disable, archive refresh,
missing folders and identity mismatch. The latest follow-up restored nine saved enabled mods
in a fresh game process without manual controller startup.

## Experimental custom models (RC6)

[Asset Creator/Main Character Replacer](mods/CatalogModels/README.txt) offers a model browser, static spawning, and approximate current-character replacement. **Animation is not 1:1; model loading needs improvement and meshes may lag.** Ayane and 2B must be downloaded separately and converted locally. No model assets are bundled. Mod and converter code are MIT; source model rights are separate. [RC6 release notes](docs/RELEASE_0.1.0_RC6.md).
