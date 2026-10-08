# GAME_BUILD

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

The installed Steam build 23765773 and shipping executable are fingerprinted and independently PE-validated. Runtime support is gated by the full SHA256 below. Embedded version text supports UE 5.4.4; all SDK layouts are independently target-derived.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## 2026-10-08 inventory evidence

OBSERVED: Installation is S:\SteamLibrary\steamapps\common\Expedition 33. Full filesystem inventory: ../evidence/installation-files.csv. No game file was modified.

OBSERVED: Steam app 1903340, buildid 23765773, depot 1903341 manifest 3499712487662840491 from local appmanifest. This is distribution build metadata, not a semantic patch number.

PROVEN (PE header parsing): Sandfall/Binaries/Win64/SandFall-Win64-Shipping.exe has machine 0x8664 (x64), preferred image base 0x140000000, entry RVA 0x6c18e30, file size 162421568 bytes. SHA256: 218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618. Reproduce using scripts/inspect_pe.py. SHA256 independently also collected by Get-FileHash in ../evidence/binary-fingerprints.json.

OBSERVED: PE timestamp 3062884140. Do not interpret as a trustworthy build date; deterministic toolchains may repurpose this field.

OBSERVED: Expedition33_Steam.exe is a separate 689544-byte launcher. SHA256 D306684D15DCB051201462D1802BFFCE0362556D1F2CDA238EBE60E7DB831D7B.

OBSERVED: PAK + .utoc/.ucas containers, including global IoStore containers. NVIDIA DLSS/Streamline, XeSS, OVRLipSync, Sentry/crashpad, Steamworks v157, MsQuic, D3D12, and AMD FidelityFX files are present. These are packaged components, not evidence that every component is active at runtime.

OBSERVED: Debug manifest lists shipping PDB but no actual PDB appears in filesystem inventory. Saved directory under LocalAppData/Sandfall contains SaveGames; no logs/config directory was found there in initial listing. Saves were not opened.

HYPOTHESIS: Engine 5.4.4 based on embedded text at file offset 0x817f328; independently validate actual UTF-16 bytes and version metadata before treating as firm build identification. Initial extractor searches every other byte and may admit false positives.

OBSERVED: No obvious standalone anti-cheat loader or existing mod-loader files in initial inventory. This does NOT prove protection absent; imports, embedded indicators, and target provenance remain to investigate before runtime attachment.

## Independent PE validation

PROVEN by pefile 2024.8.26 independently of inspect_pe.py: machine 0x8664, preferred base 0x140000000, mapped image size 166776832. CLR directory is zero, so the shipping executable is not a normal managed .NET assembly. Evidence: ../evidence/shipping-pe-independent.json (includes imports/exports/version resource).

OBSERVED version resource: ProductVersion ++streams+ProjectW-release-CL-68322; CompanyName Sandfall Interactive. No anti-cheat DLL name appeared in the ordinary import table; delay imports and dynamically loaded modules are not covered by that statement.

OBSERVED exact ASCII-range UTF-16 validation retains Unreal Engine 5.4.4 at 0x817f328. INFERRED engine minor version 5.4.4, pending corroboration by engine initialization/version paths. Date-like string 5.11.25-21.28.50:803][376] is not an engine version and must not be used as one.

## Module inventory follow-up

PROVEN: All 36 installed .exe/.dll files were parsed with pefile; none had a nonzero CLR metadata directory. No ILSpy target established. No Unity IL2CPP metadata/native-module pairing found in installation inventory; Cpp2IL remains unused.

OBSERVED: Launcher Expedition33_Steam.exe contains .bind; shipping image does not. HYPOTHESIS: launcher may contain Steam wrapper/protection metadata. Do not unpack, patch, bypass, or use a direct-launch workaround. Current static research is isolated to the untouched shipping image. Use the normal authorized Steam launch for any eventual runtime experiment; reassess before interacting with any protection.

Reproduce with scripts/inventory_modules.py; complete ordinary/delay import and section inventory is ../evidence/all-pe-module-inventory.json. File/import-name absence cannot establish absence of dynamically loaded or embedded protection.

## Compatibility rejection regression

PROVEN: scripts/verify_compatibility.py exercises the exact supported_image function called by normal native startup before signature scanning, memory reads or attachment. It accepts the preserved original SHA256 and rejects a same-size copy with one flipped final byte (UNSUPPORTED_BUILD_SHA256), a different-size file (UNSUPPORTED_BUILD_SIZE), and a missing file (MODULE_FILE_OPEN_FAILED). Changes occur only in build/compatibility on D:, never in the installed game or preserved analysis input. The --check-image command is offline only; it cannot skip fingerprint validation on a live session. Evidence: evidence/compatibility.json. Initial verifier incorrectly expected failures on stdout; native errors use stderr, so the verifier was corrected to read the appropriate stream. The gate itself rejected the altered copy on both runs.


## Static image catalog

OBSERVED from the preserved PE: ten sections (Ghidra additionally represents headers as a memory block).

| Section | RVA | Virtual bytes | Raw bytes |
| --- | --- | ---: | ---: |
| .text | 0x1000 | 114641932 | 114642432 |
| .rdata | 0x6d56000 | 36712488 | 36712960 |
| .data | 0x905a000 | 6245396 | 1901056 |
| .pdata | 0x964f000 | 5808528 | 5808640 |
| .msvcjmc | 0x9bda000 | 8 | 512 |
| CPADinfo | 0x9bdb000 | 56 | 512 |
| .rodata | 0x9bdc000 | 1936 | 2048 |
| _RDATA | 0x9bdd000 | 383760 | 384000 |
| .rsrc | 0x9c3b000 | 310224 | 310272 |
| .reloc | 0x9c87000 | 2644452 | 2644480 |

The ordinary import table contains 1103 entries from 41 DLLs, including Windows APIs, MSVC runtime, graphics/audio and OpenColorIO. There are 356 exported symbols, including libpng/sample-rate conversion and AntiLag module interfaces. These exports are not an exposed Unreal object SDK. Full ordinary/delay imports were already retained in all-pe-module-inventory.json; this compact catalog is evidence/static-image-catalog.json.

RTTI lead rejection: a bounded MSVC class-name byte scan for UObject/UConsole/UGameViewportClient and property classes only found .?AVUObject@icu_64@@ at preferred VA0x14921e820. That is ICU namespaced UObject, not Unreal UObject. This scan is not proof that all RTTI is absent. Runtime Unreal class and FField metadata, validated code paths and vtable relationships provide the established anchors.
