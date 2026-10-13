# Code provenance audit

Audit snapshot: 2026-10-12 America/New_York (release timestamps use UTC). RC4 publication commit **1fc1ea2babc3d173c9d732bc641a9a23b5a1c744**; current checkout HEAD **695b062823e63ab7821ccf22cb0378cb376e3cd8** plus pre-existing uncommitted viewer work. Release and working-tree findings are distinguished. This audit writes reports only; no implementation, license, notice, history, release or installed-runtime changes were made.

These are evidence-based technical compliance findings, not a determination of infringement or comprehensive legal clearance. “No identified concern” means no concern identified within the stated examination, not proof that no third-party rights exist.

## Assessment

Confirmed: implementation source was accessed from the BL SDK projects and other references. This was not a documentation-only or strict clean-room process. Confirmed copying of the Introspection Harness is a **first-party port of the user's own code**, as the user directly confirmed; it is not classified as third-party code. Its MIT notice is retained. No substantial LGPL implementation copying was identified in the bounded native/Python comparisons. Generated code is not presumed independent merely because an agent produced it.

The distribution has separate dependency-notice questions; see [license inventory](license-inventory.md) and [release verification](release-compliance.md). No high-priority legal-review finding of substantial unauthorized matching implementation is established by the examined evidence. Unresolved provenance and incomplete comparison coverage remain explicitly open.

## Evidence conventions

All target line ranges refer to RC4 unless marked current. Reference commits below are immutable source anchors where available. The preserved BL4 snapshots have content hashes but no established source commit. Transcript line citations refer to local physical JSONL lines; they should not be published wholesale because they can contain unrelated personal/development context. The four reports summarize pertinent evidence instead.

# Historical provenance audit — 2026-10-12 local date

Read-only project audit; scratch evidence written only under SDKProvenanceAudit/history. No source, notices, licenses, releases, or Git history changed.

## Primary transcript evidence

Transcript T = `C:/Users/Matt/.codex/sessions/2026/10/08/rollout-2026-10-08T13-29-23-01a11c90-076c-7a73-9209-e91c812bf07f.jsonl`. Line numbers are physical JSONL lines; timestamps UTC. They identify recorded tool calls, not proof that every requested output survived truncation. Corroboration includes checked-out repositories, preserved artifacts, Git introductions, and matching hashes.

| Finding | Exact evidence | Conclusion |
|---|---|---|
| Nine reference repositories cloned | T:53 sandbox attempt, T:66 escalated clone command; evidence/reference-revisions.json:1–38; repositories.json independently records current remotes/HEADs | Access was not documentation-only; full clones exist. |
| unrealsdk / pyunrealsdk implementation viewed | T:112 at 2026-10-08T17:34:14Z reads pyunrealsdk.cpp first220, weak_pointer.cpp first120, bound_function.cpp first180; T:136 reads gobjects.cpp first170, hook.cpp first200, property_access.cpp first130; T:164 gnames.cpp first130 and uobject.cpp first95; T:169 offsets.h first85 and type_casters.cpp first90 | Confirmed implementation exposure. Does not by itself establish copying. |
| Other six architectural tools/docs studied | T:144 reads README portions for universal-modder, rea, ai-game-modding-guides, ida-mcp, ILSpy, Cpp2IL; research/REFERENCE_SDK_ARCHITECTURE.md:43–47 | README-based conceptual study evidenced; no SDK embedding established. Ghidra MCP separately installed as development tool. |
| BL4 Harness original preserved | T:6378 at 2026-10-08T22:28:10Z copies 23 source/client/test/doc/archive files from installed Borderlands4 sdk_mods into Analysis snapshot; evidence/introspection-source-manifest.json | Actual source copies exist, not just API comparisons. |
| BL4 Harness core copied into SDK | T:6502 at 2026-10-08T22:34:33Z explicitly Copy-Item core.py and LICENSE into src/expedition33/introspection; commit2036cebd761780f14aef1a1812d60e4402e1223f introduced them | Confirmed whole-file MIT reuse. Current core and preserved original both SHA256 6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543. Original MIT Copyright(c)2026 Mattmab retained in adjacent LICENSE; RC4 commit1fc1ea2 contains that notice. |
| BL4 Harness clients/agent adapted | research/INTROSPECTION_PORT.md:235–281; scripts/e33_introspect.py introduced15b647c36cc7351a0610926144b9984bd284684a; agent.py b4b5462d34819a2cd6dd67773266ebff94e4a71f; scripts/e33_agent.py a6dc867140415853bfd727707bf889eadf90f723; T:25162,T:25484 actual source reads | Porting is explicitly recorded. Python comparison audit should quantify exact portions; AI origin is not independent-authorship proof. |
| BL4 management implementation preserved/read | research/MANAGEMENT_PORT.md:148–175; evidence/management-source-manifest.json; T:7445 reads policy.py first180/workspace.py first120 and searches main; T:7455 reads main lines1629–1833 and4642–4721 | MattsBL4ModsMenu1.3.3 MIT source, console_mod_menu1.6, mods_base1.12 and keybind wrappers available as actual implementation references. |
| Oak2 implementation cloned/read | T:7445 at2026-10-08T23:20:42Z clones oak2; T:7462 reads src/keybinds/keybinds.cpp entire plus console_mod_menu/screens/option.py first220 and draw.py first140 | Confirmed source exposure, commitd606e796733eced318e2a44e51b871a7becae55e. License conclusions must use exact repository notices, not historical generic label LGPL3. |
| Menu/keybind later adaptations informed by BL4 | T:29942 searches BL4 CreateWidget/cache/class lookup; T:30047 reads main181–205; T:30196 main4434–4480; T:30235 workspace206–249. research/RELEASE_CONVERGENCE.md:235,269 explicitly cites patterns | Architecture transfer acknowledged; needs similarity/manual review, not automatic derivative-work conclusion. |
| retoc source downloaded/viewed | T:39038 releasev0.1.5 downloaded; T:39073 main.rs,39092 oodle.rs,39099 Cargo,39104 rootCargo fetched into evidence/ | Third-party source actually downloaded for tool configuration/debugging. No tracked evidence files for these source downloads. |
| repak implementation viewed | T:39111 https://raw.githubusercontent.com/trumank/repak/master/oodle_loader/src/lib.rs -> evidence/oodle-loader-source.rs, first160read | Mutable master URL has no pinned source commit in recorded command; artifact hash should identify exact retained bytes. |
| UAssetAPI format implementation viewed | T:39238 2026-10-11T08:34:58Z https://raw.githubusercontent.com/atenfyr/UAssetAPI/master/UAssetAPI/Unversioned/FFragment.cs -> evidence/unversioned-fragment-source.cs | scripts/build_cinematic_catalog.py:34–50 decodes the same format masks/shift. Fragment bit masks127/128/256 and shift9 are serialized-format facts, insufficient copying proof. Source commit unpinned; source comparison/manual review required. Script introducedda5de7248124558adaf7217221cb3b30266eb648. |
| Statistics third-party binary inspected statically | research/STATISTICS_SDK_REPLACEMENT.md:64–76; archive contains no source/README; DLL SHA256 acc17990175dc2719ec500b5f7217e9615f3f49264b4a6dcc836fbffe047441b | Binary strings and version1.0.7 analyzed; recorded never installed/executed. This is still third-party implementation exposure, not a code license grant. |
| CineReplay third-party reference | User supplied DLL and quarantined loader; research/NATIVE_CINEMATIC_INVOCATION_CONTRACT.md:1–7 records target-game reflection and no supplied binary execution | Follow target-derived evidence; binary static analysis history is not clean-room separation or rights clearance. No opaque third-party DLL loading authorized. |

## Reference repository revisions (verified local clones)

See repositories.json for all exact commits. Main source-study commits: unrealsdk ac31716b2b462e78f0a841b6d352aa2fa56c7f92; pyunrealsdk cb5fc362ea228727f334d94b64eb9538d8778bc6; oak2 d606e796733eced318e2a44e51b871a7becae55e. Additional references: bethington/ghidra-mcp9cc29c0f1efb6c63a7d6898c9a23aff39397f992; HexRaysSA/ida-mcp2e62361d4c472fde93365613fd4fdcd2c1f6a4cb; icsharpcode/ILSpy b379738b7fae10027bd3c30cc2190677aea48e3b; morluto/rea3b2ec69c54fc9cf65bf8441edbb96e9619c3a37e; rehan-remade/universal-modder8370faa8e114baf33acdb23079aff552a7728c4b; SamboyCoding/Cpp2ILb5ad444b82267cb1e4b88b8b373c008105bdea52; trevaintdead/ai-game-modding-guides1c8df26a64f3d8604fa05ac2b3d3b65c0dde31ef.

## Limits and recommended classification

- Confirmed MIT Harness reuse with retained notice: no identified concern from copying alone; the user explicitly confirmed the Harness is their own code during this audit; classify this as a first-party port.
- Confirmed LGPL-family implementation exposure: source comparison/license compliance review, not infringement finding and not evidence all SDK is LGPL.
- The Harness port is reuse of the user's own code, consistent with first-party authorship. Separately, agents read third-party implementations, so strict clean-room authorship is not established. Source exposure alone does not disprove independently authored implementation.
- Local rollout scan found390JSONL files; narrowly selected relevant tool calls, not all content semantically reviewed. Earlier BL4 development predates this SDK and may have further upstream influences. Logs are partial evidence and may contain truncated tool outputs or missing/compacted history.
- Existing local cloned HEADs are corroboration, not proof each earlier source file had no uncommitted edits. Historic revision file and exact tool timestamps provide stronger pinning.
- No authoritative Git source commit located for the user's BL4 Harness/MattsBL4ModsMenu snapshots, installed mods_base/console_mod_menu archives, or mutable master downloads. Preserve SHA256s and mark commit unknown; do not invent one.
- The original checkout lacked a local RC4 tag. A separate audit clone resolves v0.1.0-rc4 to 1fc1ea2babc3d173c9d732bc641a9a23b5a1c744; GitHub release API agrees. See release-compliance.md for actual downloaded-asset verification.
- No legal infringement conclusion is supported solely by these historical accesses.

## Updated UAssetAPI anchor

The previously mutable download is now content-anchored: `evidence/unversioned-fragment-source.cs` SHA256 `769c6797ec6cd84d4192de5604cdf9af20b93aa6bfeb2b66ee476f33bcbf599d` equals [FFragment.cs at 74ed8bb3bd4eb75c5365e65a2a4191e07df52d5d](https://github.com/atenfyr/UAssetAPI/blob/74ed8bb3bd4eb75c5365e65a2a4191e07df52d5d/UAssetAPI/Unversioned/FFragment.cs). This identifies the source bytes, not necessarily the checkout revision at the original access time. Same-commit LICENSE is MIT, copyright atenfyr. Full file is untracked evidence, not an RC4 member. Shared masks/shift are format facts; see source-similarity.md for manual analysis.

## Prioritized provenance actions

1. Preserve authorship/reference records and existing notices. Keep the user's Harness explicitly identified as a first-party port; no relicensing is recommended on that basis.
2. Resolve the runtime incorporated-notice findings before another public release.
3. Preserve immutable references and exact source archives for future implementation study; pin retoc/repak historical downloads where still unresolved and document the catalog zero-mask formula's evidence.
4. Record build inputs, compiler/linker versions, dependency manifest and output hashes for native release binaries. PE imports alone do not prove absence of statically linked third-party code.
5. If a future focused comparison finds substantial protected implementation, review the grant and distribution obligations, obtain permission if needed, or use a documented independent replacement process. Do not erase history or remove notices. Seek legal review for unresolved substantial rights questions; do not automatically change the whole project's license.

Local reproducibility evidence: `D:/HobbyDevelopment/SDKProvenanceAudit/history/{HISTORICAL_FINDINGS.md,repositories.json,transcript_commands.json,download_commands.json}` and comparison scripts/results listed in source-similarity.md. No complete semantic review of every transcript, every ancestor commit, or the earlier BL4 project history was performed. This bounds the conclusion.


## Remediation addendum — 2026-10-12

The original RC4 findings above remain historical evidence. The authorized runtime-notice remediation is documented in [runtime-license-remediation.md](runtime-license-remediation.md), with component-by-component dispositions and [actual candidate verification](runtime-license-verification.json).

D1 is **partially resolved**: applicable authentic notice texts and pinned applicability evidence are now packaged and verified, including Expat; five platform/test-only inventory entries are not applicable with evidence. Microsoft entitlement/downstream protective-terms agreement questions and historical native build provenance remain unresolved. OpenSSL3.0.21's exact source/binary trees have no NOTICE file; its license and authentic attribution are included. No whole-distribution legal clearance is claimed.

The local `0.1.0-rc4-license1` candidate retains all34 official runtime files,115 SDK source/script files,five native payload files and both bundled mod archives byte-for-byte from RC4. First-party MIT and the user-authored Harness remain unchanged. Full regression:1,017tests passed; clean-install `--check` passed. No new live-game validation, published RC4 modification, tag, push or release occurred. This addendum supersedes only the current remediation status, not the historical RC4 observations.
