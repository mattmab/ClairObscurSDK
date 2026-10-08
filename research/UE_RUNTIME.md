# UE_RUNTIME

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

PROVEN: build-scoped object registry and name pool support live native/Python enumeration. Native reflection metadata, stored booleans, a fixed reflected getter and persistent observer are validated. Console research additionally corroborates engine, viewport, world and game-instance relationships and the native console construction/command/state paths. See OBJECT_SYSTEM.md, FUNCTION_INVOCATION.md and CONSOLE.md; arbitrary invocation and object lifetime remain outside the validated surface.

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


## Live local-player and component relationships

OBSERVED 2026-10-08, shipping SHA256 218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618, PID34604 at the main menu: scripts/inspect_runtime_relationships.py obtains offsets from live native reflection and follows registered object identities using read-only process access. LocalPlayer index85501 points through ViewportClient +0x78 to CustomGameViewportClient index85500, and PlayerController +0x30 to BP_jRPG_Controller_MainMenu_C index56577. That controller's Player +0x330 points back to index85501.

Its inherited Actor.RootComponent +0x1a0 points to SceneComponent TransformComponent0 index56576. The component's UObject.Outer +0x20 points back to the controller. GameInstance.LocalPlayers +0x38 is an observed pointer/count/capacity array with count1/capacity4 containing the same local player. This corroborates the viewport/game-instance/player/controller/component chain for this main-menu state; it does not establish arbitrary gameplay actors or map transitions.

Evidence: evidence/runtime-relationship-metadata.json and evidence/runtime-relationships.json. The reader checks bounded counts, registered target identities, source identity stability and the array header before/after traversal. These are external observations, not GC-pinned handles or atomic engine snapshots. No engine calls or writes occur.
