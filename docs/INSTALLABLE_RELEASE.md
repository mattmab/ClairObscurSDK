# Expedition 33 SDK — installable release candidate

This package is SDK **0.1.0-rc12**. See `docs/RELEASE_0.1.0_RC12.md` in the
source repository for release notes.

This candidate supports the verified Windows Steam executable with SHA-256
`218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618`.
Other builds fail the native fingerprint check. This is a release candidate,
not a claim that every cinematic or mod operation is individually live tested.

## Install and start

Close the game and the old SDK controller. Extract the ZIP into the game folder
containing `Sandfall`, so `SDK` and `SDK_Mods` sit beside it. If
`Sandfall/Binaries/Win64/version.dll` already exists, resolve the other loader
installation first; do not overwrite an unidentified DLL. This package contains
an independently built Windows export forwarder, not CineReplay's supplied DLL.

Start the game normally and load a save. The bootstrap launches bundled Python
in the background, waits for the game runtime, and attaches the SDK. Open Pause
and select Mods, or use the native console's `mods ui` command. The SDK does not
require a terminal command on normal game startup.

The RC12 Mods menu includes inline enable toggles, a text-size slider (Reset:
1.35), separate settings/keybind scroll panels, filters and conflict reporting.
Choose Rebind and press a key; Escape unbinds and Cancel preserves the old key.
Single keyboard keys are supported. Normal mod key callbacks are suppressed
while the console or SDK menu owns input.

RC12 waits for a gameplay pawn and pause UI before attaching,
prepare the menu before optional mods, and defer further saved mod activation
while paused. Close pause to let remaining saved mods finish loading. These changes include the post-RC11 startup fixes; timings and test scope are
recorded in the repository's startup validation document.

`SDK/logs/controller.log` records startup and runtime activity.
`SDK/logs/startup-error.log` records startup failures. A second controller for the
same installed SDK is rejected by an operating-system file lock.

## Mods and settings

SDKManagement, IntrospectionHarness and LiveObjectViewer are bundled in `SDK_Mods`.
Enable LiveObjectViewer in Pause → Mods, then choose **Open Live Object Viewer**
or enter `lov` in the native console. Existing saved enable choices are preserved.
Download optional mods separately from the repository's Mods catalog and releases.
World Builder 0.30.1 requires RC12 or later and is a separate optional download.
Extract its ZIP beside `Sandfall` and enable World Builder in Pause → Mods.
It needs no second controller or native DLL; preserve `SDK/settings/E33WorldBuilder`
for maps, camera preferences and thumbnail caches.
Add or replace trusted mod
archives there while the controller is stopped. They are validated and extracted
into a generated `SDK/mods` cache at startup. Do not edit the generated cache.
Archives execute trusted Python code; they are not sandboxed or digitally signed.
Limits: 64 archives, 32 MiB per archive, 64 MiB expanded per archive, 256 MiB total.

Management starts first. On a fresh installation only the Introspection Harness
and Management are enabled by default. Optional mods must be installed and enabled
through the Mods menu. Explicit enable/disable choices survive restarts in
`SDK/settings/management.json`; individual mod settings also live in `SDK/settings`.
The ZIP contains no user settings and does not overwrite them during upgrades.
Upgrading does not delete optional archives installed by an older bundled release.
To remove one, disable it, shut down the SDK/game, and remove its `.sdkmod` from
`SDK_Mods`; keep `SDK/settings` to preserve preferences. No pip installation is needed.
Failed activation is logged; the saved desired state is retained for diagnosis.

## Stop, restart, or disable autostart

Use `mods shutdown` in the native console to request orderly controller cleanup.
To restart without restarting the game, run `SDK/launch-sdk.cmd` after shutdown
finishes. `launch-cinematics.cmd` is an alias. To disable automatic startup,
create an empty file named `SDK/autostart.disabled` before launching the game.
Do not forcibly unload the runtime DLL; an inactive mapped module may remain
until game exit. Cleanup failures are not permission to attach another controller.

The authenticated structured local command server is optional. Create
`SDK/developer-commands.enabled` before game startup, or manually pass `--commands`.
It exposes status and orderly shutdown, never unrestricted socket Python execution.
Connection credentials are generated locally under `SDK/settings/controller`.

## Verification and known limits

Run `SDK/launch-sdk.cmd --check` for an offline integrity check of the SDK and
original bundled archives. Modified mod archives intentionally fail this strict
distribution check, but normal startup accepts structurally valid replacements.
Play/Stop and cleanup support remain adapter-specific. The 83 original-action
cinematics are mapped, not all individually verified, and do not expose safe
manual Stop. No save files or third-party game assets are included in this ZIP.
Fresh-install automatic startup and gameplay regression results must be recorded
separately from package integrity and build results.
