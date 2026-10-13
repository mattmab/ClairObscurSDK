# RC4 release compliance verification

Audit snapshot: 2026-10-12 America/New_York (release timestamps use UTC). RC4 publication commit **1fc1ea2babc3d173c9d732bc641a9a23b5a1c744**; current checkout HEAD **695b062823e63ab7821ccf22cb0378cb376e3cd8** plus pre-existing uncommitted viewer work. Release and working-tree findings are distinguished. This audit writes reports only; no implementation, license, notice, history, release or installed-runtime changes were made.

These are evidence-based technical compliance findings, not a determination of infringement or comprehensive legal clearance. “No identified concern” means no concern identified within the stated examination, not proof that no third-party rights exist.

## Decision

**Do not treat RC4 as fully license-cleared for another release yet.** The examined code comparisons do not identify substantial LGPL copying requiring SDK relicensing. The actionable release issue is the incorporated Python notice inventory, especially Expat; native source-to-binary reproducibility and several reference/version details remain unresolved. This is a release-review recommendation, not an infringement finding. No release was changed or published by this audit.

The user-authored Introspection Harness is first-party code and is not a third-party blocker. Its notice is retained in source and the actual distribution.

## Exact artifacts examined

Public [RC4 release](https://github.com/mattmab/ClairObscurSDK/releases/tag/v0.1.0-rc4), GitHub release ID 411165167, SDK asset ID 635563472. Published `2026-10-13T01:52:55Z` (October 12, 21:52:55 America/New_York). API target and audit clone tag resolve to `1fc1ea2babc3d173c9d732bc641a9a23b5a1c744`. Asset size 13,538,188 bytes. GitHub marks the release mutable; these conclusions apply to the following content hashes, not any future replacement under the same tag.

The SDK and four optional mod archives were downloaded from their public GitHub releases, not inferred solely from local staging folders. Optional tags are `mod-cinematics-v0.1.0-rc1`, `mod-continentflight-v0.1.0-rc1`, `mod-pictoeditor-v0.1.0-rc1`, `mod-statistics-v0.1.0-rc1`, all targeting RC4 commit above. SDK ZIP digest matches its API SHA256.

| Artifact | SHA256 | Top-level archive file count |
|---|---|---:|
| Cinematics.sdkmod | `ce983e48928556ca4c454eab23023f95665dc8479061c252517a375619ad737e` | 3 |
| ContinentFlight.sdkmod | `2afa10adf298d7ccf53c83b2abad4ba94d08c3d5982ddfdcb2655ed2a88280d0` | 2 |
| Expedition33-SDK-0.1.0-rc4.zip | `6f0498a9fab2d901992b16120d286b95c3874f6b60b9cb708385501d5c0faf3c` | 163 |
| PictoEditor.sdkmod | `c313fb37f32ea437b9956de0222deb9c943f53470b6e06bd153d827b7f96fe0a` | 3 |
| Statistics.sdkmod | `c401992a362f5c85a4bb1d4af0ac63b3667c0dfba393b99e298819de28979274` | 2 |

## Verification results

| Check | Result | Evidence / limit |
|---|---|---|
| Actual SDK artifact identity | PASS | Public download SHA256 agrees with API digest; 163 file entries |
| SDK release-manifest file hashes | PASS | Every listed SDK file matched; separate bootstrap hash matched |
| Packaged SDK Python/source vs RC4 | PASS | 115 files under SDK/src and SDK/scripts equal tagged source after CRLF/LF normalization; 46 byte-identical, 69 line-ending-only differences |
| Official runtime identity | PASS | All 34 SDK/runtime members byte-identical to pinned CPython3.13.15 embedded ZIP; no extra runtime files |
| Top-level MIT / third-party notice | PASS (presence only) | SDK/LICENSE and SDK/THIRD_PARTY_NOTICES.md retained; semantic completeness reviewed separately |
| Harness MIT notice | PASS | SDK/src/expedition33/introspection/LICENSE included; first-party authorship confirmed by user |
| Bundled mods | PASS | SDKManagement and IntrospectionHarness only; nested archives include LICENSE |
| Optional mod notices | PASS | Each of four .sdkmods contains LICENSE |
| All six mod archives vs RC4 source | PASS | 14 member files equal tagged source after line-ending normalization; 8 byte-identical |
| No BL SDK runtime binaries | PASS within inspected archive/import scope | No bl-sdk component member or import-table dependency; no binary semantic proof against static incorporation |
| Python incorporated-license notices | REVIEW REQUIRED | Expat notice not identified; other incorporated notices require exact applicability review; license-inventory.md D1 |
| Native binaries correspond exactly to tagged source | UNVERIFIED | Manifest authenticates bytes, not build derivation; no reproducible rebuild/link map performed |
| Microsoft CRT redistribution entitlement / OpenSSL applicable notices | UNRESOLVED | Terms/license text retained, complete applicability/entitlement not established |
| Full code originality / absence of transformed copying | NOT CERTIFIED | Bounded comparisons and selected history review; no inference that AI output guarantees independence |
| Future wheels / other releases | NOT AUDITED | This decision covers exact RC4 ZIP and four optional archives, not hypothetical wheel packaging |

No supplied third-party CineReplay/Statistics DLL or game media asset was an archive member. The project's own bootstrap is also named `version.dll`; that name alone does not identify it as the unrelated quarantined third-party loader. PE imports and source build path were inspected, but binary reproducibility remains open.

## Is MIT an accurate description?

MIT remains the **declared first-party license**, and no examined substantial LGPL source match establishes that the declaration must change. It is not an accurate blanket license for every shipped byte. Python and its incorporated libraries and Microsoft redistributables retain separate terms. RC4 already states this boundary, but `THIRD_PARTY_NOTICES.md:6–9` overstates completeness if understood to mean its single embedded LICENSE.txt supplies every incorporated notice. Correct that claim and the notice bundle together after approval; do not remove the MIT license or infer wholesale LGPL relicensing from source exposure.

## Prioritized remediation checklist

- [ ] **P1 — Runtime notices:** collect applicable notices from pinned CPython source and exact external library versions, beginning with Expat COPYING; include them as separate third-party notices in the next candidate. Check mpdecimal, random, asyncio/uvloop excerpts, Unicode, allocator applicability and remaining upstream inventory. Verify OpenSSL NOTICE applicability. Do not merely add a generic license link.
- [ ] **P1 — Verify candidate packaging:** after approval to modify notices, re-open actual ZIP and nested archives and verify notices/hashes against source and inventory. Update the completeness claim. No rebuilt candidate has been produced in this read-only audit.
- [ ] **P2 — Build provenance:** capture compiler/linker version, build flags, dependency inputs, object/link map where practical, source revision and output digests. Establish native source-to-binary correspondence; review Microsoft redistribution rights/conditions.
- [ ] **P2 — Reference provenance:** retain accurate implementation-access history, first-party Harness origin, UAssetAPI content pin; resolve remaining historical retoc/repak and installed BL4 package source anchors. Document zero-mask formula evidence. Do not call this a strict clean-room process.
- [ ] **P2 — Conditional rights review:** if further evidence identifies substantial third-party implementation, review grant/attribution/source/replacement obligations with the rightsholder or counsel; obtain permission or document an independent replacement if appropriate. Do not conceal provenance or erase history.
- [ ] **P3 — Repeat on release changes:** rerun source comparisons and archive license verification for changed code/dependencies. Include direct notice-file assertions and a machine-readable version/hash inventory in future release checks.

No finding currently meets “high-priority legal review” on the basis of a demonstrated substantial unauthorized match. D1 is “license compliance review”; incomplete build/reference provenance is “unresolved”; UAssetAPI reference accounting is “attribution review”; confirmed first-party ports and generic engine/boilerplate matches are “no identified concern.” These categories deliberately avoid a legal infringement label.

## Reproducibility and limitations

Local evidence: `D:/HobbyDevelopment/SDKProvenanceAudit/release/{rc4-api.json,releases-api.json,archive-verification.json,check_release.py}` and actual downloaded archives; `.../dependencies/{runtime-byte-comparison.json,pe-imports.json,notice-string-scan.json}` and pinned source notices; comparison/history files listed in the other reports. `archive-verification.json` records raw byte differences against the Windows checkout; the normalized source comparison resolves all 69 as line endings, not code changes.

This audit did not execute third-party binaries, alter installed SDK/game state, rebuild native artifacts, change licenses or publish releases. Existing uncommitted viewer work was preserved. The only repository additions are these four audit reports. Raw transcripts are kept local, not copied into published documentation.


## Remediation addendum — 2026-10-12

The original RC4 findings above remain historical evidence. The authorized runtime-notice remediation is documented in [runtime-license-remediation.md](runtime-license-remediation.md), with component-by-component dispositions and [actual candidate verification](runtime-license-verification.json).

D1 is **partially resolved**: applicable authentic notice texts and pinned applicability evidence are now packaged and verified, including Expat; five platform/test-only inventory entries are not applicable with evidence. Microsoft entitlement/downstream protective-terms agreement questions and historical native build provenance remain unresolved. OpenSSL3.0.21's exact source/binary trees have no NOTICE file; its license and authentic attribution are included. No whole-distribution legal clearance is claimed.

The local `0.1.0-rc4-license1` candidate retains all34 official runtime files,115 SDK source/script files,five native payload files and both bundled mod archives byte-for-byte from RC4. First-party MIT and the user-authored Harness remain unchanged. Full regression:1,017tests passed; clean-install `--check` passed. No new live-game validation, published RC4 modification, tag, push or release occurred. This addendum supersedes only the current remediation status, not the historical RC4 observations.
