# Menu startup validation — 2026-10-15

The core menu now starts when the current local controller owns a pause widget,
without waiting for an exploration pawn. Saved gameplay mods still require that
pawn (or the explicitly requested combat diagnostic gate). Menu construction runs
before optional mod restoration. Restoration yields between mods and defers new
enable calls while either the SDK menu or the game pause screen is open. A current
disabled preference overrides the startup snapshot.

Pause discovery can race garbage collection during SDK restart. Only a descriptor
identity change before attachment construction begins is retried on the next
bounded scan. Failures after construction starts retain the existing fail-closed
cleanup behavior; mutations are never replayed.

## Measurements

Fresh Steam launch and existing Continent save, with the user's optional-mod
preferences preserved:

| Milestone | Time after pause UI readiness |
| --- | ---: |
| Native Mods button attached | 5.282 s |
| Full menu prepared | 17.423 s |

Button construction itself took 2.175 s. Detached menu preparation took 12.136 s,
including 10.599 s of widget construction and 0.677 s of discovery. An earlier
session with the same saved mod set took approximately 42 s before menu readiness,
because optional mod enable work preceded menu preparation. These are individual
observations, not a controlled latency distribution.

**The first-load delay is reduced, not eliminated.** The 105-control widget tree
still uses individual retained creation calls. This change does not establish
sub-second first-load readiness and does not change that native construction cost.

## Checks

- 1,091 SDK tests and 79 standalone World Builder tests passed.
- Package integrity check passed after installing the reviewed local source files.
- Opened the game's pause screen with the existing AutoHotkey held-Escape helper.
- Clicked the actual Mods button; the controller recorded the native pause click
  opening the SDK menu.
- Switched to Keybinds, entered press-a-key capture for Flight descend, and captured
  R successfully while preserving that binding.
- Closed Mods and verified restoration of the game's pause screen and button focus.
- Opened the console and executed a Python health marker after Keybinds and capture.
- No private mod archives, assets, settings, screenshots, or controller logs are
  included in this source change or this report.
