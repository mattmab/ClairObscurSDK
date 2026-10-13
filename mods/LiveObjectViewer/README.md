# E33 Live Object Viewer 0.2.0 candidate

## Overhaul status (October 12, 2026)

Compared against the supplied Oak2 0.10.0 README. This is an independently
implemented E33 candidate, not a claim of full Oak2 parity. It is bundled with SDK RC5.

- Eight browser rows; Inspect tools contains monitoring, snapshots, comparison,
  bookmarks, object search presets, schema, roots and manual refresh. Page control
  cycles back to the first page. One shared 12-control UMG panel is retained.
- `lov_filter text` filters names; `lov_filter value:text` filters already observed
  values. `lov_mode simple|advanced` controls friendly/raw labels.
- Select a direct scalar property, then Inspect tools → Live monitoring. Only that
  property is polled, at most once per second, with adaptive backoff for slow reads.
  Closing, changing nodes, or a failed read stops monitoring. No background scans
  while hidden. Object identities are checked before rereading.
- Snapshot comparison includes removed fields and ignores display filters when
  capturing its baseline. Bookmarks are bounded to 32, session-only and re-resolved.
- Guarded editing: select a direct property; `lov_edit` accepts a boolean, number,
  null or an identity-bearing reference JSON value. Inspect tools → APPLY
  staged edit (or `lov_apply`) performs an explicit guarded write. Drafts expire in
  30 seconds, reject changed before-values, and are consumed before dispatch.
  `lov_cancel` discards a draft. Writes are not automatically undone.
  Reference properties stay selected for editing; Inspect tools → Follow selected
  object reference navigates to the referenced object. The staged expected value
  is carried into native compare-before-write validation.

- Inspect tools page three offers a boolean toggle and numeric +1/-1 staging.
  For an exact value use `lov_edit 1.25` or `lov_edit true`, then `lov_apply`.
  Supported scalar descriptors are bool, signed int32, float32 and float64.
  Writes run on the game thread with identity, type, owner, extent, flags and
  expected-value checks. Packed bool writes preserve adjacent bits. Read-only,
  replicated, parameter and accessor-backed descriptors are rejected. These are
  stored-field edits; engine setter side effects are not synthesized.

**Not implemented:** string writes, native text entry, multi-property watch
charts, Oak2 item serials/definitions, arbitrary nested container edits.

Live evidence (October 12): viewer-v2 opened while mounted on Esquie, accepted
mouse navigation, displayed live LookUpDownRate and closed with Escape. The
Harness/viewer edit path changed bIsVariable false→true→false on an SDK-owned
widget and LookUpDownRate 1.0→2.25→1.0 on the possessed pawn. Both passed native
dispatch, readback, polling and restoration. MinDesiredWidth was safely rejected
for an unsupported accessor descriptor. Int32/float64 editing remains unverified
live. Party-screen focus rejection and travel still need separate acceptance.
Raw local evidence: `.agent-work/viewer-scalar-live-result.json`.
Large object-reference property batches can still be slow; focused scalar
monitoring does not scan those references.

Mounted input uses verified UIOnlyEx/GameOnly calls and restores viewport focus.
Preparation/attachment and focus run on consecutive engine frames through the
existing message-pump dispatcher, using the same frame counter as Picto Editor.
This is not a new engine Tick hook.

The following describes the original viewer and is retained as historical context;
its six-row UI and 128-slot pool notes do not describe this candidate.

An E33-native implementation of the core browsing workflow in the supplied
Oak2 Live Object Viewer. It uses this checkout's E33 Harness and native UMG
menu service. It shares SDK Management's cached panel, avoiding a second tree
that exhausts the runtime's 128-slot retention pool (native error 401).
No Borderlands offsets, gear data or PythonSDK dependencies are
copied. The native panel uses the SDK's existing E33 menu layout.

## Start

1. Start E33 normally and load a save.
2. Use installed SDK autostart or `SDK/launch-sdk.cmd` (one controller per game).
3. Open the backtick console and enter:

```text
mods load LiveObjectViewer
mods select sdk.live-object-viewer
mods enable
lov
```

The mod also appears in SDK Management with an **Open Live Object Viewer**
action and an initially unbound **Toggle Live Object Viewer** keybind.
Choose an unused key in the Mods menu, or use `mods bind toggle F8` after
selecting this mod. Close other SDK panels before opening this one.

If upgrading after the v0.1.0 error 401, restart the game and SDK controller
before loading the viewer again. The failed old construction retains its
cleanup owner; repeating `lov` cannot clear it. The fix requires the current
SDK Management shared-view service and checks for it before allocating anything.

Click a root group, then an object to inspect it. Click properties to explore
observed structs/arrays or follow object references. **Back** rereads the prior
node. **Refresh** rereads the current request. Pages show six rows; **Next
reflected batch** requests the next bounded batch from the live catalog.
Search can have an empty batch with another batch available.

## Console commands

```text
lov                         # open native panel
lov_close                   # hide panel
lov_roots                   # World/GameInstance/LocalPlayer/PlayerController/Pawn
lov_search Actor player     # class (including subclasses), optional path text
lov_search Class movement   # search loaded classes
lov_schema                  # selected object's inherited properties/functions
lov_schema Actor            # explicit class schema and function parameters
lov_refresh
lov_back
lov_next                    # next reflected batch
lov_snapshot                # fresh baseline for this node and request batch
lov_changes                 # refresh; toggle changed/new fields only
lov_snapshot_clear
lov_dump                    # export last observation, request and baseline
```

Search/schema commands update the open panel. If closed, use `lov` afterward.
Full values and explicit unsupported/truncation markers are included in JSON
exports under `logs/LiveObjectViewer`. Long native text is clipped by the SDK;
the export retains the bounded observation in full.

Snapshots are explicit, scoped to the exact request/batch and nested path, and
mark changed/new rows with `*`. They do not detect deleted fields or compare
unobserved portions of collections. Roots may include multiple loaded worlds
and pawns; their paths distinguish them. A reference is resolved again by
class/path on each request, not pinned across object destruction or travel.

## Current limits and lifecycle

This first version is read-only and manual-refresh. Native text entry, automatic
polling, editing and function execution are not implemented. Function schemas
are browsable, but choosing a function never invokes it. E33 decoder errors and
collection truncation stay visible; no full Oak2 feature parity is claimed.

The viewer borrows SDK Management's panel and releases only its own view when
disabled. SDK Management owns widget cleanup and travel recovery. To unload:

```text
lov_close
mods select sdk.live-object-viewer
mods disable
mods unload
```

Load/enable again after travel. Failed native cleanup preserves its owner and
raises an error, allowing a later retry instead of discarding live resources.

Automated navigation, snapshot, paging, failure and lifecycle tests run without
the game. In-game layout/input and gameplay/travel acceptance require a running
E33 session and are not yet verified for this viewer.
