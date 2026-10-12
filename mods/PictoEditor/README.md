# Picto Editor

Enable **Picto Editor** in the SDK Mods menu, then open the game's Pictos menu.
Select an owned Picto to inspect and edit it. Select Health, Defense, Speed or
Crit Rate directly, adjust its multiplier, and choose Apply. Level, mastery and
Lumina cost use the same adjustment controls.

Supported ranges are stat multipliers 0–10, level 1–33 and Lumina cost 0–100.
Mastery applies to the shared passive unlock state. Additional attack counts and
new passive effects are not currently editable.

Successful edits are stored by Picto definition ID in
`SDK/settings/picto-editor.json`. The mod reapplies saved choices when the Pictos
menu becomes available after a reload. Keep the SDK settings directory when
updating the SDK or replacing this `.sdkmod` file. Disabling the mod stops its
operation; it does not reverse edits already applied to the game.

The editor uses verified game functions and identity checks. If the game build,
selected item or menu lifetime changes, a rejected operation is reported rather
than retried blindly. Some game-owned changes, including level or mastery, may
later be included in a normal game save. The mod does not edit save files or
request a save.
