# Optional mods

The SDK installer includes **SDK Management**, **Introspection Harness** and
**LiveObjectViewer** (SDK RC5 or newer). Enable the viewer in Pause → Mods.
Mods below are separate downloads with independent release tags and MIT licenses.
They use the SDK runtime; do not install separate controllers.

The current SDK release is **RC18**. [Download the SDK and current mod packages](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc18).
World Builder **0.32.1** adds P (play from camera), H (hide/show HUD), and F7
construction feedback. [Map Travel 0.2.2](MapTravel/README.txt) opens grouped map
choices and uses normal entrance transitions. Both require the matching RC18 SDK.

| Mod | Download / release | Purpose |
| --- | --- | --- |
| World Builder — EXPERIMENTAL | [0.30.1](https://github.com/mattmab/ClairObscurSDK/releases/tag/world-builder-v0.30.1) | RC12 required. Free camera, prop catalog, placement and saved maps. |
| WorldBuilder Map Loader | [RC18](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc18) | Normal-gameplay saved maps; replaces E33MapOverlays. Install only one map loader. |
| Scene Editor | [RC18](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc18) | Owned scene actors, camera, animation, audio and timeline editing. |
| Enemy Spawner | [RC18](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc18) | Original and isolated encounter routes; `-` opens the catalog. |
| ContinentFlight | [0.1.0-rc1](https://github.com/mattmab/ClairObscurSDK/releases/tag/mod-continentflight-v0.1.0-rc1) | Exploration flight |
| Picto Editor | [0.1.0-rc1](https://github.com/mattmab/ClairObscurSDK/releases/tag/mod-pictoeditor-v0.1.0-rc1) | Stock-menu Picto editing and saved overrides |
| Statistics | [0.1.0-rc1](https://github.com/mattmab/ClairObscurSDK/releases/tag/mod-statistics-v0.1.0-rc1) | Combat records and verified summary counters |
| Cinematics | [0.1.0-rc1](https://github.com/mattmab/ClairObscurSDK/releases/tag/mod-cinematics-v0.1.0-rc1) | Build-specific experimental cinematic replay |
| Asset Creator/Main Character Replacer — EXPERIMENTAL | [0.3.0 mod and converter](https://github.com/mattmab/ClairObscurSDK/releases/tag/asset-creator-v0.3.0) | RC6 required. Local model browser and approximate character replacement. No model assets included; animation is not 1:1 and meshes may lag. |

## Install

1. Install SDK **0.1.0-rc4 or newer** for the supported game build; Asset Creator requires **RC6**; World Builder requires **RC11**.
2. Close the game/controller. Download the mod's `.sdkmod` release asset and copy
   it directly into the game's `SDK_Mods` folder. Do not extract the archive.
   For a game-root ZIP such as World Builder's, extract the ZIP beside `Sandfall`;
   keep the inner `SDK_Mods/E33WorldBuilder.sdkmod` intact.
3. Launch normally, load your save, then open **Pause → Mods** and enable the mod.
   Enable choices and settings persist across restarts.

Update by replacing that archive while stopped. Remove by disabling first and
removing the archive while stopped. Existing user settings are preserved.
Only install trusted code: `.sdkmod` archives are not a sandbox.

Sources remain in the named subfolders here. Shared native/reflection support
remains in the SDK; optional entry points and resources are not in the SDK ZIP.
Example mods remain source-only development references. LiveObjectViewer is
bundled with the SDK because it is a runtime inspection tool.
Each mod can be released independently with `scripts/mod_archive.py build`.
These are release candidates. Feature-specific limits and live evidence are in
each mod's README and the repository research documents; publication does not
imply every game state or cinematic has been validated.

## Asset Creator/Main Character Replacer — EXPERIMENTAL

Requires SDK RC6. [Download and conversion instructions](CatalogModels/README.txt). No Ayane or 2B assets are included. Animation is not 1:1, loading needs improvement, and meshes may lag. MIT applies to our code only. The archive retains `CatalogModels.sdkmod` for settings compatibility.

[Download mod and converter 0.3.0](https://github.com/mattmab/ClairObscurSDK/releases/tag/asset-creator-v0.3.0).
Both the [mod](CatalogModels/LICENSE) and [converter](../tools/asset_converter/LICENSE) code are MIT licensed; model rights remain separate. Nexus publication is on hold pending SDK RC6 approval.
