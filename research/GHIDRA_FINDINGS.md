# GHIDRA_FINDINGS

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Build-specific registry/name-pool traversal, native reflection metadata, reflected getter dispatch and console construction/command paths have static and live corroboration. Findings below are chronological; OBJECT_SYSTEM.md, FUNCTION_INVOCATION.md and CONSOLE.md record the validated runtime surface. Whole-image analysis remains incomplete after memory failures; successful targeted findings do not imply whole-image completion.

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

## Startup and engine-loop path

OBSERVED through MCP and independently read string bytes: PE entry146c18e30 calls146c22680 (time/process/thread-based security-cookie initialization), then146c18cbc. The latter invokes _initterm_e/_initterm, obtains the WinMain command line and calls143ecf750. That wrapper calls143ec73b0, which reads GetCommandLineW and reaches143ec6330 directly or through143ec6660. No startup functions were called by the SDK.

143ec6330 refers to Starting, DefaultMain, EngineInit/Loading..., Tick loop starting, Ticking loop and EngineExit() was called strings. It calls143eca930 and143ec8990, then143ebdfb0 on state14910f520; on successful startup it loops calling143ebe810(&14910f520) while byte149272cea is zero, then reaches143ec5a90 on shutdown. INFERRED roles: guarded application main, staged engine preinitialization, initialization, tick and exit. Exact source-level names/ABIs are not promoted to public call targets. Evidence: entry-init.json, winmain-init.json, engine-startup.json, engine-loop-init.json and engine-loop-strings.json. An initial visual lead146c22600 resolved inside an unrelated function; the actual entry call target146c22680 is independently present in the decompilation. Mixed ASCII/UTF-16 string encodings were checked rather than interpreting garbled text as symbols.


## 2026-10-08 recovered analysis completed and persisted

PROVEN: application.log reports Auto Analysis completed at18:23:16 in3437.01 seconds. MCP analysis_status confirms analyzing=false with306134 functions. No new heap exhaustion occurred during this reduced pass. Warnings remain: no appropriate matching PDB; two Microsoft demangler failures creating data at146c5e130; exception-function creation failure at141004490; localized decompiler/pcode/read warnings. Completion means the configured reduced pass finished, not every byte or type was recovered. Disabled analyzers remain as recorded above.

Seven build-scoped plate annotations were written for console command/output/state, SpawnObject, struct/array descriptors and startup-loop findings. save_program confirmed saved=true. close_program confirmed closed_count=1 (released_cache=false); open_program reopened /game/SandFall-Win64-Shipping.exe with auto_analyze=false. Metadata returned306134 functions and2182806 symbols; get_comment returned all7 exact expected annotations. This is save/close/reopen verification in the same JVM, not a full JVM restart test.

Evidence: recovery2-analysis-progress.json, recovery2-final-saved.json, recovery2-final-closed.json, recovery2-final-reopened.json, recovery2-final-metadata.json, recovery2-final-comments.json, release-annotation-*-written.json. Previous failure/recovery records remain chronological evidence. The private v0.1 runtime archive is unchanged.
