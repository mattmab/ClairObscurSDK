# Authored frame range observation

Executable SHA-256: `218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618`.
This is a read-only codec qualification, not a mutation or generic struct ABI.

Reflection identifies `/Script/MovieScene.MovieSceneFrameRange` as a 16-byte
ScriptStruct without reflected members or a superclass. MovieScene.PlaybackRange
has offset 264; MovieSceneSection.SectionRange has offset 152 and the same type.

Sequence-player initialization at RVA `0x2d53700` follows the sequence's
MovieScene and, at `0x2d5387a`, copies 16 bytes from `MovieScene + 0x108`.
At `0x2d5389a` it loads the first eight-byte bound. `test cl,cl` selects the
increment at `0x2d538a6`, then `shr rcx,0x20` obtains the signed frame payload.
The upper bound is loaded at `0x2d538bd`; `cmp cl,1` selects its increment.
The signed integer tables at RVAs `0x72b7da8` and `0x72b7db0` both contain
`(0,1)`. These establish exclusive lower and inclusive upper adjustments when
converting to a half-open integer interval.

Section code at RVA `0x2d519e0` skips the lower endpoint when the byte at +0x98
equals 2 (`0x2d51a00`), otherwise copies its value at +0x9c. It likewise skips
the upper endpoint when +0xa0 equals 2 (`0x2d51a32`). The codec therefore admits
only kinds 0/exclusive, 1/inclusive and 2/open, with values at bound +4.
It never emits padding or the unused payload of an open endpoint.

The native reader still requires the exact executable, qualified package/name,
width and empty reflected schema, and repeats the complete stored observation.
The Python decoder admits this native payload only for that exact ScriptStruct.
Tests cover signed endpoints, open bounds, invalid kinds and extents, malformed
payloads and wrong-type injection. Native-array fixtures separately check
content/header changes and bounded copied prefixes.

Live SimonIntro inspection observed root `[74400,1739200)` and nested
`[-152000,1529600)` ranges at 24000 ticks/second. Preserve each sequence's time
space; nested range offsets must not be flattened without its subsection
parameters. The root/nested time differences are authored data, not an error.
