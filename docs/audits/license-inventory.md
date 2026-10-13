# License inventory

Audit snapshot: 2026-10-12 America/New_York (release timestamps use UTC). RC4 publication commit **1fc1ea2babc3d173c9d732bc641a9a23b5a1c744**; current checkout HEAD **695b062823e63ab7821ccf22cb0378cb376e3cd8** plus pre-existing uncommitted viewer work. Release and working-tree findings are distinguished. This audit writes reports only; no implementation, license, notice, history, release or installed-runtime changes were made.

These are evidence-based technical compliance findings, not a determination of infringement or comprehensive legal clearance. “No identified concern” means no concern identified within the stated examination, not proof that no third-party rights exist.

## Licensing boundary

The root MIT license describes the project's declared first-party code license, including the user-authored Harness port. It does **not** license Python, Microsoft's runtime, Unreal Engine or the game. RC4 `THIRD_PARTY_NOTICES.md:1–13` already states this separation. The stronger assertion that all incorporated Python licenses are preserved solely in `SDK/runtime/LICENSE.txt` needs qualification: D1 below identifies missing incorporated-notice evidence.

There is no identified substantial LGPL implementation reuse that establishes a requirement to relicense the SDK. That conclusion is bounded by the comparison coverage; it is not a blanket ownership warranty. Root MIT alone is insufficient as a description of the complete binary distribution.

## First-party and reference inventory

“Not redistributed” below means not found as a component in the examined RC4 ZIP/optional archives, not a proof against transformed source copying. Development tools and reference repositories are not automatically release dependencies. All first-party source below is at RC4 `1fc1ea2babc3d173c9d732bc641a9a23b5a1c744` unless noted.

| Component | Source/revision | Declared license / precision | Modification / redistribution / connection | Confidence and obligations |
|---|---|---|---|---|
| Native runtime, bootstrap, readers, headers, build scripts | This repository `native/`, `scripts/` | MIT, root LICENSE:1–21 | Project implementation; compiled outputs redistributed; process hooks/Windows APIs | Source declaration confirmed; binary reproducibility unresolved; preserve MIT notice |
| Python SDK and controller | `src/expedition33`, release scripts | MIT | Project implementation; source redistributed and imported by external Python | Source archive correspondence verified; preserve MIT |
| Introspection core/agent/CLI | User-authored BL4 snapshot; exact hashes/ranges in source-similarity.md | MIT ©2026 Mattmab; user confirms ownership | Core copied, adapters modified; SDK core redistributed, development CLI in source repo | First-party port; adjacent MIT preserved; upstream snapshot Git commit unknown |
| SDKManagement / IntrospectionHarness mods | `mods/` RC4 | MIT | Bundled .sdkmod modules imported by SDK | LICENSE present in both nested archives |
| ContinentFlight / PictoEditor / Statistics / Cinematics | `mods/` RC4; independent release tags | MIT | Optional .sdkmods, imported by SDK; each LICENSE retained | MIT applies to authored code, not game assets referenced by path |
| Other tracked example/viewer mods, tests, documentation | This repository RC4; dirty viewer changes separately considered | Root MIT declaration | Source repo redistribution; not additional RC4 optional binary assets | No qualifying external implementation match identified; not every author's chain of title independently reconstructed |
| unrealsdk | bl-sdk/unrealsdk `ac31716b2b462e78f0a841b6d352aa2fa56c7f92` | LICENSE:1–10: LGPL version 3 text; **or-later grant not established** | Implementation inspected; no direct component redistribution/link identified | Record as LGPL-3.0 observed, do not silently convert to LGPL-3.0-or-later; copied/linked use would need separate review |
| pyunrealsdk | bl-sdk/pyunrealsdk `cb5fc362ea228727f334d94b64eb9538d8778bc6` | Same LGPL v3 text; **or-later grant not established** | Implementation inspected; no direct component redistribution/import identified | Same conditional review; no detected substantial match |
| oak2-mod-manager | bl-sdk/oak2-mod-manager `d606e796733eced318e2a44e51b871a7becae55e` | `src/__main__.py:1–12` expressly Version 3, no later clause; `manager_pyproject.toml:13` LGPL3 | Implementation inspected; no component shipped | LGPL-3.0-only for examined explicit grant; subcomponents require own grants |
| mods_base 1.12 / console_mod_menu 1.6 | Preserved installed archives; commits unknown, hashes in source-similarity.md | LGPL v3 license texts retained in originals; later-version grant unresolved | Python source inspected; no direct redistribution/import identified | Do not equate installed bytes to Oak2 gitlink without comparison |
| MattsBL4ModsMenu 1.3.3 | Preserved archive SHA256 in source-similarity.md | MIT ©Mattmab | Implementation reference; no qualifying matching implementation identified | Preserve source history; original source commit unknown |
| UAssetAPI FFragment | atenfyr/UAssetAPI `74ed8bb3bd4eb75c5365e65a2a4191e07df52d5d` content match | MIT, same-commit LICENSE:1–21 | Whole reference file in untracked evidence; format knowledge used; not shipped | Attribution review, preserve MIT with any substantial source redistribution |
| retoc | trumank/retoc v0.1.5; historical exact commit unresolved | MIT, tag LICENSE:1–20 ©Truman Kilen and Archengius | Development executable and source read; not shipped | Preserve notices if redistributed; no SDK linkage observed |
| repak Oodle loader | trumank/repak master download; commit unresolved | Historical applicable grant not established in this audit | Source read in untracked evidence; not shipped | Unresolved reference license/commit; resolve before copying or redistributing any code |
| Statistics / CineReplay third-party DLLs | User-provided artifacts; Statistics hash in provenance report | No source grant established | Static reference analysis recorded; not RC4 dependencies | No license inferred from possession. No binary execution or copying into RC4 by this audit |
| Game/Unreal definitions, offsets, cinematic catalog | Target game reflection/static research, build hash in release manifest | Proprietary rights not granted by SDK MIT | Runtime interaction; names/paths/catalog JSON shipped, no game executable/media archive member | Reverse-engineering/asset-metadata rights outside completed source comparison; do not claim game assets MIT |

## Other actual development references

Commits are independently recorded from preserved clones; full commit table is in code-provenance.md. Source-study evidence for these tools is primarily README/architecture reading, not evidence they were incorporated. None appears as an RC4 archive component. Listed licenses are root licenses; their own dependency trees are not transitively relicensed or exhaustively audited because they are not redistributed here.

| Repository | Pinned commit | Root license evidence | Use |
|---|---|---|---|
| bethington/ghidra-mcp | 9cc29c0f1efb6c63a7d6898c9a23aff39397f992 | LICENSE:1–4 Apache-2.0 | Development tool installation/reference |
| HexRaysSA/ida-mcp | 2e62361d4c472fde93365613fd4fdcd2c1f6a4cb | LICENSE:1–21 MIT | Architecture reference |
| icsharpcode/ILSpy | b379738b7fae10027bd3c30cc2190677aea48e3b | LICENSE:1–21 MIT | Architecture/tool reference |
| morluto/rea | 3b2ec69c54fc9cf65bf8441edbb96e9619c3a37e | LICENSE:1–21 MIT | Architecture reference; separate third_party licenses exist |
| rehan-remade/universal-modder | 8370faa8e114baf33acdb23079aff552a7728c4b | LICENSE:1–21 MIT | Architecture reference |
| SamboyCoding/Cpp2IL | b5ad444b82267cb1e4b88b8b373c008105bdea52 | LICENSE:1–21 MIT | Architecture reference |
| trevaintdead/ai-game-modding-guides | 1c8df26a64f3d8604fa05ac2b3d3b65c0dde31ef | LICENSE:1–21 MIT | Documentation reference |

Other local development tools (Ghidra, Java, compiler/build environment, analysis-only Python packages) were not found in the release. Their entire installed dependency trees and procurement terms were not audited. This inventory covers actual release components plus identified development references, not every program on the development PC.

# Independent RC4 dependency audit

Scope: published SDK ZIP SHA256 `6f0498a9fab2d901992b16120d286b95c3874f6b60b9cb708385501d5c0faf3c`, optional four sdkmods, source RC4 `1fc1ea2babc3d173c9d732bc641a9a23b5a1c744`. Static read-only archive/PE inspection, no bundled binaries executed. No repository edits.

## Confirmed distribution

34 files under SDK/runtime are byte-identical, with no extras, to official CPython `python-3.13.15-embed-amd64.zip`, SHA256 `d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf`. This equals RC4 scripts/prepare_runtime.py lines8–10 pin. Download URL https://www.python.org/ftp/python/3.13.15/python-3.13.15-embed-amd64.zip. CPython annotated v3.13.15 tag9cb432a43babc597b349cabb704870e88a82a382 resolves to commit4061bc4c35f7c26f25264666d4ba083b93d2f6f9. All runtime is unmodified as distributed by Python upstream. This does not mean all incorporated licenses are covered by PSF alone.

Nested python313.zip contains541 members, only site-packages/README.txt under site-packages. No third-party pip distribution observed. SDK source is imported by external CPython controller. Runtime modules dynamically load Python and listed DLLs; SDK's native binaries import Windows system DLLs only: version.dll KERNEL32.dll; research_probe.exe bcrypt.dll, USER32.dll,KERNEL32.dll; runtime_session_picto_v4.dll USER32.dll,KERNEL32.dll. No bl-sdk DLL import or binary member observed. Imports cannot rule out statically incorporated third-party code or runtime LoadLibrary paths. No reproducible native build was performed; distributed native binary correspondence to source remains not cryptographically established by these checks. Build scripts use Microsoft cl; bootstrap explicitly /MT (scripts/build-bootstrap.cmd line10), so Microsoft runtime code may be statically linked even absent CRT import.

## Inventory and obligations

| Component | Version/source evidence | Distribution/form | License/condition | Assessment |
|---|---|---|---|---|
| CPython core and stdlib |3.13.15 exact official bytes; commit above |python313.dll,python3.dll,exe,stdlibpyc ZIP,pyd |PSF-2.0 plus historical BeOpen,CNRI,CWI terms and incorporated components; retain license/copyright, modifications summary if modified |Runtime LICENSE.txt lines62–261 retained. High confidence unmodified |
| Microsoft CRT |official Python bytes; vcruntime140.dll,vcruntime140_1.dll; SDK /MT|DLLs and embedded runtime code|Microsoft redistribution terms, not MIT/PSF; runtime LICENSE.txt lines281–318 records restrictions |Retained notice confirmed; exact build-tool redistribution rights/flowdown need separate review |
| OpenSSL |CPython PCbuild/python.props line79 pins3.0.21|libcrypto-3.dll,libssl-3.dll via _ssl,_hashlib|Apache-2.0; license, applicable notices, mark modifications |Apache text runtime LICENSE.txt lines386–557 present; attribution/NOTICE inventory still review |
| libffi |python.props line75 pins3.4.4|libffi-8.dll via _ctypes|MIT; retain copyright/permission |Runtime LICENSE.txt lines364–382 retained |
| bzip2 |python.props line73 pins1.0.8|_bz2.pyd incorporated library|bzip2-1.0.6 style license; no false origin, mark changes, no endorsement |Runtime LICENSE.txt lines324–360 retained |
| liblzma |python.props line74 pinsXZ5.2.5; PCbuild/_lzma.vcxproj lines97,114|_lzma.pyd static liblzma|XZ5.2.5 COPYING lines5–14 identifies liblzma public domain, CLI getopt distinct LGPL2.1+ |Do not classify entire package LGPL/GPL based on unrelated CLI/build scripts; no XZ CLI shipped |
| SQLite |python.props line72 pins3.50.4.0|sqlite3.dll via _sqlite3.pyd|Upstream public-domain claim; exact source grant not fetched in this audit |Version high confidence from pinned upstream build config, license exact-source review unresolved |
| zlib |python.props line83 pins1.3.1|compiled CPython compression support|zlib license; source notice retention/no false origin/mark changes |Doc/license.rst lines906–934 supplies license but runtime LICENSE.txt does not; current-version copyright not independently fetched |
| Expat |Modules/expat/expat.h lines1095–1097 pins2.8.2|pyexpat.pyd and likely _elementtree|MIT; Modules/expat/COPYING lines1–21 requires notice in copies |Confirmed missing identifiable notice text in shipped files, priority notice review |
| libmpdec |python.props line78 pins4.0.0|_decimal.pyd|BSD-2-Clause, Doc/license.rst lines978–1008 includes binary notice requirement |Notice scan absent Stefan Krah; review/add exact external version notice |
| Mersenne Twister |CPython Doc/license.rst lines305–352|_random in python313.dll|BSD3 style retained copyright/binary notice/no endorsement |No Matsumoto notice string found; supplement notice package after build applicability check |
| mimalloc |Doc/license.rst lines1048–1073|CPython build allocator; precise binary applicability not traced|MIT |No Daan Leijen notice string; review applicability |
| uvloop excerpts |Doc/license.rst lines1076–1107 documents asyncio incorporation fromuvloop0.16|asyncio/_asyncio|MIT |No MagicStack notice string; review/add exact notice |
| Unicode data |Doc/license.rst lines1137–1186|unicodedata.pyd, corestrings|Unicode Licensev3 per pinned upstream doc|No Unicode notice string; review full applicable version/data evidence |
| SDK/optionalmods |RC4 samecommit|first-party source and compiled binaries|MIT stated, separate licensing where applicable |Each optional archive LICENSE present. User specifically confirms IntrospectionHarness authorship; treat as user-owned port, not third-party LGPL code |
| setuptools |pyproject build-system requires>=68|build dependency, no pip/site-package in release |License/version not pinned; not observed redistributed |Development-only; wheel audit would require separate artifact |

Reference license texts and exact-line evidence: https://github.com/python/cpython/blob/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/Doc/license.rst ; https://github.com/python/cpython/blob/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/PCbuild/python.props ; https://github.com/python/cpython/blob/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/Modules/expat/COPYING . XZ https://github.com/tukaani-project/xz/blob/v5.2.5/COPYING.

## Material finding D1 — incorporated runtime notices need review

Confirmed: LICENSE.txt is retained exactly as Python supplies it, but that file does not contain all notices in the pinned upstream Doc/license.rst. Scanned every expanded release member AND541 nested standardlibrary ZIP members for Thai Open, Expat maintainers, Stefan Krah, Matsumoto, Daan Leijen, MagicStack, Unicode License/UNICODE LICENSE, Marek Majkowski: zero ASCII matches. Exact Expat COPYING lines1–21 has copyright and MIT inclusion condition and pyexpat.pyd is actually present. This is evidence for license-compliance review and supplemental notice bundle, not a legal infringement conclusion. Search cannot prove every notice absent in every encoding, and binary upstream builds may have special arrangements not established here. Safe next action is add exact applicable incorporated notices from pinned upstream sources after approval, separately from root MIT; verify each embedded library version. Also assess Microsoft terms and OpenSSL NOTICE applicability. No basis found to impose LGPL/GPL source/relink obligations merely because Python is GPL-compatible or XZ source tree contains GPL tools.

## Other limitations

No complete binary static code attribution, source-to-binary rebuild, compiler runtime license-entitlement audit, nested bytecode decompilation, or every stdlib notice review. Additional CPython incorporated software (dtoa,SipHash,XMLRPC,cookies,etc) remains part of full upstream notice review. Documentation says incorporated list itself incomplete. No source distribution obligation identified for confirmed permissive runtime components beyond their respective conditions. Conditional LGPL source/relink obligations depend on actual copied/linked LGPL code; native/Python comparison agents own this question. Read LICENSE application grants, not GitHub badges: LGPLv3 license section6 contains conditional or-later mechanics, not an automatic per-project or-later grant. Do not infer LGPL-3.0-or-later solely from that section.

## Evidence files

runtime-byte-comparison.json,pe-imports.json,notice-string-scan.json; python.props,python-license.rst,expat-COPYING,expat.h,xz-COPYING,lzma.vcxproj,cpython-tag.json,cpython-tag-object.json; extracted archive LICENSE/THIRD_PARTY_NOTICES and archive member listings. All under D:/HobbyDevelopment/SDKProvenanceAudit/dependencies.

Optional hashes: Cinematics ce983e48928556ca4c454eab23023f95665dc8479061c252517a375619ad737e; ContinentFlight2afa10adf298d7ccf53c83b2abad4ba94d08c3d5982ddfdcb2655ed2a88280d0; PictoEditorc313fb37f32ea437b9956de0222deb9c943f53470b6e06bd153d827b7f96fe0a; Statisticsc401992a362f5c85a4bb1d4af0ac63b3667c0dfba393b99e298819de28979274.

## Conditional distribution obligations and decisions

For MIT portions, retain copyright and permission text with copies/substantial portions. User-owned code can remain MIT; no notice removal is proposed. For PSF/runtime components, retain each applicable grant and notices; unmodified upstream bytes do not eliminate incorporated-component obligations. Apache-2.0 components require their license and applicable notices and change notices if modified; identify whether an upstream NOTICE applies rather than assuming the Apache license text alone is exhaustive.

If future evidence establishes covered LGPL library copying or a combined work, evaluate the actual grant: source/changes, copyright/license notices, and LGPL v3 section 4's replacement/recombination alternatives and applicable installation information. A suitable shared-library mechanism and relinkable application-code route are alternatives under specified conditions, not a blanket demand to open-source every application. For actual GPL-covered redistribution, evaluate corresponding-source and covered-work licensing obligations under the applicable GPL version. Neither reading a reference nor functional similarity alone triggers those conclusions. [GNU LGPL v3](https://www.gnu.org/licenses/lgpl-3.0.html), sections 0, 4 and 6, also available in the pinned reference LICENSE, supplies the conditional rules; its section 6 is not itself an “or later” grant for every project.

No reference grant was upgraded from LGPL-3.0 to LGPL-3.0-or-later based on a GitHub badge or the standard license's discussion of future versions. Resolve grant ambiguity with the rightsholder before relying on broader permissions.

Priority: D1 incorporated runtime notice supplementation/review before next release; then Microsoft/OpenSSL applicability, binary build provenance and remaining source-reference pins. No automatic relicensing or implementation rewrite is recommended from the current comparison results. Obtain permission or legal review if a material unresolved source-rights issue emerges.


## Remediation addendum — 2026-10-12

The original RC4 findings above remain historical evidence. The authorized runtime-notice remediation is documented in [runtime-license-remediation.md](runtime-license-remediation.md), with component-by-component dispositions and [actual candidate verification](runtime-license-verification.json).

D1 is **partially resolved**: applicable authentic notice texts and pinned applicability evidence are now packaged and verified, including Expat; five platform/test-only inventory entries are not applicable with evidence. Microsoft entitlement/downstream protective-terms agreement questions and historical native build provenance remain unresolved. OpenSSL3.0.21's exact source/binary trees have no NOTICE file; its license and authentic attribution are included. No whole-distribution legal clearance is claimed.

The local `0.1.0-rc4-license1` candidate retains all34 official runtime files,115 SDK source/script files,five native payload files and both bundled mod archives byte-for-byte from RC4. First-party MIT and the user-authored Harness remain unchanged. Full regression:1,017tests passed; clean-install `--check` passed. No new live-game validation, published RC4 modification, tag, push or release occurred. This addendum supersedes only the current remediation status, not the historical RC4 observations.
