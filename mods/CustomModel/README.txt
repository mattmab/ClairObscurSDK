Custom Model — Supply Crate 0.1.0 experimental

Requires the Expedition 33 mesh-v7 SDK development candidate (mesh_protocol=3).
Stock RC5 cannot load custom geometry. This mod fails enable cleanly on RC5.

An original static supply-crate model loaded from OBJ, with UVs and an original
PNG texture imported by the game. Uses one procedural mesh section and the
game's ImagePlate surface material. This initial preview material can appear dark.

Controls: model spawn / model destroy / model status in the SDK console.
Also exposes Spawn, Destroy and Status actions to SDK management.
Spawn while on foot in exploration. One crate at a time; collision is disabled.
The crate is temporary and must be spawned again after travel. Disable destroys
it. Native disconnect cleanup retains ownership even if Python stops.

Bounded OBJ subset: triangles/quads, positive v/vt/vn indices, 256 vertices and
768 triangle indices. No skeletal animation, physics, arbitrary material-file
loading, or multiple texture slots. The example PNG is 128x128 RGB.

Installation on a compatible SDK: place CustomModel.sdkmod in SDK_Mods and
enable Custom Model. For the isolated development test use
scripts/run_custom_model_candidate.py --sdk-root <installed SDK directory>.
Stop other SDK controllers first. Do not replace a release runtime piecemeal.

Model, texture, parser and mod are original MIT-licensed work. The design follows
the user's BL4AssetLibrary static-model workflow; no BL4 binaries or game assets
are redistributed. Engine material assets remain in the installed game.
Live validation results are recorded separately in research/CUSTOM_MODEL_TEST.txt.
