# GOAL

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: our native reader and Python API enumerate live objects in Steam build 23765773. Native reflection and nested type descriptors, stored booleans, fixed reflected invocation, persistent getter observation, mod lifecycle and native-console persistent Python have live proof. The requested private v0.1 scope and final analysis persistence are validated. Broader APIs remain explicitly unsupported.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Active goal and scope

NEXT ACTIVE GOAL (2026-10-08): port the user's actual BL4 Introspection Harness,
preserving its capabilities wherever technically achievable. Original source has
been located and audited; the unchanged core now supports live roots/search and
initial schema through an E33 adapter. Full parity is unfinished. Follow
INTROSPECTION_PORT.md for the feature inventory, SDK extension plan and evidence.
The completed private v0.1 checkpoint below is the foundation, not completion of
this new development goal.

ADDITIONAL ACTIVE REQUIREMENT (2026-10-08): one unified SDK management harness
with a native UMG frontend, independent console fallback (`mods`) and configurable
keybind manager. All three share one mod registry, settings store, action
dispatcher and lifecycle. Preserve the reusable Introspection Explorer. Audit
the actual installed MattsBL4ModsMenu, console_mod_menu, mods_base and native
keybinds before porting. Implement shared primitives and console fallback first;
UMG reverse engineering must not block them. Full requirements and all17 live
acceptance tests are preserved locally in USER_REQUEST_MANAGEMENT.txt. This is
additional scope, not a replacement or a completed feature. The current loader's
one-enabled-mod restriction must be resolved through shared session ownership.

Initial source discovery found MattsBL4ModsMenu.sdkmod and its package source
under BL4 sdk_mods/tools/matts_bl4_mods_menu, installed mods_base.sdkmod and
console_mod_menu.sdkmod, and keybinds Python wrapper/stubs/native module. Audit
and preservation are ongoing. CONSOLE_DUMPS.md records the short requested
diagnostic investigation and target-specific UMG/input research leads.

USER REQUIREMENT: Build an independent Python SDK for locally owned/offline Expedition 33. First capstone: our Python code enumerates real live objects through our independently validated native runtime layer. Static dumps, asset lists, and hard-coded names cannot satisfy it.

USER REQUIREMENT: Follow stages 0-12 in MILESTONES.md; no gameplay features first; no DRM/anti-cheat/authentication bypass; no public push or release. All new project material lives on D:. Existing installed tools may be reused.

The complete request is preserved locally in USER_REQUEST.txt and USER_REQUEST_CONTINUED.txt (excluded from Git).

PROVEN checkpoint (2026-10-08): independent Python live enumeration, useful reflection/bool reads, reflected getter invocation, persistent getter hooks, copied Python callbacks and a trivial mod lifecycle now work against the fingerprinted build. Stages 0-12 are complete within the documented private v0.1 boundaries. Release packaging and reduced whole-image analysis save/reopen verification passed. See MILESTONES.md and RELEASE_AUDIT.md for evidence and unsupported capabilities.
