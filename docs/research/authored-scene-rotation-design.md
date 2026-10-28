# Authored scene rotation: staged implementation plan

The existing origin protocol supports translation only. The Scene Editor must
not expose an editable whole-scene yaw until the native transform and actor
placement paths are both implemented and validated in the game.

For authored anchor `A`, desired world position `D`, and yaw rotation `R`,
an authored world-space point `P` must evaluate to `D + R(P - A)`. The owned
LevelSequenceActor's transform origin is therefore rotation `R` and translation
`D - R(A)`. `scene_transform.origin_translation` implements that pivot math.
World-space camera, animated source actors and all absolute source tracks must
be tested together. Existing adapters explicitly do not promise to relocate
possessables, relative tracks, events or unrelated world dependencies.

Blueprint NPC tracks are independent owners rather than source spawnables. An
NPC's authored local offset `O` and yaw `Y` use world position `D + R(O)` and
orientation `Y + scene_yaw`. The helpers used by replacement construction and
NPC construction/reanchoring implement this transform, defaulting to zero yaw.
Do not feed a nonzero yaw to only one side of this contract.

Before exposing yaw, introduce a new capability-gated native packet and distinct
operations for configuring and updating the complete private origin transform.
Keep version 1 requests and acknowledgement validation unchanged. Native code
must verify the existing exact private instance-data schema and fresh identity,
require an idle player for updates, re-prove the last acknowledged transform,
write only the quaternion and translation while preserving scale/padding and
unrelated flags, and quarantine unknown writes. Use a normalized Z quaternion
`(0, 0, sin(yaw/2), cos(yaw/2))`; validate finite bounded degrees and computed
translation before dispatch. Do not silently fall back to translation for a
rotation-bearing document on an older runtime.

The saved timeline schema needs an optional bounded yaw associated with the
scene position. Playback and editing promotion must reject a nonzero saved yaw
unless the new native capability is present, before creating playback owners.
The fast position-only apply path must compare yaw as well as position, and a
rotation update must rotate existing NPC owners without replacing their
identities. The native flight input packet needs a separately negotiated yaw
delta if Numpad 7/1 is used; preserve the old input protocol for older hosts.

Live acceptance should inspect the player-owned camera, authored animated
actors, a cast replacement and an active Blueprint NPC at the same frame before
and after a 90-degree turn around a nonzero anchor. Verify both actor positions
and orientations, playback and scrubbing after the turn, save/reopen, return to
exploration, and both failure/older-runtime behavior. Repeat on a second scene
with nested sequences before describing rotation as generally supported.
