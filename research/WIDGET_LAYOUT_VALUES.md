# Target-derived UMG layout values

2026-10-09; Steam build23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
The opt-in v11 backend implements this value contract with native schema checks.
It does not establish a rendered Mods Menu. Live results are recorded below when
available; offline tests alone do not prove engine behavior.

`scripts/inspect_widget_layout.py` reads live function descriptors and recursively
expands their struct references. On game PID 25560 it found all 27 requested functions,
with no missing names. Identity-selected descriptors corroborate these profiles:

| Struct path | Bytes | Exact reflected fields |
| --- | ---: | --- |
| /Script/CoreUObject.Vector2D | 16 | X:double+0, Y:double+8 |
| /Script/CoreUObject.LinearColor | 16 | R/G/B/A:float+0/+4/+8/+12 |
| /Script/SlateCore.Margin | 16 | Left/Top/Right/Bottom:float+0/+4/+8/+12 |
| /Script/Slate.Anchors | 32 | Minimum:Vector2D+0, Maximum:Vector2D+16 |

Each has no reflected superclass and no additional reflected fields. The schema
validator checks full package/type path, ScriptStruct class, extent, field count,
ownership, names, types, offsets, dimensions and nested identities. Reflection
does not itself prove arbitrary structs are trivial or callable. Only these four
profiles are candidates, supported by the target thunk evidence below.

## Executable evidence

Ghidra thunks `1430976a0` and `143097cf0` decode Vector2D for CanvasPanelSlot
SetPosition/SetSize, then narrow the two doubles into slot float storage.
GetPosition `143093ea0` and GetSize `1430940c0` widen the corresponding floats
back into a 16-byte double pair. The optional Slate update path operates separately
from that parameter storage. Consequently, the candidate codec rejects nonfinite
components and finite doubles beyond float range; it does not assume all finite
double values are safe inputs for UI setters.

Button.SetBackgroundColor `143095eb0` copies a 16-byte LinearColor into the button,
then updates its Slate representation when present. CanvasPanelSlot.SetOffsets
`143097160` copies the 16-byte Margin. SetAnchors `143095c60` copies 32 bytes for the
two Vector2D members. Their parameter paths show numeric copying without owned
string/object-pointer parameter state. Raw property mutation is not used.

The read-only dump also identifies boundaries requiring separate work:

- TextBlock.SetText accepts 16-byte TextProperty; this is not a Python string or
  a trivially copied text value.
- SlateFontInfo is 96 bytes and includes object references, FName and nested
  outline settings. It is deliberately outside the numeric profiles.
- SlateColor is 20 bytes with LinearColor and an enum; it is not interchangeable
  with LinearColor.
- UIOnlyEx/GameAndUIEx input-mode calls include an EnumProperty mouse-lock mode.
  Names/descriptors alone do not verify focus restoration or enum invocation.

## Implementation and next integration

Internal `_pod_values.py` validates observed profiles, packs exact named numeric
fields and decodes immutable copied results. `native/pod_value_codec.h` provides
the matching width/numeric validator; its standalone /W4 /WX fixture passes four
profiles and seven invalid-value/boundary cases. Python tests cover double versus
float encoding, nested values, immutable results, changed/owned/extra fields,
wrong nested identities, nonfinite values and narrowing overflow.
The complete source Python suite passes all 146 tests.

The codecs are connected to v11 invocation. `Session(pod_values=True)` selects
the separately named controller/runtime and requires `pod_value_protocol:1` in
the handshake. Call packet v2 preserves the existing byte layout, adds four
explicit kinds and stores the observed ScriptStruct identity in the constraint
slot. Older sessions reject v2. Both retained and ordinary calls share the same
validator; numeric structs acquire no native-owned storage or lease tokens.
Native schema rejection is not dispatched; invalid numeric results after a call
leave its outcome unknown and must not be retried. Existing object-output
retention and pointer scrubbing remain in place.

Python accepts exact named dictionaries or same-type NumericStructValue copies,
validates live descriptors, and returns immutable typed mappings. For example,
with observed slot/function identities:

```python
sdk.invoke(slot, set_position, InPosition={'X': 160.25, 'Y': 32.5})
position = sdk.invoke(slot, get_position).return_value
```

`launch.cmd management --pod-values` exposes this opt-in backend. The original
Harness's typed `$struct` adapter is now implemented; see INTROSPECTION_PORT.md
for its separate validation. Its core is unchanged. Arbitrary structs, FText/font/FKey ownership,
EnumProperty input modes and visible/focused menu behavior remain unsupported.

Native gate follow-up: `pod_schema.h` now implements the exact four-profile
walker; `target_pod_schema.h` supplies the real game-thread, GC/shutdown, registry,
name and local-memory operations. It verifies package/type identity, no inherited
or extra fields, field ownership, exact vtables/flags/types/dimensions/offsets,
and recursively checks Anchors' two references to the same Vector2D structure.
The parameter gate binds an FStructProperty's reference and width to that profile.
The enclosing invocation must still validate parameter ownership/layout and
contain access faults. No native constructor, setter or dispatcher is called.

`verify-pod-values.cmd` compiles the real adapter/template combination with
/W4 /WX and runs a synthetic-memory fixture through the actual schema walker.
Four valid profiles and parameter binding pass; 24 altered-schema, identity and
context cases are rejected. This is offline validation, not a claim that the
gate has run on the game's thread. Native packet tests cover explicit version
gating, zeroed outputs, identity/width checks and invalid numeric values. The
151-test Python suite includes cross-language packets for all four profiles,
return decoding, altered descriptors and pre-write capability rejection.

`scripts/verify_live_widget_layout.py` runs through the existing retained-child
lifecycle probe on the persistent owner thread, with no viewport or input change.
It checks position/size readback and margin effects, submits anchors/color, then
removes the child and compares the holder baseline. Dispatch-only color/anchor
results are explicitly distinguished from readback and rendered behavior.

## Live v11 result

2026-10-09 03:38:37 local, game PID 25560, persistent Python PID 8316 and native
controller PID 4152: the complete scoped probe passed. SetPosition/GetPosition
round-tripped `{X:160.25,Y:32.5}` and SetSize/GetSize round-tripped
`{X:640,Y:360}`. SetOffsets with `{Left:120,Top:80,Right:500,Bottom:300}` was
independently checked by subsequent position/size calls. SetAnchors and
Button.SetBackgroundColor returned from native dispatch; no rendered effect or
independent color/anchor readback is claimed. The child was removed, its count
returned to zero, and the exact native holder baseline was restored.

The v10 controller shut down cooperatively before v11 started; no second
persistent controller was attached. Native console Python dispatch and the
integrated mod host remained operational. Live evidence is
`evidence/widget-layout-live.json` and `logs/management-v11.stderr.log`.
The new pair is included by the packaging script, but isolated-package startup
and fresh-game relaunch for v11 still need validation.

Clean-source package check: candidate `20261009T074043Z`, source `9b5ee40`,
contains 226 manifest-hashed files including both v11 binaries. Directory and ZIP
hashes all match; logs, settings and raw evidence are excluded. ZIP SHA256:
`e6da3c689328b43f1f96922df5f4fa01c5179ee86440c05d074bc14311d8ff2c`.
Isolated CPython 3.13.15 loaded the bundled SDK and ran 151 tests successfully
(two native-fixture tests skipped because fixture executables are not bundled).
This is packaging/integrity validation, not live startup from that bundle.
Evidence: `evidence/pod-v11-package*.json` and `pod-v11-package-tests.log`.

Local raw evidence: `evidence/widget-layout-schema.json`,
`evidence/widget-layout-schema.log`, `evidence/widget-layout-thunks.json` and its
argument/tool files. No functions discovered during this inventory were executed.
