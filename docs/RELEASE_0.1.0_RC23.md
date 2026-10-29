# ClairObscurSDK v0.1.0-rc23

Experimental prerelease with native runtime 251. Includes the tested SDK, Scene Editor, Cinematics, encounter tools and matching public mods.

## Changes since RC22

Flight movement no longer requires holding right mouse. WASD moves the camera, E/Q or Space/Ctrl moves vertically, Shift increases speed, and right mouse controls look. Native flight updates use a high-resolution clock and a 120 Hz work limit; paused flight avoids redundant Python sequence queries and track repainting. This is a work limit, not a promised rendering frame rate.

The Scene Editor now owns an independent flight camera. **Play from flight view** resumes at the current frame and **Start in flight view** rewinds while preserving your angle. You can move the camera during playback. Exit flight view restores the authored shot camera; closing the preview restores gameplay camera and input before retiring the viewport camera. Timeline button callbacks remain valid after flight feedback and drag scrubbing.

The native command bridge tolerates temporary game-thread stalls for up to 60 seconds while retaining the original request. Correlated pending notices never resend a command or repeat a spawn. Game exit, malformed acknowledgements and a terminal timeout still fail explicitly. This addresses the five-second command timeout observed during distant flight; streaming as the original stall trigger remains unconfirmed.

Cinematics preparation retries read-only controller discovery across loading races. Rejected menu focus before UI allocation can remain pending without tearing down the SDK; uncertain ownership failures remain explicit. Nested movie clipping preserves the original film clock while respecting the visible timeline interval.

## Install and controls

Close the game and SDK controller. Extract **Expedition33-SDK-0.1.0-rc23.zip** into the game folder beside `Sandfall`. Preserve existing settings and user maps. Start the game normally. Individual mod downloads and **Expedition33-OptionalMods-RC23.zip** require the matching RC23 SDK.

Drag timeline tracks to seek. Backspace hides or restores the timeline. In flight view, numpad 8/2, 6/4 and 9/3 move the whole scene; Alt gives fine movement. **Place whole scene here** places it in front of the flight camera. Save keeps authored placement. Placement does not automatically find the ground and may need vertical adjustment.

## Validation

The regression suite completed 3,044 tests successfully, with six skipped. Native DLL and probe builds passed with warnings treated as errors. An isolated integration test exercised the actual native controller against a synthetic thread that kept the original request queued for 6.2 seconds: it survived, dispatched once, and acknowledged the next command.

The installed native 251 build passed a cold launch and save load. Live Alone checks covered flight-angle playback across shot changes, keyboard movement during playback, rewind, pause, authored-camera restoration, repeated flight entry and preview cleanup. A subsequent live run travelled more than one kilometre horizontally from the original scene, placed the scene at the distant location, restarted playback and cleaned up without another SDK teardown. That run did not reproduce an engine stall longer than five seconds; the controlled integration test covers that wait path.

The release packages are built from the same frozen native, SDK and mod inputs as the tested local build. Release version and documentation are updated for RC23. Archives, including nested mod packages, are checked against the public input inventory and local-content exclusions.

## Experimental limits

The cinematic catalog is not exhaustive playback qualification. Large scenes still require seconds to import and prepare. Character replacement appearance and body/facial animation quality need scene-specific review. Repeated or multiple movies, speed changes and some camera-animation-owned edits remain unsupported. Original map geometry and campaign actors are not imported with a sequence. A persistent engine hang can still reach the bounded terminal timeout.

No personal mods, saves, settings, generated caches or private research captures are included.
