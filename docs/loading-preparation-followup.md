# Loading preparation follow-up

Flight now discovers its exploration target and prepares copied invocation
schemas on a read-only worker during loading. Activation consumes a matching
current-world snapshot and a warmed owned reader. Native possession and
movement checks remain mandatory. Sampling stops after activation and restarts
after returning to title; no Session or scope crosses worker threads.

The version 2 read worker can select identities and read bounded values in one
request. Version 1 workers retain the existing fallback. Selected-object,
reference, descriptor and process validation remain in both paths.

Pause metadata is prepared during loading. Current pause widgets are discovered
through the verified controller and Resume button hierarchy, with bounded
discovery fallback before construction. Detached UI ownership checks reuse
only admitted metadata and freshly validate the complete owned hierarchy.
UI preparation may start before SaveLoaded becomes true; gameplay activation
still requires independent fresh admission before every enabled mod.

Activation console messages are batched between input-service intervals.
Preparation, activation and usable timings remain recorded and are displayed
by `startuptiming`.

## Title and loading refresh

Detached core menus, World Builder catalog/HUD trees and title/pause button
contents now prepare in the engine bootstrap loading window. The title entry
uses fresh authored widget hierarchy proof independently of save readiness and
can attach behind the Press Any Button screen. Gameplay activation still waits
for fresh possession and world admission. Read-only GC races defer proof and
untouched preparation owners; they do not replay uncertain native mutations.

Earlier title/loading refresh versions: Continent Flight 0.4.3, Map Travel 0.2.4 and World Builder
0.32.5-experimental. The SDK version remains 0.1.0-rc18 with native runtime210.
This refresh uses a new release tag; earlier assets remain immutable.

## Earlier title/loading baseline: validation and remaining limits

The Python suite passed 2,060 tests with 8 skips; the separate World Builder
suite passed 140 tests. Live checks covered cold launch, title menu fade-in,
save loading, Flight toggle/restore, keybind scrolling and same-session title
return. The Mods button was present alongside the authored title buttons during
their fade-in. Title attachment took 0.88-1.01 seconds before that menu appeared;
a prepared title Mods opening measured 167 ms.

In the final cold run, core menu preparation took 6.25 seconds, World Builder
3.40 seconds and Flight preparation 0.68 seconds, all during startup before
save selection. Flight activated from its loading snapshot in 44 ms. All seven
enabled gameplay mods restored successfully. The owner logged final restoration
0.65 seconds after exploration readiness, excluding earlier UI rebinding and
pause attachments. Those attachments took about 0.71 and 0.60 seconds.

The first-visible-gameplay zero-delay target is not established. First pause
inspection showed both buttons ready, but the sampling does not establish an
80 ms bound after the earliest possible pause. Changing the shared panel from
Mods to Map Travel (or back) still repaints and measured about 0.69 seconds,
down from 2.19 seconds. Its paint phase remains about 0.50-0.52 seconds. Thus the
200 ms goal applies to the measured prepared Mods opening, not every view change.
Timings remain available through `startuptiming`; detailed stage measurements
are kept in the local SDK log, not normal console startup output.

## Map Travel recovery follow-up

Map Travel now detaches borrowed input and pause entries while retaining the
GameInstance-owned menu shell. Destination observation belongs to the process,
so retirement of the departing mod cannot leave travel waiting for its timeout.
Read-only arrival checks borrow an active reader and discard known loading/GC
read failures; the native transition is never redispatched.

The departing Map Travel instance also leaves destination button creation to
fresh world activation. Attaching it from the old scope could cause retirement
to reject the new-world owner and abort the shared SDK controller. Controller
aborts and held retirement adapters now retain local stack diagnostics.

Released loading preparations are discarded after their cleanup acknowledgement,
including during world-to-world travel. World Builder clears its corresponding
preparation reference so a later activation cannot adopt closed panels.

The regression suite passes 2,071 tests with 8 skips. A cold-session transition
from Ancient Sanctuary to Blades Graveyard restored all seven enabled gameplay
mods and reopened Mods successfully (166 ms measured opening). Restoration
completed about four seconds after destination exploration admission; this
travel check does not establish the initial save-loading latency target.
The following return trip exposed the released-preparation gate; applying its
scheduling correction recovered that session without restarting. A subsequent
Ancient Sanctuary to Blades Graveyard transition then restored all seven mods
automatically, with no controller abort or retained-preparation stall.

## Earlier runtime211 assigned-map collision protection

WorldBuilder Map Loader 0.2.3 and native runtime 211 protect a saved player
whose supporting floor is supplied by an assigned WorldBuilder map. A native
guard is armed during title preparation with the explicit assigned-world
inventory (up to 32 worlds). The existing game-thread message pump observes
the exact local possession and disables movement before Python UI setup and
asset preflight. Placement acknowledgement restores the captured movement
mode. The previous two-second exploration stability delay is removed from
automatic assigned-map loading.

The guard checks the engine function schema and exact world/pawn/component
identities on dispatch. Temporary serial-stabilization leases end in the same
callback; the guard does not retain a departing world. Completed world visits
are remembered so normal character changes cannot acquire another loading
hold. Assignment updates preserve that journal. Validation/activation failures
release an unadopted native hold, and controller shutdown performs native
cleanup. Old-world retirement leaves a destination world's hold for its own
loader to acknowledge. Manual reloads also hold movement before removing the
existing props.

Two consecutive live save loads, separated by a return to title in the same
SDK session, restored 1,798 props and left the player standing on the custom
floor. Normal movement resumed after placement. The measured placement work
was about 4.9 seconds; the player remains protected throughout that work.
The regression suite passes 2,088 tests with 8 skips, and the native build and
its ownership/UI fixtures pass. Local diagnostic logs, saves, assignments and
screenshots are excluded from publishing.

A final clean launch verified the loaded DLL against the reviewed runtime211
file hash, loaded the saved world without a live Python patch, restored the
same 1,798 props in 4.94 seconds, and confirmed movement on the custom floor.
The installed release manifest verification passed after this check.

## Runtime213 custom-map preparation and reveal

WorldBuilder Map Loader 0.2.4 separates process preparation from destination
restoration. Assigned map files are decoded and validated into immutable plans
before gameplay. Static-mesh assets from `/Game/` and `/Engine/` are prepared
during loading under process ownership. Actor placement still requires a fresh
destination binding; no actor or world ownership is moved to a worker thread,
and the preparation cache never pins a departing world.

The loading presentation is a small, opaque, process-owned widget tree prepared
before save selection. The native gate observes SaveManager loading and
GameInstance map-change flags before destination possession. It shows the
prepared tree without activating CommonUI, taking focus or constructing a
destination pause menu. Native polling checks viewport membership so travel's
widget removal cannot silently leave the cover detached. Confirmed cancellation,
normal-world arrival, release and shutdown each have explicit cleanup paths.
Exact identities prevent a retiring world's callback from releasing the next
destination's presentation or movement hold.

Spawn completion, collision support and visual readiness are distinct evidence.
After placement, native queries verify that all owned actors/components remain
live and visible, run five downward traces near the saved pawn's feet, inspect
collision-enabled components, check recent rendering of SDK-owned supporting geometry,
and require no pending level-streaming state. The same query validates the
current world, pawn and save-generation binding. Python releases the captured
movement mode and cover only after this restoration contract succeeds.

The readiness loop has a 15-second failure deadline. The native cover has an
independent 60-second recovery deadline for a stalled or disconnected owner.
Neither deadline substitutes for readiness evidence or imposes a fixed success
delay. Invalid maps, cancellation and failed readiness release presentation and
the owned movement hold with a diagnostic. Recovery does not invent a checkpoint
or relocate the player; a save depending on missing custom collision may remain
unsupported after that release.

`startuptiming` records plan/asset preparation, map loading/spawning, collision
readiness, visual readiness, player release/cover removal and total restoration
work. Ordinary startup stays quiet. Recent rendering is an observable submission
signal, not a render-thread/GPU fence or a texture-streaming completion guarantee.
A floor outside the camera frustum can produce a conservative readiness timeout.

The final SDK suite passes 2,156 tests with 8 skips. Native runtime213 and
its ownership, readiness and bounded FString fixtures compile with MSVC /W4 /WX.
The integrated World Builder suite passes 140 tests; the separate project passes 78.

A clean native213 launch prepared 129 assets during loading in 4.94 seconds.
Restoring 1,798 props took 1.360 seconds; collision/visual checks took 17 ms,
and release/cover removal took 32 ms, for 1.416 seconds total beneath the cover.
The final return trip restored the same props in 1.485 seconds total, with
18 ms readiness checks and no recovery timeout. Asset preflight after loading
was below 0.5 ms. Placement remains destination work; the cover hides that work.

Cold custom-save loading, movement on its floor, same-session title/reload,
normal-save loading, travel away/back, Mods/Map Travel availability, cancellation,
and missing/invalid/incomplete map recovery were exercised live. The final
native213 build additionally verified the original loading artwork during travel
and reopening Mods with all seven gameplay mods ready. Earlier native212 checks
covered the unchanged title/reload and invalid-map recovery paths.

The original charcoal, petal and gold loading PNG is imported during preparation
using one exact audited engine signature. Its owned Image widget is covered by
an opaque fallback. No game artwork is redistributed. Vanilla support may use
an invisible collision proxy, so recent-render evidence applies only to SDK-owned
support hits; all five floor traces and settled engine streaming remain required.

A cancellation returning to the same non-title world and same pawn has no positive
cancel identity signal and may retain the cover until the native 60-second recovery
deadline. Title cancellation has explicit cleanup. No success path uses that deadline.

## Cold-title startup recovery

A subsequent launch exposed an unhandled not-dispatched stable-reference rejection
while adopting the authored title controls. A clean reproduction also exposed a
read-only descriptor identity change in the prepared-button state. Neither grants
authority to attach UI. The title entry now leaves construction unstarted, retains
its exact acquired references and detached button, and rediscovers current title
authority. Only stale/busy native rejections before dispatch are deferred; capacity,
unknown and post-construction failures remain held errors. Existing exact leases
are reused rather than acquired again. Lease diagnostics now include native codes.
