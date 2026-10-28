# Owned sequence scrubbing qualification

Native v217 adds `sequence_seek_protocol=1`, SequenceOwner operation 8.
It controls only the factory-created player already retained by that owner.
The controller cannot choose a player, actor, dispatcher or engine parameter
layout. The current captured menu/controller/world must still match.

The request carries the exact observed `SetPlaybackPosition` function identity,
an int32 player frame and binary32 subframe in [0,1). Its remaining fields are
zero. Native code validates the complete function and nested playback-parameter
reflection profile, including Timecode, FrameTime and both byte-backed enums.
The supported function thunk is RVA 0x2d6a350 on the fingerprinted executable.
The 56-byte parameter frame is built locally: Frame position mode, Scrub update
method, bHasJumped true, empty MarkedFrame FString and zero unused fields.

GetStartTime/GetEndTime disassembly establishes the owned player's start and
duration at offsets 0x298/0x29c and frame rate at 0x300. Requests outside its
start/end range, overflow, nonfinite subframes and fractional positions beyond
the endpoint are rejected before dispatch. Outcome becomes unknown immediately
before ProcessEvent. A fault or world/context loss after dispatch quarantines
the owner; a known preflight rejection leaves it closeable.

`OwnedLevelSequence.seek_frame()` stabilizes and retains function metadata once,
pauses an actively playing preview, and permanently invalidates its natural-end
tracking. A scrub to the endpoint cannot establish natural cinematic completion.
Authored ticks convert through rational source/player rates, with correct
negative-frame flooring and canonical float32 subframe rounding.

Live QA-map evidence using the reviewed Simon intro:

- The engine returned frame 300 with subframe 0.25 exactly, then frame 600.
- The first seek took 244 ms including initial metadata preparation; the second
  took 16 ms. A backward seek to frame 150.5 took 17 ms.
- Frame -100 was rejected with known no-dispatch error 1691. The same owner then
  accepted the valid backward seek without restarting the SDK.
- Seeking exactly to end frame 2174 returned 2174.0. Completion tracking was
  already cancelled, and explicit cleanup completed normally.
- With the QA helper's authored light visibility repair enabled, frames 600 and
  1600 visibly showed different shots, actor poses and party placement. The later
  shot included Verso's subtitle. Reverse seeking still returned the requested
  cursor. Cleanup restored the exploration camera and original light visibility.
- Native packet and schema fixtures compiled with /W4 /WX. Adversarial cases
  include string width/offset changes, enum remapping, cycles, stale identities,
  struct-size changes and disabled context. Python tests cover feature gates,
  response consistency, retained metadata and completion cancellation.
- Full regression: 2534 tests passed with six skips. The explicitly packaged
  v217 local install verified successfully; the original 180-file save/config
  baseline remained unchanged. No GitHub publication was performed.

This qualifies the owned scrub mechanism, not source-asset editing or arbitrary
sequence safety. Persistent timeline edits still need private native sequence
cloning/application. Character binding replacements and Encounter Blueprint NPC
integration are unfinished. Cold portable dispatch also remains expensive: the
measured run spent about four seconds preparing endpoint observations and about
nine seconds in preparation after input lock. These remain optimization targets.

## Scene Editor source-preview toolbar

The local revision 36 candidate exposes reviewed source previews from the
authored timeline screen. SimonIntro was opened through the actual UI in
Map_BattleTesting, sought to frame 600 with its actor visible, played forward
with the authored actors, and closed back to the editor. The toolbar also
provides pause, frame stepping and return-to-start controls. Those additional
controls have regression coverage; this run did not individually qualify every
button live. Saved edits are explicitly not applied by this source preview.

Two UI defects were corrected during qualification: EditableText SetText must
remain outside the numeric setter batch, and GetText must read and release its
invocation result rather than stringify the invocation object.

Completion preparation no longer performs a redundant completion poll before
the first Play. Existing pre/post context validation and idle-player checks
remain. A subsequent QA portable dispatch measured 2296 ms for completion
preparation and 7253 ms for preparation after input lock, compared with roughly
four and nine seconds respectively in the previous measurements. This is one
comparison, not a cold-launch benchmark or a claim that dispatch is seamless.

Revision 36 passed 2543 Python tests with six skips and was installed locally
using explicit candidate inputs. The 180 original save/config baseline files
remained unchanged. No publication occurred. Private sequence cloning/edit
application, character replacement and Blueprint NPC integration remain open.
