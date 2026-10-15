# SDK 0.1.0-rc10 - Faster World Builder menu

World Builder **0.30.0** ships with the matching **v53 SDK adapter**. Install both packages for batched thumbnail updates.

## Changes

- Faster initial catalog discovery using the saved asset paths, without saving live game-object identities.
- Menu and camera HUD prewarming, smaller UI planning catalogs, and fewer redundant engine calls.
- Reuses a scoped read-only SDK worker instead of starting one on every menu poll.
- Folder navigation updates immediately; visible thumbnails load incrementally in small groups. Returning to cached folders uses batched image updates.
- Bounded texture retention and cancellation of obsolete page queues. Actor indexing refreshes on demand.
- Retains RC9 camera settings, click-to-copy, Alt+Z undo, Alt+Y redo, gallery floors, and tracked map saving/loading.

## Measured results

On the tested machine, repeated folder navigation improved from **1.8-2.5 seconds to roughly 0.2-0.4 seconds**. Warm menu reopening measured about **0.9 seconds**; first opening after prewarming about **2.9 seconds**. Startup prewarming still takes approximately **6-8 seconds**. Results vary with hardware and other enabled mods; a single cold Unreal asset load can still stall.

## Downloads and installation

Download **Expedition33-SDK-0.1.0-rc10.zip** and **E33WorldBuilder-0.30.0-rc10.zip**. Optional attachments provide thumbnails and source. SHA256SUMS.txt and VALIDATION.txt are included.

Close the game and SDK controller before upgrading. Extract the SDK into the game folder, preserving settings, SDK_Assets and optional SDK_Mods. Do not overwrite an unrelated version.dll loader. Put E33WorldBuilder.sdkmod in SDK_Mods. The thumbnail ZIP includes its importer and installation instructions; existing local images are preserved.

The thumbnail pack contains **5,991 previews for 6,376 catalog meshes**. Game imagery is not covered by the SDK code license. Personal scenes, settings, screenshots and logs are excluded.

## Validation

78 mod/UI tests and 11 SDK lease tests passed during implementation. Native v53 built with /W4 /WX. Live checks covered folder navigation, image-cache rollover, camera/menu toggling and restoration of all **4,992 saved gallery objects**, with every object record unchanged. A fresh game launch tested the v53 catalog changes; the final HUD/reader refinements were additionally tested after SDK restart in that game. Full combat regression is not claimed.

Windows Steam build 23765773 is the supported target. Landscapes, foliage instances and some translucent surfaces remain unselectable. No enemy controls are included. Save your map before leaving the session.
