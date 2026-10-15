# SDK 0.1.0-rc8 — World Builder bulk spawning

Requires World Builder **0.28.0** and the included **v42 native adapter**. Stock RC7 cannot run this version of the mod.

- Native batched static-mesh spawning and deletion, with bounded work between game frames.
- Galleries of up to **5,000 props**, with an automatically sized owned floor.
- Oversized gallery exhibits fit the chosen spacing; saved map transforms retain their original scale.
- **6,000 tracked objects** and paginated map saving/loading.
- Visible **Close / F7** menu button.
- Menu rebuilds after level travel when the player controller changes, including travel to the continent.
- Existing actor-class gallery spawning remains available through the slower validated path.

## Downloads

Download the SDK ZIP and World Builder mod ZIP. Thumbnails and the source bundle are separate optional downloads. Checksums and detailed validation are attached.

Close the game and controller before upgrading. Extract the SDK into the game folder, preserving settings, SDK_Assets, and optional SDK_Mods. Do not overwrite an unrelated version.dll loader. Put E33WorldBuilder.sdkmod in SDK_Mods. The thumbnail pack includes its own importer and instructions.

## Validation and limits

Live warm-asset tests placed **4,994 of 5,000 gallery entries in 67.3 seconds** (six oversized exhibits skipped). A **5,014-object map reloaded in 18.7 seconds**, with every saved ID, asset and transform matching afterward. Gallery cleanup preserved the original scene exactly. The final candidate passed **43 tests**; opening, closing and reopening the menu on the continent also passed after the travel fix.

Cold Unreal asset loads cannot be preempted and can exceed the approximate 4 ms native batch budget. These timings do not promise cold-load performance. Gallery timing used v41; final v42 shares its placement routine with the actor fallback and was used for large-map restoration. RC8 was tested by restarting the SDK controller against the running game; a fresh game-process restart and full character/combat regression are not claimed.

The optional image pack includes **5,985 previews from 6,376 catalog meshes**; 391 entries have no supplied image. Images depict game assets and are not covered by the SDK code license. Personal maps, map screenshots, settings, logs and credentials are excluded.
