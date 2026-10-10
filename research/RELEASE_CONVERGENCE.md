# Frozen v0.1 release scope — 2026-10-09

User-directed scope change from exhaustive BL4 parity to a usable independent
SDK release. This supersedes the expanded-scope completion target in
V01_PROGRESS.md; its49%/160-320hour assessment remains historical, not the ETA
for this reduced release. Safety and truthful validation are unchanged.

## Already working: preserve, integrate, do not expand

Live objects/names/reflection and supported calls; persistent native-console
Python; currently verified Harness operations; registry/console management;
scoped commands/actions/hooks and selected load/unload/reload cleanup. Preserve
their tests and documented boundaries. No new broad reflection or trace work.

## Must fix before release, in execution order

1. Measure native menu open/paint/close costs; remove the dominant redundant work
   without dropping runtime checks. Target first open within5seconds and ordinary
   navigation within1second on this machine. These are acceptance targets, not
   achieved fresh-process timings. Existing-process timing passed on October 9
   (see bounded menu discovery below). Keep a cleanup owner on failure.
2. Minimal keybind service: registration/removal, Python dispatch, remap/unbind,
   persistence, basic conflicts, scoped unload cleanup, native-menu configuration
   and console recovery. Inspect preserved BL4 logic before implementing adapters.
3. Integrate essential management: discovery/load, enable/disable, supported
   configuration/actions and safe reload. Key mapping may use a simple verified
   key selector; arbitrary text editors and full workspace polish are not gates.
4. Portable installation/launch with no developer paths; include only supported
   runtime modes and document experimental/deferred modes accurately.
5. One representative fresh-process release matrix: attach; console Python;
   discovery/load; responsive menu navigation/close; key registration/remap/fire;
   supported Harness inspect/action; unload/reload/cleanup; normal exit/relaunch;
   run packaged outside checkout. Extend only for failures or concrete risks.

## Deferred to v0.2

Exhaustive BL4 parity; additional reflection/container codecs and mutations;
advanced/Blueprint traces; Gearbox-specific GameData/Kart; all original UI
editors/themes/polish; generalized input framework/controller support beyond
verified minimal requirements; multi-build/platform compatibility; speculative
stress campaigns unrelated to the supported release path. Existing features are
preserved, with unsupported/unverified behavior labeled rather than promoted.

## Frozen denominator and baseline

This is a NEW requirement denominator, explicitly authorized by the user.
Weighted deliverable completion estimates (not test counts): foundation15% at85,
console10% at85, supported Harness15% at80, responsive menu20% at20,
keybinds15% at0, essential fallback5% at75, mod lifecycle10% at70,
portable install5% at25, fresh integrated release validation5% at30.
Sum(weight*score)/100=50.75%, displayed as51%. This is a scope rebaseline,
not a two-point engineering improvement over the prior49%. Mandatory gates
remain mandatory regardless of the average. Scores have judgment uncertainty.

Critical path: measured menu fix -> minimal keys -> integration/package -> fresh
acceptance pass. Aim for the next few substantial sessions; no elapsed ETA is
promised before the menu and input blockers are resolved. No whole-image analysis
or architectural rewrite without evidence that the release path requires it.

At meaningful milestones report completed work, actual live proof, remaining
blockers, critical-path change and this frozen-scope percentage. Increase scores
only for verified deliverable progress; do not change weights silently.

## First measured milestone

The real existing v18 host completed a cProfile-wrapped native-menu open in
193.984seconds (profiling overhead included). It made422external _query calls
with162.51seconds cumulative time;337describe calls took116.46seconds. Build
alone took173.67seconds. These nested times overlap and must not be added.
Raw evidence: evidence/management-profile-open.{json,prof}; host log
logs/trace-v18-schema-host.log. The profile ran the previously loaded widget
module, before the hoisted lookup change; no end-to-end speedup is claimed.

The dominant next target is repeated process-backed metadata acquisition, not
an unmeasured UI rewrite. Reuse verified descriptors within the existing planner
while keeping native dispatch schema/identity checks, then remeasure. New output
identities still require live observation/ownership. The51%baseline is unchanged;
the critical path is better identified, not yet completed. The menu remains
owned by the current management service for normal close/cleanup.

## Planner metadata reuse implemented

The existing explicit InvocationPlanner now owns a bounded256-entry metadata
observation cache for functions, POD descriptors and enums. Reuse checks recorded
dependency identities against its catalog. Explicit refresh/refresh_from/close
clear observations; newly observed result closures can extend the catalog without
forcing repeated reads of unchanged schema observations. Native invocation still
checks the actual live schema, function entry, identities and execution context.
There is no cached-result fallback after an identity/read failure and no dispatch
retry. Ordinary prepare_call remains uncached outside this planner.

Five targeted tests pass for repeated reads, dependency recycling, function
recycling, read failure, and planner refresh/close revocation. The existing375
tests also passed after integration. A read-only live planning benchmark on
KismetMathLibrary.Add_IntInt compared10equal plans:3.4422seconds ordinary versus
0.3382seconds with reused metadata, including the first cache fill. No engine
calls were dispatched. Evidence: planning-metadata-benchmark.json and
planner-metadata-focused.log. This proves the targeted cost reduction, not the
full-menu acceptance target; a fresh controller/menu measurement is next.
The current mapped DLL and running controller were not replaced. Frozen release
completion remains51% until the user-facing performance gate is met.

## Live metadata-cache result

The replacement controller opened the complete native menu in60.215seconds
(cProfile enabled), down from193.984seconds in the comparable prior profile:
a69% reduction. Query count fell422->90, describe calls337->24. The menu
rendered normally. Close took11.215seconds and the existing evidence assertions
confirmed the identical game viewport, restored viewport focus, zero child
scopes, and exact pre-open retained-holder baseline. Controller shutdown then
completed with exit0. These are measurements in the existing game PID39900,
not fresh-game release acceptance.

Raw artifacts: evidence/management-profile-before-cache.{json,prof},
management-profile-metadata-cache.{json,prof},
management-profile-metadata-cache-close.json, metadata-cache-{before,open,after}.json;
logs/metadata-cache-host.log. Nested costs overlap:7full captures22.23seconds,
54selected captures18.82seconds,90external queries47.67seconds total.

The performance blocker is reduced but remains open; the frozen score stays51%.
Next remove redundant full scans and the repeated read-only probe startup/image
verification cost while preserving current-build and live identity validation.
The priority order remains menu performance, minimal keys, integration/package,
then the representative fresh-game acceptance matrix.

## Redundant catalog scans removed and verified

InvocationPlanner accepts an explicit same-process Catalog, using the existing
refresh_from validation instead of immediately scanning again. The owned panel
passes its initial observation. Selected-result panels now read RootWidget from
fresh selected tree/canvas closures, not a full enumeration. Identity failure
does not retry or fall back. Native dispatch and root compare-and-swap checks
remain unchanged.

The next live profile completed in48.805seconds; full captures fell7->4,
with11.57seconds in those captures and39.52seconds across89external queries.
Close completed in8.542seconds. Before/open/after assertions again confirmed
shared registry, zero remaining child scopes, exact holder baseline and the
same viewport with restored focus.28focused prepared-invocation/widget tests
passed, including the two new failure-boundary tests. Raw artifacts:
management-profile-selected-root.{json,prof}, management-profile-selected-root-close.json,
selected-root-{before,open,after}.json; logs/selected-root-host.log.

This is approximately75% less time than the comparable193.984second profile,
but not a responsive release menu. Completion remains51%; no keybind or
packaging credit is claimed. Repeated process-backed reader startup is now the
next measured target, followed by the remaining full captures and observation
merge overhead if needed. No native DLL was rebuilt or replaced for these fixes.

## Operation-scoped reader and catalog reuse (2026-10-09)

Menu open/close now own a read-only child process for that operation. The worker
verifies the build and resolves disk anchors once under a deny-write/delete file
handle, pins the original process, and rechecks process/module/file identity and
live anchor bytes for every request. Runtime observations remain fresh reads.
Both protocol layers reject mutation commands; failed/truncated/malformed replies
close the worker without a retry or one-shot fallback. Closing the operation
closes its child, which owns no game hooks, widgets or retained values.

The live ten-query equality benchmark took 3.421 seconds with ordinary queries
versus 0.446 seconds with the worker, including startup. Worker exit was zero,
the reader thread stopped, and a direct native mutation opcode was rejected.
The first integrated menu profile was 18.696 seconds open / 6.882 seconds close.

Explicit same-process planning catalogs now eliminate redundant assignment and
menu-preparation scans. Merging already validated observations preserves identity
and class-relation checks without rebuilding every unchanged class index. Native
schema checks, object identity, compare-and-swap and lease ownership are unchanged.
The resulting live profile was 10.191 seconds open / 4.276 seconds close, with
two full captures instead of four. All twelve controls rendered. Before/open/after
assertions passed for shared registry, restored viewport focus, zero child scopes
and the exact retained-holder baseline. These runs used existing PID39900, not
fresh-game acceptance. All 392 unit tests passed.

Raw evidence: readonly-worker-benchmark.json;
management-profile-readonly-worker.{json,prof},
management-profile-readonly-worker-close.json, readonly-worker-{before,open,after}.json;
management-profile-worker-catalog.{json,prof},
management-profile-worker-catalog-close.json, worker-catalog-{before,open,after}.json;
menu-worker-catalog-regression.log; logs/readonly-worker-host.log and
logs/worker-catalog-host.log. Profile timings include instrumentation overhead.
The timing helper now supports profile=False with separate timing artifacts.
The frozen completion score remains 51% pending the user-facing performance gate.

The subsequent unprofiled rebuild measured 9.493 seconds open, 0.193 seconds
refresh and 3.968 seconds close. All before/open/after assertions passed again.
Evidence: management-timing-{open,refresh,close}.json and
worker-timing-{before,open,after}.json. Refresh is not a measured physical-click
navigation test. Opening still misses the five-second target. Remaining measured
cost includes two full captures and per-line cross-thread reader delivery;
optimize that delivery before considering additional native engine primitives.

## Targeted WidgetTree discovery (2026-10-09)

The operation-scoped queue batching experiment returned an identical 96059-object
catalog but did not materially reduce full-capture time (ordinary 2.583 seconds,
batched 2.571 seconds). It was reverted. A separate C++ stream synchronization
experiment was also reverted after the worker took 2.883 seconds versus 2.608
seconds for the ordinary capture; evidence: reader-stream-benchmark.json.
Neither experiment changed the mapped native DLL or earned release credit.

Instead, read_object_reference now reads one reflected scalar ObjectProperty,
validates the original response, captures the observed target/reference identities
and their class/outer closure, and decodes against that verified closure. It
returns an extended observation catalog, not an ownership token. Changed or
missing identities fail without property retry or full-scan fallback. The menu
uses this to discover the newly created widget's WidgetTree, avoiding its second
full catalog capture. The original unselected path remains available.

Live unprofiled opening fell from 9.493 to 7.159 seconds in PID39900. All twelve
controls rendered. Close took 4.001 seconds. Before/open/after assertions verified
the shared registry, exact retained-holder baseline, zero child scopes and restored
focus on the same viewport. The 395-test suite passed, including new direct-reference
closure, null/type and changed-identity tests. Evidence:
management-timing-reference-closure-{open,close}.json,
reference-closure-{before,open,after}.json, reference-closure-regression.log,
logs/reference-closure-host.log. This still misses the five-second opening target;
completion remains 51%. The remaining full initial catalog and serialized game-thread
construction calls are the next costs to address, not per-line queue mechanics.

## Bounded menu discovery: performance gate passed in existing session

The read-only worker now supports bounded exact-name/class candidate discovery,
followed by the existing validated identity and class/outer dependency closure.
The native menu requests its actual dependencies rather than serializing the
whole registry. Missing, changed or ambiguous targets fail; no full-scan retry
or weakening of native invocation/ownership checks was introduced. Function and
default-object lookup observations are cached only within each owned panel and
cleared on close. This follows the preserved BL4 menu's targeted class lookup
pattern while using our own verified observation and invocation infrastructure.

A read-only comparison in PID39900 found all 470 requested matches in a
1337-object closure, versus 96059 objects in the full catalog. Every returned
observation equaled its full-catalog counterpart. Capture took 0.792 seconds
versus 2.598 seconds. All 398 regression tests passed. The mapped DLL was not
rebuilt or replaced; only the standalone read worker changed.

Live unprofiled opening took 4.903 seconds. A physical click into the Harness
details page completed dispatch and repaint calls in 0.419 seconds; a subsequent
screenshot confirmed the rendered details page. This measures controller-side
dispatch, not independent input-to-display latency. Close took 3.924 seconds.
Before/open/after assertions passed: shared registry, exact retained-holder
baseline, zero remaining child scopes, same viewport and restored viewport focus.
The game remained at its main menu. No fresh game launch is claimed. Opening has
little margin under five seconds and must pass again in packaged acceptance.

Raw local evidence: evidence/menu-catalog-benchmark.json,
evidence/management-timing-matched-catalog-{open,close}.json,
evidence/matched-catalog-navigation.json,
evidence/matched-catalog-{before,open,after}.json,
evidence/matched-catalog-regression.log and logs/matched-catalog-host.log.

Frozen-scope progress is now **57%**: menu deliverable increases from 20 to 50
for verified responsive construction/navigation and cleanup; every other score
and weight stays unchanged. Weighted sum is 50.75 + 20*(50-20)/100 = 56.75.
Menu configuration/key integration and fresh-process acceptance remain incomplete.
Critical path now proceeds to minimal configurable keys, then integration,
portable packaging and the fresh-process acceptance matrix. Advanced parity is
still deferred; the performance work does not earn credit for those features.

## Keybind preferences and frontend integration

Inspected the preserved BL4 set_keybind_value and workspace key-management
implementation: shared runtime/display values, None for unbind, saved settings,
enabled-mod conflict reporting, and lifecycle-owned callbacks. Our ModDefinition
now accepts Keybind definitions with stable IDs, titles, defaults and callbacks.
The existing Registry owns mappings and presents the same saved values to the
console and UMG presenter. No second preferences store was introduced.

The console supports mods keys/bind/unbind/resetkey. The UMG presenter provides
a paginated key selector, unbind and reset using ordinary native buttons. Mappings
are persisted before the in-memory generation changes; a failed save preserves
the prior map. Remapping invalidates earlier selections/deliveries. Disabled and
unloaded mods have no routes. Conflicts suppress all enabled owners of that key;
callbacks are owner-thread checked, error-contained and never replayed. Dispatch
revalidates the selected generation, current map and enabled/conflict state.

All 406 tests pass, including eight new focused tests for persistence, failed
saves, stale delivery, disable/unload, collisions, callback failure, console
recovery and the UMG selector. Evidence: evidence/key-preferences-regression.log.
This is implemented and unit-tested controller-side functionality only. Native
key delivery has NOT been connected, and the new frontend has NOT been validated
in the live game. The existing controller is still running its previous modules.
Frozen completion remains 57%; no live keybind completion credit is claimed.

Next: add bounded key-map/event transport to a new runtime candidate using the
already verified game-thread message hook. Preserve console ownership, reject
stale map generations, suppress repeats and console typing, and clean up on
disconnect. Do not overwrite the mapped v18 DLL. Then validate actual physical
press/remap/unbind/unload and integrate packaged fresh-game acceptance.

## v19 bounded native key transport candidate

A separate v19 DLL/controller builds with warnings treated as errors. It retains
the v18 capability chain and adds a fixed 64-binding / 64-event protocol. Its
game-thread message hook only queues copied token/key pairs; it never calls
Python or consumes ordinary game input. Delivery is suppressed for repeats,
modifier chords, other foreground applications, native console typing and an
active SDK UMG menu. Eligibility reuses this build's verified console attachment
and state checks. No stock Unreal FKey layout or new engine hook is assumed.

Maps require a session nonce and strictly increasing generation. Replacement
clears earlier queued input; drain requires the exact current generation.
Duplicate keys/tokens and console-toggle collisions are rejected. Teardown clears
the map before any unrelated cleanup can defer. The fixed queue reports overflow.
The Python wire decoder checks identity, bounds, unused fields and rejection
consistency; older runtime handshakes reject this capability before transport.

The native fixture passed ABI/filter/generation/overflow/cleanup checks; all 410
Python tests passed. Evidence: evidence/keybind-native-fixture.log,
evidence/key-wire-regression.log, evidence/keybind-candidate-hashes.txt.
The v19 build was confirmed absent before creation; PID39900 still uses its
existing v17/v18 modules. No mapped DLL was overwritten and no v19 live attachment
has occurred. Registry polling/dispatch integration and live physical-key
acceptance remain required. Frozen completion is still 57%.

## First live key delivery and remap

The v19 registry bridge is now integrated into ModLoader polling and available
through Session(keybinds=True) / launch.cmd management --keybinds. A single
session-owned map uses monotonic generations across registry-owner reuse. The
complete response batch is checked against the acknowledged map before callbacks.
Each callback rechecks registry generation, enabled state, current mapping and
conflicts. Overflow discards the batch. Uncertain transport outcomes stop delivery
without retry; a borrowed session remains owned by its host and cannot be adopted
by another key service. Normal loader close clears the native map.

All 417 distinct Python tests passed, including seven new service tests covering
map replacement, disable, malformed batches, overflow, callback-triggered lifecycle
changes, owner reuse and uncertain outcomes. Evidence: key-service-regression.log.

After cooperative v18 shutdown (host exit0), v19 attached to existing PID39900.
KeybindExample was loaded/enabled through the native Python console. Physical F6
produced callback count1 at 19:53:00. Remapping count to F7 advanced the registry
generation and saved F7 in settings/management.json. Physical F6 then produced no
additional callback, and physical F7 produced count2 at 19:53:45. The native
console stayed functional and the game remained at its main menu. Evidence:
logs/keybind-v19-host.log and evidence/keybind-first-delivery-host.log.

This is live proof of registration, delivery and API remapping in one existing
game process, not full keybind acceptance. UMG selection, typing suppression,
error containment, unbind, unload/reload, controller reconnect and fresh-game
restore still require live checks. The v19 DLL is now mapped: DO NOT rebuild or
overwrite it while the game remains running. Use the example's current saved F7
mapping in subsequent checks; its counter is currently2.

Frozen score: keybinds increase from0 to30 for this verified partial deliverable.
Weights and other scores are unchanged:56.75 + 15*30/100 =61.25, displayed **61%**.
Next finish the keybind acceptance checks, then portable packaging/fresh acceptance.

## Existing-process keybind integration acceptance

On October 9, the same v19 controller and game PID39900 passed physical-key
checks for console typing suppression, callback error containment followed by
successful delivery, unbind, unload revocation, saved mapping restoration on mod
reload, and actual callback execution after that reload. The unloaded example's
console alias was removed; a temporary retained Python reference proved that a
subsequent physical press did not increment the old instance. That reference was
then deleted.

Physical clicks navigated the native menu through Keybind Example / Keybinds /
Count press and selected B. The UI and settings file both showed B. A B press
while the menu was open was suppressed; after clicking Close, B incremented the
counter from1 to2. The closed panel had zero child scopes and no reported error.
An initial assertion incorrectly expected not_created (the explicit service-close
state); it failed harmlessly and was corrected to the button-close state, closed.
No implementation change was required for that assertion failure.

The console management command handler then assigned the example's second binding
to B. It reported both conflicting owners; a physical B press produced neither
the count callback nor the error callback. Console unbind/bind commands cleared
the conflict and restored count to F7; physical F7 then incremented count to3.
Evidence: evidence/keybind-existing-process-acceptance.log and
evidence/keybind-existing-process-settings.json. The preserved raw log includes
the expected callback exception and the incorrect test assertion. Some redirected
log lines are interleaved/truncated; assertions and observed UI transitions
provide the supporting context recorded here.

This validates the connected native menu, console recovery and key service in an
existing process. It does NOT prove controller reconnect, fresh-game persistence,
all key-selector pages/reset/unbind buttons, cross-mod conflicts, or packaged
operation. Native UMG text/numeric/JSON editors remain deferred. v19 is still
mapped and must not be overwritten. Current example count3, mapping F7, error
binding unbound; native panel closed, controller still running.

Frozen score: keybinds30 ->60; other weights/scores unchanged.
61.25 +15*(60-30)/100 =65.75, displayed **66%**. The remaining critical path is
controller reconnect and integrated lifecycle checks, portable packaging, then
the mandatory fresh-process acceptance matrix. No release-ready claim is made.
