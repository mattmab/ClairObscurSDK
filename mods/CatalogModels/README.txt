Asset Creator/Main Character Replacer 0.3.0 — EXPERIMENTAL

Requires ClairObscurSDK 0.1.0-rc6 (mesh-v27). Public RC5 is not compatible.
Code and converter: MIT. Models, textures and animations are NOT included and
are NOT licensed under our MIT license. Download them from their original pages
and follow the respective authors' terms. This is an unofficial SDK mod.

MODEL DOWNLOADS
Ayane by NekoPixil (Ninja Gaiden 2 Black):
https://www.deviantart.com/nekopixil/art/FBX-Ayane-Ninja-Gaiden-2-Black-DL-1153722246
Download the archive through the author's page. Extract it using 7-Zip, keeping
Materials and Textures alongside Fbx. Choose Ninja Gaiden Sigma 2 Outfit/Fbx/Ayane.fbx.

2B:
https://open3dlab.com/project/4f29c82f-b638-41c5-998c-0039d456786d/
Use 2B_Rip_v1_6_R.blend from this project. The previously suggested Sketchfab
model is NOT the tested source. Do not substitute a different model version.

ONE-PASS LOCAL CONVERSION
Install Python 3.13 (64-bit) with the Windows Python launcher. Extract the
AssetConverter download to a writable folder with space for its Blender Python
runtime. Close/disable this mod before converting or replacing an asset.
From PowerShell in that folder, run ONE of these commands (replace paths):

py -3.13 run.py ayane "D:\Downloads\Ayane (Ninja Gaiden 2 Black)\Ninja Gaiden Σ 2 Outfit\Fbx\Ayane.fbx" --game "S:\SteamLibrary\steamapps\common\Expedition 33"
py -3.13 run.py 2b "D:\Downloads\2B_Rip_v1_6_R.blend" --game "S:\SteamLibrary\steamapps\common\Expedition 33"

First run installs pinned bpy, NumPy and Pillow into a local converter environment
from PyPI. They are separate dependencies under their own licenses, not bundled
in the mod. Later runs reuse that environment. The converter does not download
models. Blender file auto-execution is disabled. Only use trusted source files.
Output goes to <game>\SDK_Assets\ayane or 2b, outside disposable SDK mod caches.
Successful reconversion retains the old output in a uniquely named backup folder.
Do not distribute these generated assets with the mod.

INSTALL AND USE
Upgrade the SDK with the game closed, preserving SDK/settings and SDK_Assets.
Copy CatalogModels.sdkmod into <game>\SDK_Mods. The archive keeps its old filename
and internal ID to preserve existing enabled settings; the displayed name is
Asset Creator/Main Character Replacer. Do not install a second renamed copy.
Enable it in Pause > Mods, then choose Browse model catalog. Both models are listed;
unconverted models show download/conversion guidance. Select a model and choose
Spawn on ground (static) or Replace current character (animated approximation).
Destroy current model restores the original. Disable/disconnect releases ownership.
Reopen the browser after conversion to refresh availability.
Console: catalog open; catalog replace ayane; catalog replace 2b; catalog destroy.
No keybind is installed by this mod. The game retains its normal character-switch key.

LIMITATIONS — READ BEFORE INSTALLING
Animation is NOT 1:1. Existing game skeletons drive reduced body-bone mappings;
proportions, fingers, facial animation, cloth and hair do not match the original rig.
Model loading still requires improvement. Meshes may lag or jitter during animation,
character switches, combat transitions or travel. Initial preparation is not instant.
Monoco's different proportions are particularly approximate. The mod preserves
original gameplay actors, collision and animation logic; it is a visual replacement.
It does not import a native Unreal SkeletalMesh. Static props have no collision.
Materials approximate the source. Hair tint is simplified; some transparent eye,
eyebrow and eyelash overlays are omitted for Ayane. Original shader parity is absent.
User testing confirmed the local candidates; not every character/animation/zone is
individually verified. A failed/unsupported binding should restore the original.
Replacement selection is not automatically reapplied after controller restart.

DEVELOPER OPTIONAL CATALOG
E33_NORMALIZED_CATALOG can point to a separately prepared normalized-asset/1
catalog. No Borderlands installation or catalog is required for the two downloads.
Unrelated catalog entries are not claimed compatible. Quarantined entries stay excluded.

AI Developed. Report issues with SDK version, model source version and reproduction
steps. Never upload model assets or private settings as part of an issue report.
