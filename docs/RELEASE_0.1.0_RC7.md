# SDK 0.1.0-rc7 — World Builder runtime

RC7 supplies the native and Python support for E33 World Builder 0.27.0.
World Builder cannot run on stock RC6. This package is assembled from the
hash-verified RC6 release with an explicit six-file Python overlay and the
World Builder v39 native probe/runtime plus thumbnail worker v2.

The mod and optional neutral thumbnail pack are separate downloads. The SDK
continues to bundle only SDKManagement, IntrospectionHarness and LiveObjectViewer.

## Changes

- Native builder camera, surface picking, scene editing and preview booth.
- Asynchronous GPU picking and full-image background thumbnail readback.
- Native PNG composition worker and reusable capture scene.
- World Builder request validation for operations 20–49.
- Menu capacity raised to 64 controls; larger bounded resource quotas.
- Case-insensitive package/asset basename matching for cooked asset paths.

The image pack contains 5,983 previews from a 6,376-mesh catalog. The remaining
393 entries failed capture/loading and do not have supplied pictures. The pack
includes an importer that validates checksums and the supported executable /
container inventory, then remaps image names to the recipient's cache keys.
Personal maps, map screenshots, preferences, logs and authentication data are
excluded. Images depict game assets and are not covered by the SDK code license.

## Installation

Close the game and controller before upgrading. Extract the SDK archive into
the game root, preserving SDK/settings, SDK_Assets and optional SDK_Mods.
Do not overwrite an unrelated version.dll loader. Put the World Builder archive
in SDK_Mods and enable it through SDK Management after loading an exploration
save. Follow the thumbnail pack README to import the optional images.

Only the verified Windows Steam executable is supported. Native model/hair
capabilities from the development adapter are retained; full character/combat
regression coverage is not claimed. Foreground/map captures still use synchronous
export; background catalog captures use asynchronous readback. Some initial
asset loads can still stall.

## Validation scope

Standalone RC7 manifest/startup check passed. Runtime dependency/notice hashes
passed. 34 World Builder tests and 20 SDK regression tests passed against the
staged SDK. RC7 was installed and the game restarted through Steam; the bootstrap
started its controller automatically. A saved 19-object scene was restored.
The catalog loaded cached neutral images, the 3D booth opened and accepted camera
motion, Escape returned from the booth to the menu, F7 closed the menu and F8
worked with the menu open. Builder and GPU diagnostics reported no errors.
This is a focused fresh-launch check, not every-zone or character regression coverage.

The source bundle includes native code, GPU helpers, Python mod, adapter overlay,
RC6-to-RC7 Python diff, tests and release tools. Build the native components from
an x64 Visual Studio Native Tools prompt using build.cmd and
build_thumbnail_worker.cmd. No developer-specific drive paths are required.
