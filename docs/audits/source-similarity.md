# Source similarity audit

Audit snapshot: 2026-10-12 America/New_York (release timestamps use UTC). RC4 publication commit **1fc1ea2babc3d173c9d732bc641a9a23b5a1c744**; current checkout HEAD **695b062823e63ab7821ccf22cb0378cb376e3cd8** plus pre-existing uncommitted viewer work. Release and working-tree findings are distinguished. This audit writes reports only; no implementation, license, notice, history, release or installed-runtime changes were made.

These are evidence-based technical compliance findings, not a determination of infringement or comprehensive legal clearance. “No identified concern” means no concern identified within the stated examination, not proof that no third-party rights exist.

## Consolidated findings

| ID | Evidence | Classification | Resolution |
|---|---|---|---|
| S1 | Harness core exact copy; CLI/agent adaptations; detailed ranges below | No identified concern: confirmed first-party port, user-confirmed authorship | Preserve MIT notice and port history |
| S2 | Native standard include sequences, maximum 19 literal tokens | No identified concern: generic boilerplate | No rewrite or relicensing warranted |
| S3 | No qualifying substantial BL SDK Python/native match within tested corpus | No identified concern within scope; transformed/omitted copying unresolved | Retain methods and limitations; do not claim proof of independence |
| S4 | UAssetAPI fragment format masks/shift and recorded source access | Attribution review; format knowledge is not itself copied protected expression | Preserve source attribution; pin source bytes; document remaining formula provenance |
| S5 | Confirmed implementation-source exposure | Unresolved provenance beyond examined matches | No strict clean-room claim; no automatic infringement inference |

No material matching implementation in these comparisons supports a high-priority legal-review classification by itself. Similarity scores are evidence triage, not legal conclusions.

# Native provenance comparison — 2026-10-12

## Scope and immutable inputs
- RC4: `https://github.com/mattmab/ClairObscurSDK`, tag `v0.1.0-rc4`, commit `1fc1ea2babc3d173c9d732bc641a9a23b5a1c744`; separate clone `D:/HobbyDevelopment/SDKProvenanceAudit/native/rc4`.
- Working tree baseline HEAD `695b062823e63ab7821ccf22cb0378cb376e3cd8`, plus existing modifications/untracked scalar_assignment.h and build-viewer-candidate.cmd. Audit did not modify project files.
- `bl-sdk/unrealsdk`: existing development clone at `ac31716b2b462e78f0a841b6d352aa2fa56c7f92`.
- `bl-sdk/pyunrealsdk`: existing development clone at `cb5fc362ea228727f334d94b64eb9538d8778bc6`.
- `bl-sdk/oak2-mod-manager`: separate clone at `d606e796733eced318e2a44e51b871a7becae55e`, also the revision cited in MANAGEMENT_PORT.md.

## Methods and reproducibility
`compare.py`, `comments.py`, `native-comparison.json`, `native-comments-strings.json` are in this directory. 385 RC4 and 387 current target files were checked: C/C++ headers/source and CMD/BAT/CMake files under native/ and scripts/. 269 same-extension reference files across all three repositories were checked. Reference git submodules were not recursively acquired, so their contents are not covered by this comparison.

Methods: exact UTF-8-decoded whole-file equality; lexical tokens with comments/whitespace removed, common contiguous seeds of 16 tokens; a second mode replaces non-keyword identifiers with ID and seeds 32 tokens (retaining literal values). Candidate pairs were ranked by shared seeds; top ten candidates per target were compared using SequenceMatcher with autojunk disabled. This is not a full all-pairs AST equivalence test. It will miss some transformed/non-contiguous copying and pairs excluded by candidate ranking. Strings/comments of at least 30 characters were separately checked after whitespace normalization. Standard include boilerplate was manually reviewed.

## Findings

### N-01: No substantial implementation match identified within comparison scope
**Classification: No identified concern (limited comparison result), not proof of independent authorship.** No exact full-file match occurred. No matching comment/string >=30 characters was found. The only >=16-token literal token match was:
- RC4 and current `native/research_probe.cpp:12–16` versus unrealsdk `src/unrealsdk/pch.h:54–58`, 19 tokens: standard `<sstream>`, `<stdexcept>`, `<string>` include directives, with neighboring delimiter fragments.
- Source commit `ac31716b2b462e78f0a841b6d352aa2fa56c7f92`; target RC4 commit above.
This is generic C++ boilerplate, not evidence of a copied implementation.

Identifier-renamed matches were also entirely include blocks:
- research_probe.cpp:6–22 versus pch.h:33–49, 79 tokens.
- console_fixture.cpp:1–7 versus pch.h:33–39, 32 tokens.
- owned_text_fixture.cpp:2–9 versus pch.h:33–39, 32 tokens.
- pause_attachment_fixture.cpp:1–7 versus pch.h:33–39, 32 tokens.
Collapsing header identifiers to ID makes unrelated include lists look identical. These are false-positive structural candidates.

### N-02: Implementation source exposure is confirmed
**Classification: Attribution/provenance review; exposure is not itself copying.** `research/REFERENCE_SDK_ARCHITECTURE.md:9,17–33` expressly records implementation inspection at the two pinned commits, including discovery, gobjects, gnames, property_access, bound_function, type_casters, interpreter initialization, hooks, nodelete, weak pointers. Therefore an assertion that agents saw only documentation or that this was a strict clean-room implementation would be contradicted by recorded evidence. The document says architecture informed implementation and distinguishes target-derived evidence from reference observations. Its statement that signatures were not transferred is a development assertion, not independently established by that sentence alone.

`research/MANAGEMENT_PORT.md:150–176` records preserved BL4 source archives and supplementary native Oak2 input source inspection. Original source archives were retained outside the SDK tree. Exact references include `evidence/management-source-manifest.json`.

### N-03: Manually reviewed architecture is materially different
**Classification: No identified concern for the reviewed comparison; not a blanket legal conclusion.**
Oak2 `src/keybinds/keybinds.cpp:24–118` uses engine FKey/FInputKeyParams, FName-keyed unordered_multimap, filtering by EInputEvent, player-controller bShowMouseCursor, and embedded Python GIL/callback invocation. Expedition `native/keybind_protocol.h:5–66` uses bounded copied key-token packets, session/generation validation, and a 64-entry game-thread event queue; `native/runtime_session.cpp`'s WM_KEYDOWN handling observes Windows virtual keys and queues rather than calling embedded Python. Exact current WM_KEYDOWN range is 1001–1021; RC4 line numbers differ, so use the file's `session_keys.press` anchor when inspecting tagged source. These share an input-routing objective but not the reviewed implementation.
Unrealsdk `src/unrealsdk/unreal/wrappers/bound_function.cpp:46–59` holds FunctionCall lock and temporarily sets FUNC_NATIVE around process_event. The Expedition code uses verified reflected request packets and target schema gates. No corresponding copied flag-setting sequence was found by lexical comparison.

### N-04: Target-derived claims have supporting development artifacts, but authorship is not fully provable
`native/trace_frame.h:6–46` identifies target functions 141393330/141395250 and validates frame locals/out-record chains; its introduction is commit `cb0a9711f61c79de3ea9d820a3c629d143e703b4` (Resolve bounded native trace frame storage from verified out-record layout). `native/strong_reference.h:5–16` labels a 24-byte verified holder and points to `research/WIDGET_OWNERSHIP.md`; that document records static and live evidence (e.g. SpawnObject143744670, AddChildToCanvas143092410, explicit retained-object lifecycle). Engine field names, flags and memory layouts can coincide due to the engine ABI and are not alone copying evidence. This audit did not independently rerun Ghidra for every constant or prove the origin of every line.

## Licensing boundaries and recommendations
All three reference repositories contain GNU LGPL Version3 license text. Presence of that text alone does not establish “or later”; consult each project's express licensing grants rather than normalizing to LGPL-3.0-or-later. The parent dependency inventory covers final classification and package notices. Native build commands compile this project's translation units and link Windows system `user32.lib`; source inspection found no include/import of bl-sdk headers or linking to bl-sdk DLLs. This is not a PE import or full binary dependency audit.

1. Preserve and publish accurate reference-inspection provenance; do not claim clean-room or infer AI authorship is independent.
2. Preserve upstream notices on deliberately ported Python components (separate Python audit).
3. Retain this comparison's pinned inputs, scripts and results with the audit. Repeat after substantial changes and whenever additional referenced implementation source is found.
4. No native source relicensing/rewrite is recommended solely from these comparison results. If transcript review identifies an actual copied algorithm/snippet, reclassify and perform focused source/license review.
5. Explicitly retain limitations: no complete C++ AST analysis, no recursive reference submodule content, no binary decompilation comparison, no proof that transformed code was not copied, and no legal conclusion about game reverse-engineering terms.
RC4 exact line supplement for N-03: native/runtime_session.cpp:990–1000 is the Windows WM_KEYDOWN observation and session_keys.press branch. The source bound_function.cpp:49–58 is the lock/flag-change/dispatch/restore sequence.

---

# Python and documentation comparison findings

Audit date: 2026-10-12. Read-only source examination; only audit scratch files created.

## Scope and reproducibility

- RC4 source examined using `git show 1fc1ea2:<path>`; full commit is obtainable from repository `git rev-parse 1fc1ea2`. This is the release implementation commit, followed by 695b062 (release-link correction).
- 837 target Python file instances: all RC4 tracked .py/.pyi plus current working-tree src/mods/scripts Python. Some identical files counted twice intentionally for snapshot distinction.
- 64 reference Python/stub files in existing development clones and preserved originals: oak2 at d606e796733eced318e2a44e51b871a7becae55e, pyunrealsdk at cb5fc362ea228727f334d94b64eb9538d8778bc6, unrealsdk at ac31716b2b462e78f0a841b6d352aa2fa56c7f92, preserved BL4Introspection and BL4 management originals under D:/HobbyDevelopment/Analysis/ClairObscurSDK.
- `compare.py`: tokenize excluding comments/whitespace, exact 24-token overlapping grams candidate detection, SequenceMatcher with autojunk=False, exact AST function comparison for functions >=6 lines. `python-comparison.json` includes paths, SHA256 and exact line ranges for every match.
- `ast_compare.py`: additionally normalizes function names, variable names, argument names and attribute names, comparing complete function AST structures of >=60 nodes. Constants and control flow preserved. Results in `ast-renamed.json`: only already-identified MIT Harness matches.
- `docs_compare.py`: RC4 42 tracked Markdown docs against 19 reference Markdown docs, normalized lowercase alphanumeric words, 20-word contiguous threshold. `docs-comparison.json`: no matches at threshold. License texts are separately examined, not mistaken for authored documentation.
- No >=24-token contiguous implementation matches to the inspected LGPL Python refs, nor MattsBL4ModsMenu, were identified. This is limited negative evidence, not proof of independence; rewritten/noncontiguous copying below thresholds and omitted historical versions remain possible.
- C++ pyunrealsdk/unrealsdk implementations require native audit; this Python scan covers only their .py/.pyi files.

## Confirmed derivation: Mattmab MIT Introspection Harness

1. `src/expedition33/introspection/core.py:1-325` is byte-identical to `bl4-introspection-original-20261008/tools/introspection/package/BL4Introspection/core.py:1-325`. SHA256 of both actual files: `6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543`. All 3,652 normalized tokens match. Eleven nontrivial function ASTs match, including encode31-66, decode68-106, inspect145-165, dispatch190-325. The distinctive bounded serializer, retained values, trace callback and schema logic establish copying independently of functional similarity. Same content in RC4 and working tree. Introduced by target commit `2036cebd761780f14aef1a1812d60e4402e1223f`.
2. `scripts/e33_introspect.py:33-97` matches source `tools/bl4_introspect.py:27-91` for 645 consecutive normalized tokens; total753/817 target tokens in blocks. `main:56-93` AST identical to source50-87. Source SHA256 `4be2d184d2d402c160bdac9a584532f85d48544aceee16dea61f277feca4f985`. Target introduction `15b647c36cc7351a0610926144b9984bd284684a`. Target docstring1-2 explicitly identifies MIT port and adjacent retained license path.
3. `src/expedition33/introspection/agent.py:12-42` and111-127 match source `tools/introspection/package/BL4Introspection/agent.py:12-33` and96-106. Total725/2127 target tokens. `plain:21-30` AST identical source20-25. Source SHA256 `a38e089c320b7005efda21b85805b1abb4d3bca38d42afc1a75d4272f748f151`. Target header explicitly credits MIT port. Introduction `b4b5462d34819a2cd6dd67773266ebff94e4a71f`.
4. `introspection/service.py:82-86` matches original package __init__.py83-87 (43tokens): response-size256KiB check and response envelope. Treat as short corroborating port structure, not independent substantial infringement finding.
5. Tiny matches in `scripts/e33_agent.py:68-70`, `introspection/__init__.py:270-274`, `verify_live_harness_set.py:21-24` are JSON/CLI exception and bounded encode boilerplate in the documented port family; no additional LGPL concern identified.

User explicitly confirms that Introspection Harness is their own code. Classify the confirmed copying as a first-party user-authored port, not unidentified third-party derivation. Original source commit for local BL4Introspection is UNKNOWN. It was preserved from installed SDK-mod sources with manifest hashes (`evidence/introspection-source-manifest.json`), not an immutable repository commit. Do not invent an upstream commit. Its package LICENSE is MIT, Copyright(c)2026 Mattmab; LICENSE_NOTES.md explicitly grants only Mattmab-owned original code/docs, excluding third-party rights. Target `src/expedition33/introspection/LICENSE:1-21` retains same notice since the introduction commit; target root LICENSE also names Mattmab. `research/INTROSPECTION_PORT.md:37-43` explicitly calls this an adaptation of Mattmab MIT source and states original core unchanged. Notices generally supported, but the upstream author's ownership of every source line is not proven by a self-declared license. Classify confirmed MIT reuse with no identified licensing concern in examined notices, historical source commit remains unresolved; user authorship confirmation supplies direct provenance evidence.

## Accessed additional Python implementation sources

`research/MANAGEMENT_PORT.md:149-175` explicitly records copies of nineteen source artifacts and source reading; `evidence/management-source-manifest.json` contains original paths/hashes. References included:
- MattsBL4ModsMenu1.3.3, archiveSHA256 `9d27ef6a2761612cf02a5ae698668fdd324e550bbd96b80e479709799dcf7b18`, MIT Mattmab. Entry, workspace, policy Python included in comparison. No qualifying match to Expedition source.
- bl-sdk/mods_base1.12, archiveSHA256 `16d8cd0da9870af849eae3831922507df3eab66ede2e9420933067000f42c2e8`; LGPLv3 LICENSE present. Exact installed commit not established. Oak2's gitlink is a8c0e36ec902e6e5841c8cf3d4845aa5da352ae6, but do NOT assume installed archive equals it without byte comparison.
- bl-sdk/console_mod_menu1.6, archiveSHA256 `145bec5ace3e884058435472973759c6c29dfce69adc22176c9ae10968d17eb5`; LGPLv3 LICENSE present. Exact installed commit not established. Oak2 gitlink029f370e716ef6872bde9f276c4abec527a49e6d likewise not assumed installed equivalence.
- Oak2 src/__main__.py1-12 explicitly grants GNU Lesser General Public License Version3; no 'or later' language in that header. Distinguish from LGPL-3.0-or-later. Reference source LICENSE text alone does not resolve every component's grant version.
- `research/REFERENCE_SDK_ARCHITECTURE.md:17-33` explicitly describes implementation reading (reflection conversion, initialization, callback/GIL paths); NOT documentation-only access. Do not describe development as clean-room merely because resulting architecture differs.

## Recommendations

- Preserve current MIT Harness attribution; explicitly describe SDK as containing reused Mattmab MIT Harness code instead of implying every file independently originated for this project.
- Keep exact reference archive hashes and record upstream commits wherever they can be established; do not substitute Oak2 submodule pins for installed artifact provenance.
- Check actual RC4 packaging includes retained Harness MIT notice (dependency/release auditor responsibility).
- Complete native/transcript review before release clearance. This component review found no substantial LGPL Python match, but cannot certify entire-project non-derivation or ownership based on absence of similarity.
- No source/license/history edits, automatic relicensing, or removal of notices performed.


## Additional source: UAssetAPI FFragment

Confirmed preserved `evidence/unversioned-fragment-source.cs` equals bytes at upstream commit `74ed8bb3bd4eb75c5365e65a2a4191e07df52d5d`, path `UAssetAPI/Unversioned/FFragment.cs`. SHA256 `769c6797ec6cd84d4192de5604cdf9af20b93aa6bfeb2b66ee476f33bcbf599d`. Immutable public reference: https://github.com/atenfyr/UAssetAPI/blob/74ed8bb3bd4eb75c5365e65a2a4191e07df52d5d/UAssetAPI/Unversioned/FFragment.cs . Commit fetched from public API latest file history, downloaded byte equality established; this anchors source content, not necessarily original checkout commit. MIT license at same commit: Copyright(c)2020–2026 atenfyr, downloaded as UAssetAPI-LICENSE in audit scratch.

Manual cross-language comparison: reference constants36–41 and Unpack60–68 specify masks127,128,256 and right shift9; target `scripts/build_cinematic_catalog.py:34–50` uses those serialized format assignments in its bounded fragment loop. Target introduction commit `da5de7248124558adaf7217221cb3b30266eb648`; included RC4. Target does not reproduce reference comments, errors, class scaffolding, packing routine, constructors or debug formatting. Python's zero-mask-size formula and fields enumeration are not present in this FFragment file, so their provenance is not explained by this particular comparison.

Classification: attribution review / source-derived format knowledge; confirmed reference copying into local untracked evidence, no finding of substantial protected-expression copying in runtime/source solely from shared format constants. The locally downloaded entire C# source is an actual copy and its license should accompany preservation or any redistribution. It is untracked (`git ls-files evidence/unversioned-fragment-source.cs` returns no entry), so do not imply it was published. Retain reference attribution and independently document format facts; investigate any additional source used for zero-mask formula before categorical independence claims. No automatic relicensing warranted by this evidence.

## Limits across the combined review

The corpus includes the source actually preserved locally and the pinned reference snapshots, not every historical upstream version. Native comparison is token-aware, not C++ AST-aware; Python includes AST and identifier-normalized AST checks. Documentation comparison covers 42 tracked RC4 Markdown files and 19 reference documents, not all untracked research notes or every external web page. Standard library/runtime binaries are inventoried separately, not compared by decompilation. Third-party game mod DLLs were not executed and no binary semantic-equivalence proof was attempted. Generic engine names, ABI layouts, signatures, serialized format constants and ordinary algorithms do not establish copying.

Reproduction tools/results are preserved under `D:/HobbyDevelopment/SDKProvenanceAudit/native/` (`compare.py`, `comments.py`, `native-comparison.json`, `native-comments-strings.json`) and `.../python/` (`compare.py`, `ast_compare.py`, `docs_compare.py`, `python-comparison.json`, `ast-renamed.json`, `docs-comparison.json`). The reports retain material file/range/commit evidence even if those local scratch directories are not distributed.


## Remediation addendum — 2026-10-12

The original RC4 findings above remain historical evidence. The authorized runtime-notice remediation is documented in [runtime-license-remediation.md](runtime-license-remediation.md), with component-by-component dispositions and [actual candidate verification](runtime-license-verification.json).

D1 is **partially resolved**: applicable authentic notice texts and pinned applicability evidence are now packaged and verified, including Expat; five platform/test-only inventory entries are not applicable with evidence. Microsoft entitlement/downstream protective-terms agreement questions and historical native build provenance remain unresolved. OpenSSL3.0.21's exact source/binary trees have no NOTICE file; its license and authentic attribution are included. No whole-distribution legal clearance is claimed.

The local `0.1.0-rc4-license1` candidate retains all34 official runtime files,115 SDK source/script files,five native payload files and both bundled mod archives byte-for-byte from RC4. First-party MIT and the user-authored Harness remain unchanged. Full regression:1,017tests passed; clean-install `--check` passed. No new live-game validation, published RC4 modification, tag, push or release occurred. This addendum supersedes only the current remediation status, not the historical RC4 observations.
