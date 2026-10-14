# SDK 0.1.0-rc6 — experimental custom model runtime

RC6 adds the native procedural-mesh and pose-following runtime required by
**Asset Creator/Main Character Replacer 0.3.0**. Public RC5 cannot run this mod.
The mod is an optional separate download; SDKManagement, IntrospectionHarness
and LiveObjectViewer remain bundled developer/management tools.

**EXPERIMENTAL: animation is not 1:1. Model loading still requires improvement,
and meshes may lag or jitter.** Reduced body-bone mappings approximate current
character animations; facial/finger motion, cloth, hair, unusual proportions and
original material behavior are not fully reproduced. Combat and exploration
candidate testing does not establish every-character/every-zone compatibility.

Ayane and 2B assets are **not included**, either in the SDK, mod or converter.
Download each from its original author page and run the separate local converter.
See [the mod instructions](https://github.com/mattmab/ClairObscurSDK/blob/main/mods/CatalogModels/README.txt).
The correct 2B source is Open3DLab, not the previously suggested Sketchfab model.
Converted data stays under `SDK_Assets`, outside replaceable mod caches.

Close the game and controller before upgrading. Extract into the game root and
preserve `SDK/settings`, `SDK_Assets` and optional `SDK_Mods` archives. Do not
overwrite an unrelated `version.dll` loader. Only the verified Windows Steam
executable is supported; other builds, storefronts and Proton are unverified.

Native mesh-v27 built with MSVC `/W4 /WX`. Regression and archive validation
results accompany the release preparation record. User testing confirmed the
local model candidates, including Ayane's corrected ground-level root. New
converter outputs are separately checked; this is not a stability guarantee.

First-party SDK, mod and converter code is MIT. Third-party runtime dependencies
retain their separate notices. Neither MIT nor this release grants rights to
the separately downloaded models. The converter installs bpy, NumPy and Pillow
locally from PyPI; they are not bundled or relicensed. Unofficial and AI Developed.
