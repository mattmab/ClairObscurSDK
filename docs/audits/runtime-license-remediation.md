# Python runtime license remediation

Review date: 2026-10-12, America/New_York. This is a remediation addendum; the original RC4 audit remains historical evidence. First-party source remains MIT. No tags, pushes or public release changes were made.

## Outcome

**D1 is partially resolved, not blanket compliance clearance.** Missing applicable incorporated notices were supplied from pinned authoritative sources and verified in the actual new ZIP. Expat, libmpdec, Mersenne Twister, mimalloc, asyncio/uvloop, Unicode, zlib, remaining applicable CPython inventory entries, HACL*/KaRaMeL and BLAKE2 now have included notice coverage. Microsoft redistribution entitlement/downstream agreement questions and historical native build provenance remain unresolved.

The local candidate is ready for focused compliance review, **not a recommendation to publish without resolving the Microsoft questions**. Adding notices does not establish assent to Microsoft's protective terms or qualifying toolchain entitlement. No implementation or architecture change is required by this finding at present; none was made.

## Original issues and what changed

RC4 preserved the official embedded `runtime/LICENSE.txt`, but it did not identify all incorporated notices documented by CPython source, with Expat the clearest missing notice. OpenSSL NOTICE applicability, exact external library notices and Microsoft redistribution conditions were also unverified. The original Python license file is unchanged. The SDK now includes 19 authentic upstream notice/reference text files, one explanatory README, and a machine-readable manifest under `SDK/licenses/`. Required texts are included, not replaced by URLs.

The manifest contains 30 component records: 23 applicable components with verified notice coverage, five absent platform/test components, and two Microsoft cases with partial/unresolved review. “Resolved” in this table concerns the identified notice/applicability question; it is not an unlimited legal warranty or a finding that every upstream binary was rebuilt independently.

## Component-by-component disposition

| Component | Version / source scope | Disposition | Incorporation evidence | Included notice paths (relative to SDK) |
|---|---|---|---|---|
| expat | 2.8.2 | Resolved — evidence supplied | PCbuild/pyexpat.vcxproj:94-107 compiles Modules/expat/xmlparse.c,xmlrole.c,xmltok.c with XML_STATIC; distributed pyexpat.pyd. Modules/expat/expat.h:1095-1097 version macros; runtime probe expat_2.8.2. | `licenses/python-incorporated/Expat-2.8.2-COPYING.txt` |
| mpdecimal | 4.0.0 | Resolved — evidence supplied | PCbuild/python.props:78 mpdecimal-4.0.0; PCbuild/_decimal.vcxproj:127-141 compiles libmpdec into distributed _decimal.pyd. Runtime decimal.__libmpdec_version__=4.0.0. | `licenses/python-incorporated/mpdecimal-4.0.0-COPYRIGHT.txt` |
| mersenne-twister | MT19937 CPython 3.13.15 variant | Resolved — evidence supplied | PCbuild/pythoncore.vcxproj:433 compiles Modules/_randommodule.c; _random built into python313.dll. Doc/license.rst:305-352 contains full original notice. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| mimalloc | 2.1.2 CPython vendored variant | Resolved — evidence supplied | Include/internal/mimalloc/mimalloc.h:11 MI_MALLOC_VERSION 212; PC/pyconfig.h.in:532 WITH_MIMALLOC 1. PCbuild/pythoncore.vcxproj:522 compiles Objects/obmalloc.c; Objects/obmalloc.c:14-22 includes mimalloc/static.c. | `licenses/python-incorporated/mimalloc-2.1.2-LICENSE.txt`, `licenses/python-incorporated/mimalloc-vendored-copyright-headers.txt` |
| asyncio-uvloop-excerpts | uvloop 0.16 excerpts in CPython 3.13.15 | Resolved — evidence supplied | Lib/asyncio/constants.py:1-4,events.py:3-6,sslproto.py:1-4 identify uvloop v0.16.0 and MagicStack MIT. asyncio/constants.pyc,events.pyc,sslproto.pyc present in actual python313.zip. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| unicode-data | 15.1.0 | Resolved — evidence supplied | Modules/unicodedata_db.h:3 UNIDATA_VERSION 15.1.0; distributed unicodedata.pyd; runtime probe confirms15.1.0. Doc/license.rst:1137-1186 explicitly grants Unicode License v3 for incorporated data. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| zlib | 1.3.1 | Resolved — evidence supplied | PCbuild/python.props:83 pins zlib-1.3.1; pythoncore.vcxproj:645-658 compiles zlib sources. Runtime ZLIB_RUNTIME_VERSION1.3.1. | `licenses/python-incorporated/zlib-1.3.1-LICENSE.txt` |
| cookie-management | CPython 3.13.15 incorporated source | Resolved — evidence supplied | Lib/http/cookies.py; Doc/license.rst:418-443 http/cookies.pyc present in distributed python313.zip. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| execution-tracing | CPython 3.13.15 incorporated source | Resolved — evidence supplied | Lib/trace.py; Doc/license.rst:446-476 trace.pyc present in distributed python313.zip. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| uu-codec | CPython 3.13.15 incorporated source | Resolved — evidence supplied | Lib/encodings/uu_codec.py; Doc/license.rst:479-506 encodings/uu_codec.pyc present in distributed python313.zip. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| xmlrpc-client | CPython 3.13.15 incorporated source | Resolved — evidence supplied | Lib/xmlrpc/client.py; Doc/license.rst:509-539 xmlrpc/client.pyc present in distributed python313.zip. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| siphash | CPython SipHash13/24 variant | Resolved — evidence supplied | PCbuild/pythoncore.vcxproj:556 Python/pyhash.c; Include/pyhash.h:42-48 defaults SipHash13 on supported aligned targets. Python/pyhash.c retains Marek Majkowski notice; Doc/license.rst:599-625. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| dtoa | CPython 3.13.15 David Gay derived conversion | Resolved — evidence supplied | PCbuild/pythoncore.vcxproj:629 compiles Python/dtoa.c; Doc/license.rst:628-655 preserves full notice. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| cfuhash | CPython 3.13.15 derived hashtable | Resolved — evidence supplied | PCbuild/pythoncore.vcxproj:594 compiles Python/hashtable.c; Doc/license.rst:937-975. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| gus-qsbr | CPython 3.13.15 FreeBSD-derived | Resolved — evidence supplied | PCbuild/pythoncore.vcxproj:628 unconditionally compiles Python/qsbr.c; Python/qsbr.c:1-32 preserves Jeffrey Roberson notice. | `licenses/python-incorporated/CPython-3.13.15-license.rst` |
| wide-socket-fallback | CPython 3.13.15 WIDE fallback | Not applicable — evidence supplied | Modules/socketmodule.h:63-75 Windows SDK defines HAVE_GETADDRINFO/HAVE_GETNAMEINFO; socketmodule.c:450-461 compiles WIDE fallback only without them. | No notice required for this absent component; upstream inventory retained for context. |
| asyncore-asynchat-tests | CPython 3.13.15 test support | Not applicable — evidence supplied | Doc/license.rst:390-415 identifies Lib/test/support/asynchat.py and asyncore.py; test package absent from python313.zip. | No notice required for this absent component; upstream inventory retained for context. |
| test-epoll | CPython 3.13.15 test suite | Not applicable — evidence supplied | Lib/test/test_epoll.py absent from actual python313.zip. | No notice required for this absent component; upstream inventory retained for context. |
| select-kqueue | CPython 3.13.15 BSD interface | Not applicable — evidence supplied | Modules/selectmodule.c:1728 guards kqueue implementation with HAVE_KQUEUE; Windows config does not define HAVE_KQUEUE. | No notice required for this absent component; upstream inventory retained for context. |
| w3c-c14n-tests | C14N 2.0 test suite | Not applicable — evidence supplied | Lib/test/xmltestdata/c14n-20 absent from embedded python313.zip. | No notice required for this absent component; upstream inventory retained for context. |
| hacl-karamel | HACL* bb3d0dc8d9d15a5cd51094d5b69e70aa09005ff0 CPython variant | Resolved — evidence supplied | PCbuild/pythoncore.vcxproj:424-427 compiles Hacl_Hash_MD5/SHA1/SHA2/SHA3.c; Modules/_hacl/refresh.sh:25 pins HACL source. Generated hash headers carry MIT; include/krml/internal/target.h carries Apache-2.0. Source headers retained verbatim. | `licenses/python-incorporated/HACL-KaRaMeL-Apache-2.0.txt`, `licenses/python-incorporated/HACL-dist-LICENSE.txt`, `licenses/python-incorporated/HACL-KaRaMeL-source-notices.txt` |
| blake2 | CPython 3.13.15 incorporated reference | Resolved — evidence supplied | PCbuild/pythoncore.vcxproj:416-418 compiles _blake2 wrapper and implementations; blake2b_impl.c includes impl/blake2b-ref.c on default Windows build. Modules/_blake2/impl/blake2b-ref.c:1-12 CC0 dedication; full legal text and source-specific dedications included. | `licenses/python-incorporated/CC0-1.0.txt`, `licenses/python-incorporated/BLAKE2-source-notices.txt` |
| cpython | 3.13.15 | Resolved — evidence supplied | Official Windows embedded runtime; all 34 RC4 files previously byte-verified against upstream archive SHA256 d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf. Core and stdlib; incorporated components have separate terms. | `licenses/python-external/CPython-LICENSE.txt` |
| openssl | 3.0.21 | Resolved — evidence supplied | libcrypto-3.dll and libssl-3.dll imported by _ssl.pyd/_hashlib.pyd. PCbuild/python.props:79-81 and get_externals.bat select 3.0.21; parent runtime probe reports OpenSSL 3.0.21 9 Jun 2026. | `licenses/python-external/OpenSSL-LICENSE.txt`, `licenses/python-external/OpenSSL-AUTHORS.md` |
| libffi | 3.4.4 | Resolved — evidence supplied | libffi-8.dll via _ctypes.pyd. CPython python.props:75 and get_externals.bat select libffi-3.4.4. Binary-deps notice matches source-deps73b247f34ef3ae1859b8c2c34d321d34ebc5db15 notice after line-ending normalization. | `licenses/python-external/libffi-LICENSE.txt` |
| bzip2 | 1.0.8 | Resolved — evidence supplied | _bz2.pyd contains library; CPython python.props:73 and get_externals.bat select bzip2-1.0.8. License text itself states version1.0.8 dated13July2019; SPDX identifier describes license family, not component version. | `licenses/python-external/bzip2-LICENSE.txt` |
| liblzma | 5.2.5 | Resolved — evidence supplied | _lzma.pyd statically incorporates liblzma: pinned PCbuild/liblzma.vcxproj lists src/liblzma and two src/common/tuklib helpers; CLI getopt/GPL scripts are not compiled. COPYING distinguishes public-domain library and build/CLI licenses. | `licenses/python-external/XZ-COPYING.txt` |
| sqlite | 3.50.4.0 | Resolved — evidence supplied | sqlite3.dll via _sqlite3.pyd. CPython python.props:72 pins3.50.4.0; source tag dereferenced to ef547e549b49a2822214ef7880c0ca212b32929e. sqlite3.h lines1-11 contain copyright disclaimer. sqlite3.c beginning identifies library3.50.4 and Fossil check-in4d8adfb30e03f9cf27f800a2c1ba3c48fb4c; same disclaimer at lines33-44. Runtime probe reports3.50.4. | `licenses/python-external/SQLite-NOTICE.txt` |
| microsoft-python-runtime | 14.51.36247.0 | Partially resolved | Official Python archive includes vcruntime140.dll and vcruntime140_1.dll; both PE FileVersion/ProductVersion14.51.36247.0. CPython notice also addresses code embedded by linking its .exe/.dll/.pyd. This version is distinct from SDK local toolset14.44.35207. | `licenses/python-external/Microsoft-CRT.txt` |
| microsoft-sdk-static-runtime | local MSVC14.44.35207; distributed binary build provenance not established | Unresolved | scripts/build-bootstrap.cmd:4,10 selects local VSBuildTools and explicit /MT. Microsoft documentation identifies /MT static LIBCMT linking; lack of CRT DLL imports does not remove Microsoft code. Compiler/install tools are development-only; linked runtime is not. | `licenses/python-external/Microsoft-CRT.txt` |

CPython's full pinned `Doc/license.rst` contains no unresolved include/literalinclude directives: its incorporated texts are actually present. It is supplemented by exact external-version notices where the document has older text; for example, libmpdec4.0.0's COPYRIGHT is 2008–2024, while the historical documentation excerpt is 2008–2020. Original texts are preserved rather than edited into an invented combined grant. The mimalloc and HACL/BLAKE2 excerpt files identify each source and retain its original leading copyright/license blocks verbatim.

GUS/QSBR is conservatively covered based on the Windows source build graph. Particular GIL-build code paths or linker dead-stripping are not independently proved at machine-code level. Its grant is retained rather than declaring unsupported absence. WIDE socket fallback and kqueue are excluded by Windows configuration; asyncore/asynchat support, epoll tests and C14N test data are absent test-only components in the embedded archive.

## Pinned inputs and authentic sources

Runtime: official `python-3.13.15-embed-amd64.zip`, SHA256 `d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf`; CPython source `4061bc4c35f7c26f25264666d4ba083b93d2f6f9`. All 34 original member hashes are in `licenses/runtime-dependencies.json` and rechecked against the final distribution. Component evidence cites the pinned build files, source files and actual module probes. Development-only compiler, setuptools and source/test trees are not redistributed merely because inspected.

| Notice file | Authoritative source revision/link | Included file SHA256 |
|---|---|---|
| `licenses/python-incorporated/CPython-3.13.15-license.rst` | [4061bc4c35f7c26f25264666d4ba083b93d2f6f9](https://github.com/python/cpython/blob/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/Doc/license.rst) | `952ac05720d7f1dcb63589b35eb0931b1442eb250230a4ad31198eddf0ad6abc` |
| `licenses/python-incorporated/Expat-2.8.2-COPYING.txt` | [4061bc4c35f7c26f25264666d4ba083b93d2f6f9](https://github.com/python/cpython/blob/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/Modules/expat/COPYING) | `31b15de82aa19a845156169a17a5488bf597e561b2c318d159ed583139b25e87` |
| `licenses/python-incorporated/mpdecimal-4.0.0-COPYRIGHT.txt` | [48316ec025c1ebe500854c332be0a12c640c7301](https://github.com/python/cpython-source-deps/blob/48316ec025c1ebe500854c332be0a12c640c7301/COPYRIGHT.txt) | `2713324211652ce4a60e6e21e54f9dc3004299e591b0933a352f1a89c5fb53c2` |
| `licenses/python-incorporated/zlib-1.3.1-LICENSE.txt` | [4dc98e1909830e2bdc2a9cc2236e3c5d5037335b](https://github.com/python/cpython-source-deps/blob/4dc98e1909830e2bdc2a9cc2236e3c5d5037335b/LICENSE) | `845efc77857d485d91fb3e0b884aaa929368c717ae8186b66fe1ed2495753243` |
| `licenses/python-incorporated/mimalloc-2.1.2-LICENSE.txt` | [43ce4bd7fd34bcc730c1c7471c99995597415488](https://github.com/microsoft/mimalloc/blob/43ce4bd7fd34bcc730c1c7471c99995597415488/LICENSE) | `19c99805e7a44a34b297a75d1edea9985e300066dfc024d5c99d4236d4573b5d` |
| `licenses/python-incorporated/mimalloc-vendored-copyright-headers.txt` | [4061bc4c35f7c26f25264666d4ba083b93d2f6f9](https://github.com/python/cpython/blob/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/Objects/mimalloc) | `9323877f0c2c561fc7a03eab648cb90f4d0898e27d691c8e8d98230c44d31bc8` |
| `licenses/python-incorporated/HACL-KaRaMeL-Apache-2.0.txt` | [bb3d0dc8d9d15a5cd51094d5b69e70aa09005ff0](https://github.com/hacl-star/hacl-star/blob/bb3d0dc8d9d15a5cd51094d5b69e70aa09005ff0/LICENSE) | `c5accbbd8546e94c34aed24afe689a617627d18eed5a6c48277e48db57c23851` |
| `licenses/python-incorporated/HACL-dist-LICENSE.txt` | [bb3d0dc8d9d15a5cd51094d5b69e70aa09005ff0](https://github.com/hacl-star/hacl-star/blob/bb3d0dc8d9d15a5cd51094d5b69e70aa09005ff0/dist/LICENSE.txt) | `998ce04fb8ad9dedb0bc1b44938f8c3dcf1089780fa105ce1c8c30fb5554d78c` |
| `licenses/python-incorporated/CC0-1.0.txt` | [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt) | `a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499` |
| `licenses/python-incorporated/HACL-KaRaMeL-source-notices.txt` | [4061bc4c35f7c26f25264666d4ba083b93d2f6f9](https://github.com/python/cpython/blob/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/Modules/_hacl) | `c0abc4cc944b47649da520895f789d1366f6e7a7a9b6ab1f606926eb6309cbca` |
| `licenses/python-incorporated/BLAKE2-source-notices.txt` | [4061bc4c35f7c26f25264666d4ba083b93d2f6f9](https://github.com/python/cpython/blob/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/Modules/_blake2) | `40a5f6c3309a1503fb27435f75e4b1a919e7b854122a0e43e0f769eb691e9670` |
| `licenses/python-external/CPython-LICENSE.txt` | [4061bc4c35f7c26f25264666d4ba083b93d2f6f9](https://raw.githubusercontent.com/python/cpython/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/LICENSE) | `78b12c3a81360b357002334f0e70ea0e92eebf7a9b358805c03c48484945f3bb` |
| `licenses/python-external/OpenSSL-LICENSE.txt` | [4c7747da0d1addd20c95c2f911f8d2e09254a3d2](https://raw.githubusercontent.com/python/cpython-bin-deps/4c7747da0d1addd20c95c2f911f8d2e09254a3d2/amd64/LICENSE.txt) | `ed72ce2b51ee58f117e5a021e2e04af158857f40269fbc03491f0b2a99dbcc96` |
| `licenses/python-external/OpenSSL-AUTHORS.md` | [460451a0bb19cdbf0ab1add4de1420d143995467](https://raw.githubusercontent.com/python/cpython-source-deps/460451a0bb19cdbf0ab1add4de1420d143995467/AUTHORS.md) | `5076ca441daef7fb35e904c2ac070880c7b3d58300a5a6aecac41e8f525f4412` |
| `licenses/python-external/libffi-LICENSE.txt` | [94cb9a1c7feb608adf2b9f8fe2dbd6925ffbf90d](https://raw.githubusercontent.com/python/cpython-bin-deps/94cb9a1c7feb608adf2b9f8fe2dbd6925ffbf90d/LICENSE) | `2c9c2acb9743e6b007b91350475308aee44691d96aa20eacef8e199988c8c388` |
| `licenses/python-external/bzip2-LICENSE.txt` | [05301997b2f9590f49c672cf3dfd3d3dfa7ad521](https://raw.githubusercontent.com/python/cpython-source-deps/05301997b2f9590f49c672cf3dfd3d3dfa7ad521/LICENSE) | `c6dbbf828498be844a89eaa3b84adbab3199e342eb5cb2ed2f0d4ba7ec0f38a3` |
| `licenses/python-external/XZ-COPYING.txt` | [c6bc0c612605622aaef101a33a751f9de2ecc193](https://raw.githubusercontent.com/python/cpython-source-deps/c6bc0c612605622aaef101a33a751f9de2ecc193/COPYING) | `bcb02973ef6e87ea73d331b3a80df7748407f17efdb784b61b47e0e610d3bb5c` |
| `licenses/python-external/SQLite-NOTICE.txt` | [ef547e549b49a2822214ef7880c0ca212b32929e](https://raw.githubusercontent.com/python/cpython-source-deps/ef547e549b49a2822214ef7880c0ca212b32929e/sqlite3.h) | `a4073095982a84421da1a1e49bd26e97ba1a09c2de5dda5eac776cd4a420d41a` |
| `licenses/python-external/Microsoft-CRT.txt` | [4061bc4c35f7c26f25264666d4ba083b93d2f6f9](https://raw.githubusercontent.com/python/cpython/4061bc4c35f7c26f25264666d4ba083b93d2f6f9/PC/crtlicense.txt) | `3c71b3ae243121f6f227374cd1ef7c59ed07b1969b330d0e947f91a3a1b3fd73` |

For excerpt/assembled header files, hashes identify the included file. The manifest describes extraction, and each header block links to its original source. SQLite's source copyright disclaimer is a verbatim lines1–11 excerpt from the pinned sqlite3.h; it is not a newly authored license. Whole-source hashes and fetched build evidence are retained in the local remediation evidence directory.

## Microsoft and OpenSSL

OpenSSL3.0.21: complete, non-truncated trees were checked for `openssl/openssl` commit `51ea949dc1436e865935b47874b21a3bb31a102e`, CPython source-deps `460451a0bb19cdbf0ab1add4de1420d143995467`, and binary-deps `4c7747da0d1addd20c95c2f911f8d2e09254a3d2`. None has a NOTICE path. Authentic Apache-2.0 LICENSE and AUTHORS are included; AUTHORS is supplemental attribution, not falsely presented as a mandatory NOTICE. The extra condition about reproducing an upstream NOTICE has no such file in these pinned inputs. No pre-3.0 OpenSSL license was substituted.

Microsoft: CPython's pinned `PC/crtlicense.txt` is included verbatim. It requires downstream distributors/users to agree to terms protecting Microsoft Distributable Code. Notice preservation alone does not establish that agreement. The official Python CRT DLL resources report14.51.36247.0; the local SDK MSVC toolset is14.44.35207. These are separate provenance/entitlement cases. `/MT` uses a static runtime, so an absence of CRT DLL imports does not remove Microsoft conditions.

The inspected [Build Tools terms](https://visualstudio.microsoft.com/license-terms/vs2022-ga-diagnosticbuildtools/) (EULAID `VS_2022_Tools_2024Mar_ENU.1033`) require a qualifying Visual Studio Product license except the narrower third-party open-source dependency use described there. The fact this SDK is MIT does not establish eligibility for that exception. The [Microsoft /MT documentation](https://learn.microsoft.com/en-us/cpp/build/reference/md-mt-ld-use-run-time-library?view=msvc-170) and [2022 redistribution list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution) support the static-runtime distinction; Python's14.51 components require checking their corresponding [newer distribution terms](https://learn.microsoft.com/en-us/visualstudio/releases/2026/redistribution), not assuming the older list alone settles them.

Smallest remaining action: the owner/compliance reviewer establishes the applicable toolchain entitlement and appropriate downstream protective-terms agreement mechanism before public redistribution. Exact historical native build derivation remains the earlier audit's separate limitation. No license restriction is being added to MIT first-party code by this report, and no unsupported entitlement claim is made.

## Packaging implementation and tests

`scripts/license_manifest.py` validates the reviewed runtime URL/version/archive digest, exact34-member file set and hashes, component version versus `reviewed_version`, required notice paths, nonempty authentic notice files, safe paths and hashes. It rejects symlinks/junctions and unknown extra files in reviewed directories. `scripts/package_release_candidate.py` validates before staging, automatically copies the licensing hierarchy, and validates the final ZIP against the reviewed pre-build manifest. An embedded manifest cannot silently authorize a different notice after staging. `.gitattributes` preserves the notice bytes across Windows checkouts.

The ten dedicated tests cover missing/empty/modified notices, runtime upgrades/extra files, version-only dependency drift, required notice references, path traversal, omitted/modified final-ZIP notices, changed embedded manifests, and actual package inclusion. Review status remains explicit: passing integrity validation does not imply every status is resolved.

Final regression: **1,017 tests passed**, including ten licensing tests and three existing mod packaging tests. Invocation: `python -m unittest discover -s tests -q`, with PYTHONPATH containing `src` and `scripts`, TEMP/TMP in the writable D: test directory, and localhost socket access for controller tests. An initial restricted run failed because localhost sockets were denied; the final permitted run passed. An earlier invocation omitted `scripts` from PYTHONPATH; it was corrected without changing functionality.

## Actual candidate verification

Candidate is based on RC4 commit `1fc1ea2babc3d173c9d732bc641a9a23b5a1c744`, not the unrelated dirty viewer work. The isolated candidate source uses published RC4 source/runtime/native payloads plus the licensing build overlay. Native binaries were **reused, not rebuilt**. This intentionally tests a licensing-only repack and does not claim reproducible native builds.

- Official runtime:34/34 files byte-identical, including original LICENSE.txt; no new runtime DLL/package dependency.
- SDK source/scripts:115/115 byte-identical to public RC4;108 Python modules parsed successfully in the clean embedded runtime.
- Five native payload files: byte-identical to RC4 and correctly referenced by regenerated manifest hashes.
- Bundled SDKManagement and IntrospectionHarness archives: byte-identical to RC4; nested archive hashes/format verified by the installed controller's `--check`.
- Root MIT/license bytes unchanged; protected native/src/mods/runtime working-tree baseline unchanged.
- ZIP adds only21 `SDK/licenses/` files (19 upstream texts, README and manifest). Existing changes are THIRD_PARTY_NOTICES, regenerated release-manifest, and README line endings only. No files removed.
- Clean extraction to `D:/HobbyDevelopment/SDKLicenseRemediation/clean-install`: embedded `python.exe -I -S -B SDK/scripts/run_release_sdk.py --check` returned verified true with2mods.
- Actual clean runtime imports SSL, SQLite, zlib, Expat, decimal, Unicode, bz2, lzma, ctypes, asyncio and random successfully and reports the expected pinned versions.
- **No live-game test was performed.** Native hooks/game behavior were not exercised anew; byte equality and regression tests establish the limited preservation evidence, not fresh gameplay validation.

Artifact: `D:/HobbyDevelopment/ClairObscurSDK/dist/installable-rc4-license1/Expedition33-SDK-0.1.0-rc4-license1.zip`

SHA256: `eeb481c8a29f6e7c68231a1331b543a1540cf324a93327aa069782902a514a67`

Size:13,593,222bytes. Build summary is `dist/installable-rc4-license1/artifact.json`. Structured verification is [runtime-license-verification.json](runtime-license-verification.json). Reproduction/evidence scripts, pinned downloads, full test log and isolated source are retained under `D:/HobbyDevelopment/SDKLicenseRemediation/`; no source/runtime from the installed game was replaced.

## Exact repository additions/modifications

- `.gitattributes`
- `THIRD_PARTY_NOTICES.md`
- `scripts/license_manifest.py`
- `scripts/package_release_candidate.py`
- `tests/test_license_manifest.py`
- `licenses/python-external/bzip2-LICENSE.txt`
- `licenses/python-external/CPython-LICENSE.txt`
- `licenses/python-external/libffi-LICENSE.txt`
- `licenses/python-external/Microsoft-CRT.txt`
- `licenses/python-external/OpenSSL-AUTHORS.md`
- `licenses/python-external/OpenSSL-LICENSE.txt`
- `licenses/python-external/SQLite-NOTICE.txt`
- `licenses/python-external/XZ-COPYING.txt`
- `licenses/python-incorporated/BLAKE2-source-notices.txt`
- `licenses/python-incorporated/CC0-1.0.txt`
- `licenses/python-incorporated/CPython-3.13.15-license.rst`
- `licenses/python-incorporated/Expat-2.8.2-COPYING.txt`
- `licenses/python-incorporated/HACL-dist-LICENSE.txt`
- `licenses/python-incorporated/HACL-KaRaMeL-Apache-2.0.txt`
- `licenses/python-incorporated/HACL-KaRaMeL-source-notices.txt`
- `licenses/python-incorporated/mimalloc-2.1.2-LICENSE.txt`
- `licenses/python-incorporated/mimalloc-vendored-copyright-headers.txt`
- `licenses/python-incorporated/mpdecimal-4.0.0-COPYRIGHT.txt`
- `licenses/python-incorporated/zlib-1.3.1-LICENSE.txt`
- `licenses/README.md`
- `licenses/runtime-dependencies.json`
- `docs/audits/code-provenance.md`
- `docs/audits/license-inventory.md`
- `docs/audits/source-similarity.md`
- `docs/audits/release-compliance.md`
- `docs/audits/runtime-license-remediation.md`
- `docs/audits/runtime-license-verification.json`

The existing four audit reports receive dated addenda, preserving RC4 findings. Root LICENSE, Introspection Harness, native reflection and SDK functionality remain unchanged. No tag, commit, push or publication was performed.
