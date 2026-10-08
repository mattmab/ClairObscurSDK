# UE_RUNTIME

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: build-scoped object registry and name pool support live native/Python enumeration. See OBJECT_SYSTEM.md. Reflection and invocation remain under investigation.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Static lead experiment 001

OBSERVED (exact bytes; shipping SHA256 218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618):

| Text | Encoding | RVA | Preferred VA |
|---|---|---|---|
| StaticFindObject | UTF-16LE | 0x6e1ce50 | 0x146e1ce50 |
| /Script/CoreUObject | ASCII | 0x6dde790 | 0x146dde790 |
| /Script/CoreUObject | UTF-16LE | 0x6db7d70 | 0x146db7d70 |
| /Script/CoreUObject | UTF-16LE | 0x6df8a90 | 0x146df8a90 |
| Unreal Engine 5.4.4 | UTF-16LE | 0x817ff28 | 0x14817ff28 |

Reproduce: run scripts/find_static_leads.py against the unchanged shipping image using the D: tools interpreter. Complete result: ../evidence/static-string-leads.json. These are string addresses, NOT function/global addresses; preferred VAs are not live ASLR addresses.

No exact hits for GUObjectArray, FUObjectArray, FNamePool, UObject::ProcessEvent, ProcessEvent, StaticAllocateObject, NamePoolData, or .?AVUObject@@. This is not evidence that the corresponding runtime primitive is absent; native shipping code often lacks these spellings.

NEXT EXPERIMENT: Ghidra xrefs to the unique StaticFindObject text and CoreUObject package registration strings, then inspect callers/callees for allocation/lookup behavior. Do not assign canonical function names before that evidence exists.

