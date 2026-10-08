# GHIDRA_FINDINGS

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Shipping import and analysis configuration, 2026-10-08

PROVEN: MCP imported the SHA256-verified analysis copy as /game/SandFall-Win64-Shipping.exe into Expedition33-23765773.gpr. Ghidra metadata agrees with independent PE inspection: x86:LE:64:default, Windows compiler spec, little endian, preferred image base 0x140000000. Eleven memory blocks total 166774272 bytes; this is the sum of mapped blocks, not the PE SizeOfImage (166776832, which includes alignment gaps). Before auto-analysis, the loader had already created 288587 functions; this is not proof those functions are analyzed or correctly understood.

Computer Use inspected Analysis > Auto Analyze options. Retained standard x64 Windows defaults: disassemble entry points, references/Unicode string references, x86 constant references, function starts, Microsoft demangler, PE exception handling and RTTI enabled; aggressive instruction finder and decompiler parameter ID disabled. PDB Universal enabled but search of untrusted symbol servers disabled. Full option inventory in evidence/mcp-shipping-analyzers-before.json. Started Analyze through the GUI. Stage 3 completion remains pending actual analysis completion.

Initial evidence: evidence/mcp-import-shipping-result.json and mcp-shipping-metadata-preanalysis.json. Static string addresses from static-string-leads.json remain leads only, not runtime anchors.

## Corrected string boundaries and source-path leads

PROVEN by MCP read_memory and independent pefile-backed byte scan: substring StaticFindObject at preferred VA 0x146e1ce50 is inside the UTF-16 diagnostic `Illegal call to StaticFindObjectFast() while serializing object data or garbage collecting!`, beginning 0x146e1ce30. The old substring address is not a function address or necessarily a referenced string start. scripts/find_static_leads.py now records bounded enclosing printable spans and null termination. Original evidence is retained; new evidence is static-string-leads-with-context.json.

OBSERVED full ASCII diagnostic source paths (preferred static VA): UObjectGlobals.cpp 0x146e1cef0; UObjectArray.cpp 0x146e1c470; UObjectHash.cpp 0x146e22130; UnrealNames.cpp 0x146dcc6a0; ScriptCore.cpp 0x146e19a00; GarbageCollection.cpp 0x146e04a50. Paths are under C:/p4ws/Engine/Source/Runtime, embedded build-machine strings, not local filesystem paths. These support focused future xref experiments; they do not prove a registry address, layout, FName resolver, or ProcessEvent identity.

MCP analysis_status still reports analyzing=true. The analyzed=true flag in the same response is NOT completion while analyzing remains true. Early string xref queries returned empty lists; no negative semantic conclusion may be drawn before relevant disassembly/reference analysis finishes.

## Runtime-corroborated anchors — 2026-10-08

PROVEN for the recorded fingerprint: registration `1413ab9d0`, chunk allocation `1413aae40`, registration caller `1413aeba0`, name formatting `1411bcab0`, entry copy `1411a3660`, pool initialization `14119e730`. See OBJECT_SYSTEM.md for the independently derived offsets and live invariants. Raw RIP-relative byte candidates were only hypotheses until disassembly/decompilation corroborated them. Full-image autoanalysis still running at the first successful live query; partial function metadata during analysis is not a final boundary guarantee.
