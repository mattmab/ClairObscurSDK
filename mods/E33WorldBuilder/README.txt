H: Hide / show the entire World Builder HUD (remappable).
P: Play from camera (remappable in Mods > World Builder keybinds).
F7 shows Building Widgets... in the HUD while constructing its menu.

RC14: Holding built-in scenery through a level-streaming unload now releases
the expired selection while freecam stays active. Requires the RC14 SDK.

RC13 additions:
F5 opens live duplication of the current selected spawned prop. Set copy count
and compound X/Y/Z offsets, inspect the world preview, then Apply copies.
Unapplied previews are canceled when leaving the tab. Originals stay unchanged.
Delete removes the current spawned selection. Alt+Z restores its position,
rotation, scale and map tracking; Alt+Y deletes it again.
F7 switches from duplication to the Build prop catalog; F7 in Build closes it.
Escape closes the current menu. Selection and Controls are displayed in the HUD.

E33 World Builder 0.32.0 experimental
Requires SDK 0.1.0-rc14 or later with the World Builder native API.
Install E33WorldBuilder.sdkmod in the game-root SDK_Mods folder, then enable
World Builder in Pause > Mods. It is an optional mod, not bundled with the SDK.
Maps and settings remain in SDK/settings/E33WorldBuilder when disabled.

Downloads:
  SDK RC13: https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc14
  World Builder: https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc14
Close the game and SDK before updating. Extract E33WorldBuilder-0.32.0.zip
beside Sandfall; leave its inner .sdkmod archive intact. Preserve SDK/settings.
No separate Python, controller or native DLL is needed for World Builder.
Use the SDK Mods menu's Keybinds tab to rebind F7/F8/F9/F10: choose Rebind and
press a key. Escape unbinds; Cancel preserves the old binding. Resolve conflicts
before using a binding. Builder camera settings remain in its own Camera settings UI.
Catalog prewarming waits while another SDK menu owns focus.

Historical RC12 / 0.30.1 clean-install checks passed on 2026-10-15: Pause > Mods,
text sizing/reset, Keybinds and rebinding, F7 catalog open/close, F8 camera
off/on, foreground/rear cube targeting, drag and subsequent console execution.
Unavailable temporary catalog assets logged skipped-thumbnail errors. Not every
asset or operation was tested. Streamed map restoration remains a known limit.
See docs/RC12_VALIDATION.md in the repository for the full scope.

F8: enter/leave builder camera. Mouse look; WASD fly.
Space: up. Ctrl: down. E/Q also work. Shift: four times faster.
Hold left mouse to grab the prop under the crosshair; fly to carry it.
Release to place. The name is shown while aiming and carrying.
A temporary emissive surface highlights the prop; original materials return
when aim moves away, the game loses focus, or builder mode exits.

With Num Lock on:
  Numpad 8/2 forward/back; 4/6 left/right; 9/3 up/down; 7/1 yaw.
  Alt makes these adjustments ten times finer.
Alt+Z: undo the last drag, nudge gesture, duplicate creation, or selection deletion (64 history entries).
Undoing duplicate creation deletes only the copy and removes its map record.
Later edits undo first; the original gallery prop is preserved.
Alt+Y: redo undone moves, duplicate creation, or deletion at the saved transform.
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
SDK RC12 checks full-scene depth before individual candidates,
so foreground scenery blocks selection of props behind it. Every overlapping
candidate remains eligible; searches no longer stop at 32 bounds. Each search
revalidates its hit and owns the capture target until its readback completes.
Install SDK RC12 as well as this mod; replacing the .sdkmod alone does not
update native targeting.
No synchronous pixel reads or GPU waits are used.
Overlapping candidates can add targeting latency. Results are rejected when
stale or no longer aligned with the crosshair. Discovery takes several seconds
after entry and updates incrementally for streamed scenery.
Ambient SM_Sphere meshes and cloud/fog/sky/volumetric actors are excluded.
Landscape and foliage/instanced components are not supported. Translucent
surfaces that do not write scene depth may not be selectable.
The tracked scene supports up to 6,000 objects (including owned props and world edits).

Level streaming can reset the position of moved built-in world objects when
the game unloads and reloads those assets. Custom-placed props do not
participate in level streaming and are unaffected by those unload/reload cycles.

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

Reader recovery: a failed menu read is reported once and its closed worker is
retired. The next operation creates a fresh reader; it does not repeat a failed
widget mutation or clear scene edits. Successful recovery resumes status polls.

Region templates (paired template-capable SDK required):
F3 and F4 mark opposite corners at the builder camera position.
The box includes loaded, visible static-mesh origins inside it. Instanced meshes
are captured as independent props; rotations and scales are preserved. Hidden,
ambient, unloaded, skeletal, and gameplay logic objects are not copied. Material
overrides and actor scripts are not serialized by mesh templates.
In Maps, enter a name and choose Save Template (region). Capture runs in bounded
batches. Saved templates opens the reusable template list, across game maps.
Preview template places a temporary group anchored at the camera. Enter XYZ
world offsets and yaw, or use the +/- movement buttons. Apply makes the copies
tracked map assets; Cancel or closing/leaving the tab removes unapplied copies.
Templates are stored in SDK/settings/E33WorldBuilder/templates. The source
structure stays unchanged. Clear region removes the box and cancels scanning.

F1 toggles the Controls help between its full text and "(F1) Help".
Current Selection stays visible. The toggle is also rebindable in SDK Keybinds.
In Maps / Templates, selection yaw, pitch and roll rotate the bounds around
their center. Apply rotation updates the visible box and its capture filter.
Yaw +/- 15 offers quick adjustments. Capture discovers components in the
background, resolves asset references incrementally, and displays progress.
Cancel scan keeps your corners. Templates support at most 5900 captured props.

Maps > Edit bounds live hides the catalog so the selection box stays visible.
Mode cycles Move / Rotate / Resize; Step cycles fine to coarse increments.
The six +/- buttons change each axis immediately. Move uses world axes; Resize
uses box-local axes and preserves the center. Rotate also preserves the center.
Name and Save Template capture the adjusted region. Back to maps restores the catalog.

Hold an axis +/- button to repeat after a short delay. Releasing the mouse or
leaving the game stops repetition. Bounds edges update in place without respawning.
Mode also includes Scale with percentage steps; All scale +/- changes all axes.
Whole box cycles through eight corners, labelled by local XYZ signs and marked
with a cube. Move changes that corner in world axes while fixing its opposite;
Resize and Scale expand from the opposite corner. Rotation stays center-pivoted.

Region capture resolves up to 64 mesh references together and runs bounded scan
work per controller tick. Template and static-mesh duplication previews use the
same native batches of up to 64 props as saved maps. Duplication reuses existing
preview copies when adjusting offsets. Template updates replace pending movement
and apply the newest placement to remaining spawns. Apply waits for completion;
progress shows the remaining work and changes to ready when it finishes.

Template and duplication movement uses native batches of up to 128 transforms,
with a 4 ms game-thread budget and partial-progress acknowledgements. Requires
the matching SDK with builder operations 66/67. New templates are centered ahead
of the camera using their group extent. In Duplicate, Template Placement and
Bounds, hold the left mouse button in the open left side and drag to look around.
Release to use the placement controls; drags begun over the right panel do not
move the camera. The menu and current preview remain open.

Placement navigation: hold left mouse over the open world view and drag to look; while held, WASD flies, Space/E rises, Ctrl/Q lowers, and Shift boosts speed. Works in template, duplication and bounds menus. Release to edit fields. Requires the matching native SDK menu-flight update.
Large template previews start at most 5,000 units ahead of the camera. Bring preview here repositions the unapplied group near your current view, preserving its yaw and resetting XYZ offsets.
