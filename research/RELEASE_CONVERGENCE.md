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
   achieved timings. Keep a cleanup owner on failure.
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
