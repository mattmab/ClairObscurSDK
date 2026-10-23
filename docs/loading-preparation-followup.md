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

## Validation and remaining work

Local live tests exercised cold launches, save loads, Flight toggling, Mods
opening, and return-to-title followed by another save load in the same session.
Flight consumed its loading snapshot in 31–40 ms in the measured runs. A warm
Mods opening took 163 ms. The full Python suite ran 2,039 tests with 8 skips;
the read worker compiled with warnings treated as errors.

The first-visible-gameplay readiness target is **not yet met**. Final saved-mod
restoration took approximately 0.59–0.76 seconds after the owner logged
exploration readiness. That interval excludes earlier synchronous UI handoff
and pause-entry attachment: closer screen sampling exposed several seconds of
that work after gameplay started becoming visible. These measurements must not
be reported as zero-delay readiness. Moving the eligible preparation window
earlier did not eliminate that handoff on the tested save. Further work must
remove or schedule the synchronous UI setup before presentation.
