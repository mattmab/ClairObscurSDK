# E33 Live Object Viewer 0.1.1

An E33-native implementation of the core browsing workflow in the supplied
Oak2 Live Object Viewer. It uses this checkout's E33 Harness and native UMG
menu service. It shares SDK Management's cached panel, avoiding a second tree
that exhausts the runtime's 128-slot retention pool (native error 401).
No Borderlands offsets, gear data or PythonSDK dependencies are
copied. The native panel uses the SDK's existing E33 menu layout.

## Start

1. Start E33 normally and load a save.
2. Run **Launch Native Mods.cmd** in the game folder (one controller per game).
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
