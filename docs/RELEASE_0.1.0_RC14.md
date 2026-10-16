# SDK 0.1.0-rc14 - World Builder 0.31.1

Fixes World Builder stopping when the game unloads a built-in prop that is
being carried out of its streamed area. Install the matching RC14 SDK and
World Builder 0.31.1; replacing only the mod does not update the native fix.

## Changed behavior

- Detect expired selected actor/component identities before movement and nudging.
- Release the unloaded selection and clear carry/drag state while keeping
  freecam and the rest of the scene active. A fresh click starts the next grab.
- Preserve normal error handling for failures unrelated to an unloaded object.
- Retains live duplication with compound XYZ offsets and Apply, Delete selection,
  Alt+Z/Alt+Y deletion and duplication history, and F7 returning to props.

## Level streaming

Moving built-in world objects may reset their positions when the game unloads
and reloads those assets through level streaming. Custom-placed props do not
participate in level streaming and are unaffected by those unload/reload cycles.
Ordinary visibility culling does not recreate an object or reset its transform.
This note is also available in World Builder's Maps tab.

## Downloads and installation

Close the game and SDK, then extract these beside Sandfall:

- Expedition33-SDK-0.1.0-rc14.zip: required SDK and native runtime.
- E33WorldBuilder-0.31.1.zip: World Builder mod in SDK_Mods.

Preserve SDK/settings for maps, preferences and existing thumbnail caches.
For a first install, enable World Builder in Pause > Mods. The base SDK bundles
Management, Introspection Harness and Live Object Viewer. Map Overlays remains
separate and is not bundled here.

Optional downloads:

- E33WorldBuilder-thumbnails-rc14.zip: neutral asset thumbnails and portable
  importer. Extract separately and follow README.txt with the game/SDK closed.
- ClairObscurSDK-rc14-source.zip: matching source and build instructions.
- SHA256SUMS.txt and VALIDATION.txt: checksums and validation scope.

## Verification

Native warnings-as-errors build and motion regression fixture passed. The
fixture covers expired actor/component identities, loss during reads/writes,
continued movement, healthy carrying and unrelated failures.

After a fresh game launch, a held test prop was destroyed and garbage-collected.
World Builder cleared selection/carry/drag, moved the camera 10 units, and
remained active with zero native/tick errors. The original level-streaming
route was subsequently tested by the user and confirmed working on 2026-10-16.
Published native binaries are hash-matched to that verified local installation.
World Builder's 107 tests and four native command wire tests also pass.

Archives are checked for integrity and private content, including nested mod
archives. Personal settings, saved maps and map previews are excluded. This
is not a claim that every feature was retested from a downloaded RC14 archive.

## Remaining limits

The supported executable fingerprint and general installation limits remain
as documented in INSTALLABLE_RELEASE.md. Unsupported landscape/individual
foliage, transparent surfaces without depth, and unavailable streamed assets
remain limited. Save maps in their original level. Undo history is session-local.
