E33 World Builder 0.29.0 experimental
Requires SDK 0.1.0-rc9 with the worldbuilder-v52 native adapter.
RC8 does not include these newer camera and duplication controls.
Stock RC6/RC7 cannot run this version.

F8: enter/leave builder camera. Mouse look; WASD fly.
Space: up. Ctrl: down. E/Q also work. Shift: four times faster.
Hold left mouse to grab the prop under the crosshair; fly to carry it.
Release to place. The name is shown while aiming and carrying.
A temporary emissive surface highlights the prop; original materials return
when aim moves away, the game loses focus, or builder mode exits.

With Num Lock on:
  Numpad 8/2 forward/back; 4/6 left/right; 9/3 up/down; 7/1 yaw.
  Alt makes these adjustments ten times finer.
Alt+Z: undo the last drag, nudge gesture, or duplicate creation (64 history entries).
Undoing duplicate creation deletes only the copy and removes its map record.
Later edits undo first; the original gallery prop is preserved.
Alt+Y: redo undone moves or duplicate creation at the saved transform.
Restored copies retain their map ID. New edits clear redo history.
Z is blocked from gameplay while the builder camera is active.
History belongs to the current session and is not restored from saved maps.
F10 / Duplicate: copy the selected spawned prop into your hand.
Click copies ON: clicking a spawned prop carries a copy; click again to place.
The menu toggle is saved. OFF restores click-and-hold movement of originals.
F9: restore all edited transforms and mobility.
Escape: close the current preview/menu/camera layer without game pause.

GPU scene-depth captures select actual rendered surfaces of ordinary static-mesh
props, including Blueprint-owned components and props without collision.
Rotated bounds only shortlist candidates; they never count as a surface hit.
Three fence-gated readback slots pipeline candidate checks, with at most one
small capture submitted per frame. No synchronous pixel reads or GPU waits.
Overlapping candidates can add targeting latency. Results are rejected when
stale or no longer aligned with the crosshair. Discovery takes several seconds
after entry and updates incrementally for streamed scenery.
Ambient SM_Sphere meshes and cloud/fog/sky/volumetric actors are excluded.
Landscape and foliage/instanced components are not supported. Translucent
surfaces that do not write scene depth may not be selectable.
The tracked scene supports up to 6,000 objects (including owned props and world edits).

Movement runs on the native game thread once per rendered frame; Python only
polls diagnostics twice per second. Losing focus pauses movement and ends a
grab; a fresh click is required on return. Start in unmounted exploration.

F8 leaves placed geometry in this loaded session. F9, mod disable, and SDK
shutdown restore world edits and remove spawned props. Save a map before exiting.
Static lighting may remain at its baked position. Game actions are not globally
suppressed, so use in a quiet exploration area.

Aim rays are deprojected from the viewport center matching the crosshair.
The D3D12 adapter targets this E33 build's two-pass scene-depth capture path.
Hold LMB while the asynchronous result arrives to grab it.

F7: toggle asset catalog. Close / F7 in the top-right closes only the menu. F8 also works while the catalog is open.
Click folders to browse; Up folder returns to the parent.
Search filters asset paths globally. Mesh/Actor switches asset type.
Favorites persist between sessions. Click a mesh card for its larger preview,
then Spawn selected to place it in front of the builder camera.
The catalog queries the game asset registry without loading every mesh.
The captured registry contains 6,376 static meshes; actor classes depend on
the loaded game world.
Actor eligibility excludes enemies, gameplay controllers and progression actors.
Catalog metadata and generated thumbnails persist in SDK/settings/E33WorldBuilder/cache.
The menu tree warms up after SDK startup. Reopening reuses up to 120 textures;
after restart, thumbnails load from PNG files without respawning their meshes.
New thumbnails generate progressively while the menu is open. Preview colors
use base-color/normal captures with fixed neutral illumination, independent
of the current map lighting. Game/package updates invalidate cached entries.
Background mesh captures use full-image asynchronous GPU readback and a native
PNG worker. First-time mesh loads can still briefly stall. Foreground/manual
and map captures retain synchronous export. Existing GPU picking is asynchronous.
Some special/material-only meshes produce an empty preview.

Build: browse and spawn individual assets.
Gallery: batches of up to 5,000 meshes use native time-budgeted spawning.
The owned floor expands beneath tight or spaced layouts. Oversized exhibits
fit within the chosen spacing; map loads retain their saved scale.
Closing the menu pauses the gallery; Pause / resume continues its queue.
Clear gallery removes only its exhibits and floor. Actor classes remain
available through the slower individually validated spawn path.
Library: shows spawned scene assets, excluding temporary preview props.
Maps: select a saved map and use Load map. Save map uses the editable name
and creates a new save each time. Clear scene before loading another map.
Map files live in SDK/settings/E33WorldBuilder/maps/*.e33map.json.
They track asset paths, transforms, actor component edits and the source level.
Only load in the same game level. Assets must exist in the current catalog.
These are builder scene files, not replacement game levels or game save files.
Enemy controls are intentionally omitted.

3D booth: select an asset and click Preview. Mouse orbits, W/S zooms,
numpad 8/2 pitches the prop, 7/1 yaws, 9/3 rolls. L cycles Studio, Bright,
and Dark lighting. Escape or F7 returns to the prior camera and catalog.
The room, lights and preview prop are disposable and excluded from map saves.

Gallery: choose a folder/search, set batch size (1-100) and spacing in cm.
Tight packing measures actual bounds with a 50 cm gap; Spaced uses the grid.
Next/previous replaces only the gallery batch. Pause retains its queue.
Save galleries stores the asset plan and origin; Rebuild restores that plan
in the same game level. Visit next moves the camera to successive exhibits.

Library defaults to spawned scene objects. Visit, Duplicate and Delete apply
to the selected scene instance. Asset tools switches to the catalog and adds
category/tags, favorites, icon capture pause/resume/cancel, loaded/registry
indexing and cleanup retry. Category/tags are searchable and persist on disk.

Maps: save/load a tracked scene, select its map card, then Take map thumbnail.
The captured world view and camera pose persist. Visit saved view returns to
that pose in the same game level. Map thumbnails retain the level lighting.

Camera update (native v44): independent mouse-look avoids the continent pawn horizon limit. Mouse sensitivity is 1.25 degrees per input unit; pitch ranges from -89 to +89 degrees. Play from camera (top menu) teleports the character using collision checks and returns character control. A blocked destination keeps freecam active.

Native v45: Camera settings button opens sensitivity and fly-speed fields with Apply and save, Reset defaults, and a saved automatic prop highlighting switch. Preferences are stored in SDK/settings/E33WorldBuilder/camera-settings.json. Grabbing a spawned scene/gallery prop selects its source asset when F7 next opens the catalog; Favorite / unfavorite saves it.

Native v46: Prop highlight cycles Auto / On click / Off and saves immediately. On click highlights only the grabbed prop while holding the left mouse button, restoring its materials on release. Existing on/off preferences are preserved.

Native v47: F10 / Duplicate to hand clones the selected spawned scene or gallery prop. The source stays untouched; fly the tracked copy and click once to place it. Copy rotation and scale are retained. Numpad fine movement remains available. Copies are included in map saves. Place the current copy before duplicating again.
