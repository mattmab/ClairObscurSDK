Map Travel 0.2.2

Requires SDK native zone travel runtime v68.
Enable Map Travel in Pause > Mods. Open Map Travel from Pause, select a map
or grouped variant, then Travel to entrance. The continuous scroll list,
search and same-name groups are preserved.

When opened from Pause, the SDK first calls the game's Resume callback.
Travel calls the game's ChangeMapByName transition with the destination's
level-data ID and MainSpawnPoint tag. The game's spawn manager places the
party at that entrance during the same load. No console open command or
post-load TeleportToSafeLocation recovery is used. Unknown outcomes are
never retried automatically. Normal story and entrance triggers can run.

The catalog comes from the installed map manifest and live DT_LevelData.
Maps without an unambiguous normal route remain visible with travel disabled.
SDK menu resources are disposed before travel and rebuilt for the new world.

Archive inputs: mod.py, browser.py, README.txt and LICENSE only.

0.2.2: Numbered Unreal map names are compared with their complete suffix. Known route rejections remain in the pause menu instead of automatically reopening a menu with stale focus.
