# Target-derived UMG layout values

2026-10-09; Steam build23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
This is a candidate value contract, not enabled struct invocation or a rendered
Mods Menu. The running v10 host is unchanged.

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

Neither codec is wired into invocation yet. The next native backend must validate
the struct identity and full allowed field shape again on the game thread, match
the parameter's FStructProperty reference, and reject unsupported profiles before
dispatch. Preserve old capability rejection, current packet correlation and
unknown-outcome behavior. Then expose copied struct inputs/results through the
SDK and original Harness adapter, and test position/size round trips on an
SDK-owned widget before connecting menu layout to the shared registry.

Local raw evidence: `evidence/widget-layout-schema.json`,
`evidence/widget-layout-schema.log`, `evidence/widget-layout-thunks.json` and its
argument/tool files. No functions discovered during this inventory were executed.
