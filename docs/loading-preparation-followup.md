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

Public mod versions: Continent Flight 0.4.3, Map Travel 0.2.4 and World Builder
0.32.5-experimental. The SDK version remains 0.1.0-rc18 with native runtime210.
This refresh uses a new release tag; earlier assets remain immutable.

## Validation and remaining limits

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

## Assigned-map collision protection

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
