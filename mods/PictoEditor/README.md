# Picto Editor

Enable **Picto Editor** in the SDK Mods menu, then open the game's Pictos menu.
Select an owned Picto to inspect and edit it. Select Health, Defense, Speed or
Crit Rate directly and adjust its multiplier. The rows preview the resulting
stat values using the live level-scaling table. Level, mastery and Lumina cost
use the same adjustment controls. Changed fields and the Picto title show `*`.
You can switch fields or Pictos without losing drafts. **Apply** commits all
staged fields for the selected Picto, then saves the confirmed overrides together.
Unapplied drafts last for the current mod session; only applied values survive
a restart. Zero removes that stat's contribution.

Supported ranges are stat multipliers 0–10, level 1–33 and Lumina cost 0–100.
Mastery applies to the shared passive unlock state. Additional attack counts and
new passive effects are not currently editable.

Successful edits are stored by Picto definition ID in
`SDK/settings/picto-editor.json`. The mod reapplies saved choices after gameplay
loads, before the Pictos menu opens. Keep the SDK settings directory when
updating the SDK or replacing this `.sdkmod` file. Disabling the mod stops its
operation; it does not reverse edits already applied to the game.

The editor uses verified game functions and identity checks. If the game build,
selected item or menu lifetime changes, a rejected operation is reported rather
than retried blindly. Some game-owned changes, including level or mastery, may
later be included in a normal game save. The mod does not edit save files or
request a save.

**Unlock status** opens the full catalog. It temporarily replaces the left Picto
list with a native, two-column scrolling list. Its header shows gameplay,
owned and locked counts, with All, Owned, Locked and Experimental filters.
Selecting a row updates both the details panel and the property editor.
**Tools** restores the stock list. Experimental definitions remain inspection-only.
Browsing never grants or equips an item. **Unlock Picto** validates ownership,
performs one guarded operation, then verifies the actual inventory before reporting
success. **Remove Picto…** stages removal; Apply commits it. Equipped items cannot
be removed. Applied overrides are retained if a removed Picto is unlocked again.

The catalog currently uses alphabetical ordering and ownership filters. Text
search and mastery filtering are not enabled. Per-Picto drafts are retained when
selection changes. Locked Pictos show verified definition cost and effect references;
inventory-dependent fields remain unavailable until unlocked. Effect descriptions
and acquisition sources are unavailable where the SDK cannot decode them.

**Unlock All Missing** in Tools first previews the number of missing gameplay
Pictos. Confirm submits one native queue, which attempts at most one inventory
change per actual game frame; Cancel stops the remaining queue. Inventory is
verified again at completion and confirmed ownership settings are saved together.
Completed, skipped and failed counts remain visible. Repeating a partially completed
operation rechecks inventory and skips existing items. No uncertain mutation is
automatically retried. Confirmed ownership is saved with the other overrides.

**Remove All** uses the same preview, confirmation, progress and cancellation
workflow for currently owned gameplay Pictos. Equipped Pictos remain protected
by the native inventory guard and appear in the failure count; other items can
still complete. Removal keeps saved stat, level, cost and mastery overrides for
later unlocking. Experimental definitions are excluded from both bulk actions.

Catalog scrolling keeps 26 entries loaded, including three rows above the
viewport and several below it. Circular row reuse updates only newly entering
entries during ordinary scrolling. Four-stat equipped cards use compact,
equal-width headings so their Level column remains readable. Metadata is read on
a worker; native controls are prepared incrementally while the editor stays usable.
Bulk ownership runs through the native frame queue while Python polls progress.
Other native commands remain synchronous and bounded. Older runtimes without
the queue capability use the slower sequential bulk fallback.

Clear restores the pre-override startup snapshot, including the original stat
list: an added Defense or Crit Rate row is removed instead of left at zero.
Disabling restores configured fields before detaching the editor, while keeping
saved settings for re-enable. This means the current save's starting state, not
factory defaults or historical progression. Exact stat restoration requires a
schema2 baseline captured on a fresh game start with the updated native runtime.
Failures are reported in disable diagnostics; equipped added Pictos retain the
existing removal protection. Restart after changing save slots before relying
on the recorded baseline. Disable restoration and UI cleanup can take several
seconds with a large configuration.

Master all Pictos and Unmaster all Pictos operate on currently owned items.
Both use the native frame-paced queue when `picto_mastery_batch_protocol=1`:
one item per actual engine frame, one final inventory/mastery readback, and one
preferences update for confirmed results. Mastering reads each passive's own
unlock threshold. Unmastering resets both the learnt flag and partial battle
progress to zero. Cancellation retains only confirmed completed edits. The open
menu refreshes when the batch finishes. Older runtimes use the slower guarded
per-item fallback.
