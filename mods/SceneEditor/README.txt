Scene Editor - live authoring and scrub timeline (v24 local candidate)

Requires the matching isolated native candidate and development SDK source.
SDK Mods > Scene Editor, or Insert: Load Sample Scene, then Live edit / timeline.

FLIGHT MODE
A center crosshair and SCENE AUTHORING status identify the mode.
Mouse looks continuously; WASD flies, Space/E rises and Ctrl/Q descends.
Shift flies faster. Aim at a character for the WorldBuilder debug-emissive
highlight. Hold LMB to carry it at the picked depth; release to place it.
The original grab offset is retained. Numpad 8/2, 6/4, 9/3 moves XYZ;
7/1 rotates yaw; Alt reduces movement speed. Only scene-owned actors move.
PageDown previews the selected character's animation independently.

TIMELINE MODE (Home toggles timeline / flight)
The world stays visible while the timeline owns mouse focus.
Drag empty track space to scrub at 30 FPS. Drag a colored clip marker to
change its scheduled time. ANIM shows the currently selected character only;
use Actor < / Actor > to choose another. AUDIO shows enabled audio cues.
Camera keys cannot cross neighboring keys. All drags snap to frames.
The yellow playhead, frame counter and ruler show the current time.
-1 frame / +1 frame provide exact stepping. Start rewinds.
Actor < / Actor > selects the character for Preview / Stop preview.
Play / pause runs scheduled animation and audio; reaching the end pauses
without destroying the scene. Scrubbing is silent and never fires notifies.
This authoring transport does not fire the sample Niagara effects/recoil.
Save stores the current scene, including the native placements and anchor.
Stop scene or End releases the temporary scene and restores gameplay.
Insert returns to the full document browser after safely stopping authoring.

CAMERA
A native shot CameraActor is independent of the authoring view. Its magenta
emissive cube and frustum edges show its position and orientation. The guide
transform order is corrected for StaticMeshActor's root component. Guides
are temporary and are absent from full-scene playback. Saved camera_keys
(up to 16) interpolate position/FOV and shortest Euler angle differences;
without keys, full playback retains the original orbit. The CAM track draws saved keys. Add camera key captures the current flight
view at the playhead. Fly with Home to frame the next shot, return to the timeline,
scrub to a new frame, then Add camera key. Clicking an existing key selects it;
Update camera replaces its view while retaining its time, and Delete camera
removes it. Adding at an occupied frame updates that key. Save persists keys.
The fallback no-key guide pose is illustrative, not the exact orbit pose.

CATALOG AND DOCUMENTS
484 selectable entries include nine assembled presets and raw skeletal meshes
from the game's typed registry, including Paintress. Raw entries may be body
parts, equipment or variants, not complete assembled characters. Search Add
character by name/path. Raw entries start in bind pose. The 293 approved clips
are revalidated for skeleton compatibility, root motion, additive state and
notifies; Paintress-specific clip discovery remains pending.

The full browser still edits character assemblies, animation choices, looping,
transforms and event start times. Changes to actor count/assembly/clip are made
there and reconstructed on entry to live editing. The timeline supports scrub/preview, rescheduling animation/audio starts and
camera-key capture/edit/delete. Add animation opens an eight-choice paged picker for the 293 verified clips.
Choose Actor < / >, scrub to a frame, then choose a clip to insert it there.
Up to 24 additional animations are supported across the six actors. Latest
start wins per actor (later inserted extras win equal-time ties); clips switch
rather than blend, and non-looping clips hold their final pose.
Audio library opens the game's typed SoundWave catalog. Type a name or folder
in the search field, click Search, select a result, and use Preview sound or
Add selected sound. Stop sound stops audition; previews automatically stop
after five seconds. Preview uses 0.2 gain; scheduled clips use 0.35 gain.
Each clip retains its chosen sound path (up to 23 additional audio clips).
Select an animation or audio start marker, then use Delete selected clip.
Deleting a character's original animation leaves the character in bind pose
until another scheduled clip starts. Other clip identities/times are preserved.
Select audio and use Volume -5% / +5% to set its saved gain from 0% to 200%.
Volume changes pause transport; replay from before the cue to compare levels.
Game music: ON/OFF toggles the original interactive background music for this
scene. The preference is saved and applies to authoring and full playback.
Stopping the scene restores music components paused by Scene Editor; components
that were already paused are preserved. Environmental sound effects are separate.
New audio clips create their own owned components without rebuilding actors.
Search matches all entered words against the full asset path. Existing saved
whoosh clips remain compatible. Start markers show clip names and
times; the selected animation/audio clip has its full name in the detail line.
New animation assets rebuild only temporary scene actors while preserving
anchor, placement, flight camera and playhead. Failed known preparation rolls
back to the previous scene; unknown native outcomes are never retried.

Saved scenes: settings/SceneEditor/scenes/<ID>.scene.json relative to the
candidate mod-root parent. Saving is atomic. The bundled sample is unchanged.
No gameplay AI, damage, gameplay Blueprints, dialogue or lip sync is invoked.
The original experimental recoil is preserved in full playback.

End: safe stop. Unknown native outcomes are not automatically retried.
No installed game files or existing user scenes are replaced by this candidate.

V28 LIVE AUTHORING CAMERA
The flight view uses 90 degrees FOV, independently of the scene shot's FOV.
The timeline stays visible while flying. Hold Right Alt to use the cursor;
release to resume flight. Home pins/unpins the cursor for search text entry.
Aim at the displayed camera BODY and hold LMB to carry it; release to place.
This inserts or updates a CAM key at the current frame (16 keys maximum).
Numpad translation/yaw also edits the selected camera. Select a character to
return these controls to character placement. Save persists camera transforms.
Only one crosshair is drawn. First-time timeline construction still takes time.
