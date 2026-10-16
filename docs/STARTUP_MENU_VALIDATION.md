# Menu startup validation — 2026-10-15

The core menu starts when the current local controller owns both a pause widget
and an exploration pawn (or the explicitly requested combat diagnostic gate).
A pause widget alone was observed during loading, before safe attachment.
Menu construction runs
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

| Milestone | Previous | Construction batching |
| --- | ---: | ---: |
| Native Mods button attached | 5.282 s | 5.213 s |
| Full menu prepared / SDK ready | 17.423 s | 9.058 s |

Times begin at the respective readiness check, not at process launch. The new
check also requires the gameplay pawn, so these are not identical starting gates.
Button construction itself took 2.143 s. Detached menu preparation took 3.785 s
(previously 12.136 s), including 2.166 s of widget construction (previously
10.599 s) and 0.664 s of discovery. An earlier
session with the same saved mod set took approximately 42 s before menu readiness,
because optional mod enable work preceded menu preparation. These are individual
observations, not a controlled latency distribution.

The 105-control widget tree now creates independent objects in groups of at most
24 using a capability-gated native operation whitelist. Each group's outputs are
retained and observed before dependent calls are planned. Failures abort ownership
without replay. Older runtimes retain the existing individual-call path.

First-load readiness is still not sub-second. The fresh automatic launch completed
successfully after two earlier loading-time failures reported GPU crash dumps,
including one with the previous runtime restored. This validates the new gate for
this run; it does not establish a definitive cause for those crashes.

## Checks

- 1,097 SDK tests and 79 standalone World Builder tests passed.
- Native construction whitelist/packet fixtures and release build passed.
- Package integrity check passed after installing the reviewed local source files.
- Opened the game's pause screen with the existing AutoHotkey held-Escape helper.
- Clicked the actual Mods button; the controller recorded the native pause click
  opening the SDK menu.
- Switched to Keybinds, entered press-a-key capture for Flight descend, and captured
  R successfully while preserving that binding.
- Fresh automatic launch: pause button opened Mods and Keybinds remained usable.
- Text slider changed from 1.35 to 1.85 and back to 1.35 in the fresh session.
- All nine saved enabled mods restored after leaving pause. World Builder's
  separate options/keybind panels rendered correctly; the global keybind list
  scrolled to its lower entries. World Builder has no registered options, so this
  run does not validate overflowing options content.
- AutoHotkey status reporting tolerates a missing stdout handle and writes a local
  test log; held Escape completed successfully without the invalid-handle dialog.
- Closed Mods and verified restoration of the game's pause screen and button focus.
- Opened the console and executed a Python health marker after Keybinds and capture.
- No private mod archives, assets, settings, screenshots, or controller logs are
  included in this source change or this report.
