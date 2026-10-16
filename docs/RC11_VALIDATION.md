# RC11 and standalone World Builder validation

This report describes the **original published RC11 archives** identified below.
Later source changes `569e15e` and `03ccb88` have separate
[startup/menu validation](STARTUP_MENU_VALIDATION.md): 1,097 SDK + 79 World Builder
tests, faster construction, a gameplay attachment gate, actual pause-button access
using AutoHotkey, and console checks after Keybinds. Those follow-up results do
not change the archive hashes or historical measurements in this report.

Tested on Windows, 2026-10-15, with the supported Steam executable and a loaded
Continent save. The existing SDK, mod archives and preferences were backed up
before testing. The release ZIP was extracted with no inherited SDK settings;
World Builder was then installed from its separate archive.

## Automated checks

- 1,088 SDK tests passed.
- 79 standalone World Builder tests passed.
- Native release runtime, research probe and thumbnail worker built with /W4 /WX.
- Native 105-control focus/tab reuse and key-capture fixtures passed.
- Release launcher --check passed on the extracted installation.
- ZIP integrity, runtime license hashes and notices verified.
- Base SDK contains three core mod archives; World Builder is absent from it.
- Standalone World Builder contains its mod archive, documentation and license,
  without an SDK runtime, settings, logs or Python caches.

## In-game checks

- Normal game launch automatically started the clean SDK.
- Pause entry attachment completed 4.826 seconds after gameplay-ready detection
  (2.154 seconds for attachment itself). Detached menu warmup took 12.104 seconds.
- Console opened and `mods ui` opened the new menu.
- Standalone World Builder loaded and enabled through the Mods menu.
- Global Keybinds opened without SDK teardown; menu navigation and reopening worked.
- Press-a-key rebinding and persisted camera mapping were exercised during the
  first clean pass, including entering/exiting the camera with the rebound key.
- Final clean pass exercised the text slider from 1.35 to 2.04 and Reset to 1.35.
- A temporary 20-option/25-keybind fixture verified separate physical wheel
  scrolling: scrolling either panel retained the other panel's position.
- World Builder enabled while Mods owned focus without catalog-prewarm failure.
  After closing Mods, F7 opened the catalog and F8 returned to gameplay.
- Catalog folder navigation, generated thumbnails, selected-asset preview,
  spawning SM_Bowl_01a and clearing the tracked scene passed (1 then 0 tracked).
- World Builder camera settings rendered; console remained usable afterwards.
- SDK shutdown removed the pause entry and exited its controller cleanly.
  The temporary fixture was removed before restoring the user's configuration.

## Corrections and limits

Clean-install testing caught a stale runtime path and an undersized native widget
ownership budget in the release launcher. Both were corrected and the final ZIP
was re-extracted and tested. Catalog prewarming now waits while another menu owns
focus; its former failure was also retested on the final standalone archive.

The first-load menu still requires the measured background warmup; this is not an
instant-start claim. Automated Escape taps did not confirm opening the game's
pause menu, so pause-button click-through is not claimed by this run. Menu access
through the console was verified. Other resolutions, controller input, combat and
map travel were not included in this live acceptance pass.

World Builder remains experimental. Some enumerated assets fail thumbnail loading
with ASSET_NAMES_NOT_LOADED and are skipped. The camera speed caption is tightly
spaced against the preceding field at the tested resolution. Not every catalog
asset or builder operation was exercised in game; scene, bulk-operation and camera
edge cases also have automated coverage.

## Tested archive hashes (SHA-256)

- Expedition33-SDK-0.1.0-rc11.zip:
  `c09a1c92dc7089013abf5f1ad650b3cc5df46177e8527ea41a85a32382828b78`
- E33WorldBuilder-0.30.0.zip:
  `ecc92ec24a01700c14e31241f855741c0b65fcbcbaa8f51813114609b479d2c8`
