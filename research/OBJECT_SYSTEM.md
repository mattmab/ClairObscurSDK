# OBJECT_SYSTEM

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: our native reader and Python API enumerate live objects in Steam build 23765773. Reflection, invocation, hooks, and the full SDK remain unfinished.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Reference lessons, target still unknown

OBSERVED in BL-SDK: native registry access and FName resolution underpin lookup. A Python wrapper's existence is independent of the engine object's lifetime. py::nodelete avoids deleting engine-owned memory but cannot guarantee the pointer stays valid. Reference WeakPointer uses registry index/serial validation where supported.

HYPOTHESIS to test for Expedition 33: a chunked object registry and interned name pool. Do not import chunk size, entry stride, flags or offsets. Evidence required: static access paths plus runtime identity consistency across multiple objects and repeated observations.

Live evidence now supersedes the initial untested registry hypothesis; see the validated layout below.

## Validated object and name subset

PROVEN on Steam build 23765773, shipping SHA256 `218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618`.
Registry RVA `0x9361b60`; name pool RVA `0x92aadc0`. These are resolved through independently derived unique instruction signatures, then checked against the recorded build. No absolute process address is assumed.

Ghidra registration routine `1413ab9d0` and chunk allocator `1413aae40` establish 65,536 slots per chunk and 24-byte slots. Registry+0x10 points to the chunk table; count is registry+0x24. Object identity fields: index+0x0c, class+0x10, FName+0x18, outer+0x20. Caller `1413aeba0` corroborates the global and assignments.

Name formatting routine `1411bcab0`, entry copy `1411a3660`, and initializer `14119e730` establish block pointers at pool+0x10, block=id>>16, byte offset=2*(id&0xffff), two-byte entry header, length=header>>6, UTF16 flag=header&1, payload+2. Nonzero number appends underscore and number-1.

OBSERVED: native first-32 query in PID25988; Python full query returned 96,053 occupied stable observations from 96,605 slots, max index96,604, spanning two chunks. Class and metaclass pointers resolve back through their registry indices; Class is its own metaclass. Name ID0 resolves None. Game remained at its main menu after the queries.

Reproduce with `scripts/verify_live_enumeration.py`. Local evidence: `evidence/python-live-enumeration.json`, `.log`, `mcp-object-registration-followup.json`, `mcp-anchor-disassembly.json`, `mcp-namepool-init.json`. Snapshots are not atomic across GC; rereads detect some changes but do not pin objects. Never reuse a snapshot address as an ownership guarantee.

## Native reflection metadata

OBSERVED in target code: `1412813d0` traverses child fields at struct+0x50, field next+0x18, updates struct extent+0x58, and copies parent extent. `1412792f0` inherits class constructor-related values from class+0x40. `14134c3b0` computes field offset+0x44 and extent from dimension+0x30 and element_size+0x34. `1412aca00` formats field name at+0x20; `1412ab240` formats field-class name from pointer+0x08. `1412ac700` and `1412b0080` distinguish UObject owners by low tag bit at field+0x10.

PROVEN by native/Python live checks: parent+0x40, property head+0x50, instance size+0x58; field class+0x08, tagged owner+0x10, next+0x18, FName+0x20, dimensions+0x30, element size+0x34, offset+0x44. Field-class FName begins at its base and cast bits at+0x10 include0x8000 for these properties. All traversed direct owners must match the containing class after removing the tag bit. Cycle/count/extent limits and repeated metadata reads reject inconsistent samples. This still does not provide an atomic GC snapshot.

Actor reports 80 properties and size656; HUD reports 16 direct plus 80 inherited properties, size896. Root Object size40, no properties. Local evidence: mcp-reflection-first-functions.json, mcp-reflection-followup.json, mcp-reflection-field-path.json, python-live-reflection.json. BoolProperty masks and complex value semantics remain unvalidated; shared byte offsets are not sufficient to decode booleans.
