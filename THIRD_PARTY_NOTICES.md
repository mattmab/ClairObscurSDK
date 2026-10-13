# Third-party notices

ClairObscurSDK's first-party SDK and included mod source are MIT licensed; see LICENSE.
The Introspection Harness retains its existing MIT notice in
src/expedition33/introspection/LICENSE.

The installable SDK redistributes the unmodified official CPython 3.13.15 Windows
embedded runtime. Its original `runtime/LICENSE.txt` is preserved byte-for-byte.
Python is covered by the PSF license, historical grants, and the separate terms
of incorporated software. The original runtime license file is not asserted to
be an exhaustive inventory of all incorporated notices.

Supplemental authentic notices are included under `licenses/python-incorporated/`
and `licenses/python-external/`. `licenses/runtime-dependencies.json` records the
reviewed runtime hashes, dependency versions, notice hashes, upstream references,
applicability evidence, and unresolved questions. These paths are relative to the
SDK directory in the installation. See `licenses/README.md` for the review scope.

Microsoft runtime components have separate redistribution terms. Their notices
and applicable review evidence are recorded separately from PSF and MIT grants.
The SDK's static Microsoft runtime linkage does not make that runtime MIT-licensed.
Likewise, OpenSSL and other incorporated libraries retain their own licenses.
Including a notice is not a statement that every redistribution entitlement or
uncertain component applicability has been conclusively established.

Development-only tools and reference projects are not included in the embedded
runtime merely because they were used during development. The manifest distinguishes
distributed components from development-only or inapplicable components.

The root MIT license does not replace any of these third-party terms and does not
describe the entire binary distribution. No third-party code is relicensed here.

Unreal Engine, Expedition 33, and their game assets are not licensed by this
project. No game assets or third-party mod DLLs are distributed here.
