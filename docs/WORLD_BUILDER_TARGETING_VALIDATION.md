# World Builder targeting validation — 2026-10-15

The source following RC11 removes the 32-bound shortlist limit, starts each
query with scene depth to reject occluded props, and keeps capture identities
paired with their readback. Camera movement invalidates pending results and
old hits no longer seed new searches.

Validation:
- Release runtime/probe build passed with MSVC warnings treated as errors.
- All 79 World Builder Python tests passed.
- `native/builder_targeting_fixture.cpp` passed: more than 32 overlapping
  bounds, vanished hits, unsupported foreground occlusion, shared capture
  ownership, and camera movement while readback is pending.
- Local installed runtime integrity check passed.
- Live Continent test: two overlapping cubes selected the foreground cube;
  after moving it aside, the crosshair selected the rear cube. A mouse drag
  selected the foreground component and produced an undo entry. Both test
  cubes were removed; tracked test edits and undo entries returned to zero.
- Console commands continued working throughout the live checks. An ordinary
  world static mesh was also identified after the controlled cube test.

These checks do not establish selection support for every model. Individual
foliage/instanced-mesh instances remain unsupported. Dense overlap can still
increase targeting latency because candidates share one asynchronous target.
The published RC11 archive has not been replaced by these source changes.

To run the native regression from an x64 MSVC developer prompt:

```bat
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:build\builder_targeting_fixture.exe /Fo:build\builder_targeting_fixture.obj native\builder_targeting_fixture.cpp
build\builder_targeting_fixture.exe
```

A pre-restart local builder-map backup restored all 28 serialized objects after
retrying in the original loaded area. Earlier attempts failed on a component
transform and on an unloaded component path; the precise transform rejection
cause remains unconfirmed. The original backup was retained unchanged. This
is not evidence that map loading is reliable across streamed-area changes.

## Reader recovery follow-up (0.30.1)

Closed persistent menu readers are discarded at the next operation boundary;
failed widget bodies are not replayed. Recovery restarts status polling and
preserves scene edits. The expanded World Builder suite passed 81 tests.
Live F8 on, F7 open, F7 close and F8 off all passed. Console assertions confirmed
28 tracked edits retained, a healthy reader and finite polling deadline.
SDK RC12 packages the targeting changes described above; the original RC11
archive remains unchanged. Final archive integrity is separate from these live
checks of the installed build.
