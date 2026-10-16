# SDK RC11 and standalone World Builder 0.30.0

RC11 integrates Matt's E33 Mods menu and the native API required by World Builder.
The SDK ZIP contains SDK Management, Introspection Harness and LiveObjectViewer.
World Builder is a separate optional download: extract its ZIP beside `Sandfall`
to install `SDK_Mods/E33WorldBuilder.sdkmod`, then enable it in Pause > Mods.
No second controller or native DLL installation is needed for the mod.

The menu includes inline enable/disable toggles, a text-size slider with Reset,
separate settings and keybind scroll panels, press-a-key rebinding, conflict
reporting, filtering, bulk actions and appearance settings. The native focus
table now supports all 105 reused menu controls across tab switches. The pause
entry attaches before optional mod restoration. Full menu construction still
takes additional time; this release does not claim instant startup.

World Builder's source is in `mods/E33WorldBuilder`. Camera, catalog, scenes,
thumbnail caching and configuration belong to the optional archive. Shared
native ownership, GPU readback, input and widget APIs remain in the SDK runtime.
Maps and preferences remain under `SDK/settings/E33WorldBuilder` when disabled.
No personal maps, caches, user settings or game assets are included in either ZIP.

## Reproduce

From an x64 Visual Studio tools prompt at the repository root:

```bat
scripts\build-release-runtime.cmd
runtime\python.exe scripts\run_regressions.py
runtime\python.exe scripts\package_release_candidate.py dist\sdk-rc11 --version 0.1.0-rc11
runtime\python.exe scripts\package_world_builder.py dist\world-builder-030
```

The embedded Python runtime and bootstrap must first be prepared as documented
in the existing development instructions. Packaging checks the reviewed Python
runtime and notice hashes. The World Builder package can be rebuilt independently
of the SDK ZIP. Optional thumbnail packs can be imported with
`scripts/import_world_builder_thumbnails.py`; they are not needed to load the mod.

## Regression scope

The complete SDK suite and standalone World Builder suite cover archive integrity,
settings, keybind routing/conflicts, menu lifecycle, scrolling models, ownership,
camera controls, scene validation, bulk operations, catalog navigation and native
thumbnail output. Native focus and keybind fixtures exercise tab reuse and input
capture. Live clean-install results are recorded in `RC11_VALIDATION.md`.

Clean-install checks caught and corrected an old runtime path and undersized
ownership limits in the release launcher. World Builder now defers catalog
prewarming while another SDK menu owns focus. Menu warmup failures include a
traceback and retain ownership for orderly cleanup.

World Builder remains experimental. Some registry entries are not loadable in a
given game state; failed thumbnail attempts are recorded and skipped. This is
not a claim that every asset, map, cinematic or gameplay transition is verified.
