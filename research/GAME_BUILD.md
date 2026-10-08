# GAME_BUILD

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

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
