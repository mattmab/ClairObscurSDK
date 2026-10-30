# Reflection and copied-value capability audit — 2026-10-24

Scope: isolated capability-expansion branch. Source inspection and offline tests only; no game invocation, injection, installation, release, or private content. Historical research notes are leads, not evidence of current missing functionality.

## Verified existing coverage

| Category | Current evidence | Assessment |
|---|---|---|
| Identity and inheritance | `src/expedition33/catalog.py:30`, `:208`, `:236` implement immutable observed objects, filtered and identity-selected closure, exact resolution and merge conflict checks | Already supported; do not duplicate a name-based reflection registry |
| Class, struct and function metadata | `src/expedition33/reflection.py:36`; native `native/research_probe.cpp:855` metadata walk | Bounded descriptor batches, inherited owners, function flags and parameter/property metadata already available |
| Enum/reference metadata | Native metadata emits struct/enum/class/meta-class/delegate and array-inner identities | Existing capability; missing top-level struct/enum address fields limited selected closure |
| Arrays and recursive structs | `src/expedition33/values.py:18`, `:40`, `:155`, `:261` | Copied values, bounded array prefixes and recursive validation already exist; copies do not own native allocations |
| Maps | `src/expedition33/values.py:50`, `:56`, `:61` | Supported typed combinations only; complete copied maps and struct-key entries already exist. Generic arbitrary map mutation is not implemented |
| Selected projected values | `src/expedition33/values.py:296`, `:358` | Selected values and optional object-reference closure already exist; no reason to introduce an overlapping API |
| Interactive inspection | `src/expedition33/introspection/__init__.py:409` | Existing schema/value wrapper and explicit unsupported-capability diagnostics; not a blank slate |

## Implemented gap: selected schema dependency closure

Previously a caller could select a function/class exactly, then fail to describe it because one referenced property type was absent from the selected catalog. `capture_selected` closes class/super/outer relationships, not arbitrary FProperty type relationships. Callers otherwise needed to know and select those types separately, or obtain a broad catalog. This obstructs reusable schema inspection despite native metadata already knowing the exact referenced identities.

Added `expedition33.reflection.describe_selected(pid, identities)` returning frozen `ReflectionSnapshot(catalog, descriptors)`. It captures exact roots, stages the existing descriptor replies, captures only missing property-type identities, then uses the same strict descriptor decoder against the combined catalog. No registry enumeration, name matching, metadata retry, recursive schema walk, value read, retention, or invocation is introduced.

Bounds: 1–1024 root selectors, batches of 128, at most 1024 additional referenced types, at most 16384 combined catalog objects. Root and dependency index/serial/address/name mismatches fail rather than substituting a replacement object. Dependencies include all eleven native forms in `REFERENCE_KINDS`, including map key/value structs. The ordinary `describe` decoder now validates those map struct identities too; previously it omitted them despite receiving the metadata.

Native change: `native/research_probe.cpp` now includes the already validated address with top-level struct/enum references. Other reference forms already included addresses. This is an additive read-only JSON change, not a runtime ABI change. **Older readers:** existing `describe` with a complete catalog still works. `describe_selected` explicitly reports “Reader omits referenced type address; update reader or use describe with a complete catalog” when missing dependencies cannot be selected safely. No unchecked address/name fallback exists.

Example (observations must come from the same live process):

```python
from expedition33.reflection import describe_selected

snapshot = describe_selected(pid, [(observed.index, observed.serial, observed.address)])
descriptor = snapshot.descriptors[observed.index]
for prop in descriptor.properties:
    print(prop['name'], prop['type'])
```

The result is an observation, not a callable handle or GC-atomic transaction. The reader revalidates selected identities during reads; engine state may subsequently change. Invocation still requires the independent existing native validation and capability gates.

## Prioritized candidates

Scores are engineering judgments (1–5); benefit and confidence favor higher numbers, cost and risk favor lower numbers.

| Candidate | Benefit | Cost | Risk | Confidence | Decision |
|---|---:|---:|---:|---:|---|
| Exact selected schema/type closure | 5 | 2 | 1 | 5 | Implemented; foundational for inspectors and planners without broad scans |
| Validate map key/value struct identities | 4 | 1 | 1 | 5 | Implemented; closes an observable decoder omission |
| Generic copied set support | 3 | 4 | 3 | 3 | Defer; requires verified sparse-set layout, element codecs, complete/prefix semantics and adversarial fixtures |
| Generic map key/value expansion | 4 | 4 | 3 | 4 | Defer; current whitelist is real, new combinations require native schema/value validation rather than a Python wrapper |
| Arbitrary container writes | 4 | 5 | 5 | 4 | Defer; allocation/destruction/hash invariants and ownership are materially different from copied reads |
| Recursively describe all referenced schemas | 3 | 3 | 2 | 4 | Defer; cycles and unbounded fan-out need explicit depth/byte/query budgets. Current API deliberately returns direct descriptors only |

## Validation and remaining evidence gaps

- 94 focused Python tests passed across reflection, selected catalog, copied/projected values, structs, POD, table rows, invocation, enums and prepared invocation.
- Eight new selected-reflection tests cover exact selectors/no broad query, existing closure, older-reader rejection, stale reference serial/address/name, conflicting dependency selectors, all reference forms, process/malformed replies, and dependency budget. Existing reference validation test now covers map struct identities too.
- Standalone `scripts/build-research-probe.cmd` compiled the read-only reader successfully with MSVC 17.14.41, `/W4`, C++17, into worktree `build/research-probe`. No installed executable was replaced.
- Native `enum_schema`, `pod_schema`, and `metadata_stabilization` fixtures compiled with `/W4 /WX` and passed: enum fixtures rejected 24 malformed/context/identity cases plus six invalid wire packets and a legacy version; POD fixtures rejected 24 altered/context/identity cases. Outputs remained under worktree `build/reflection-temp`.
- Unit protocol fixtures simulate metadata; they do not claim live engine struct-layout verification. Live use of the new selected API remains untested in this audit. No claim of performance improvement without live measurements.

Changed files owned by this audit: `native/research_probe.cpp`, `src/expedition33/reflection.py`, `tests/test_reflection.py`, `tests/test_reflection_selected.py`, and this report. Public import is directly from `expedition33.reflection`; no package-root or Session export is required.
