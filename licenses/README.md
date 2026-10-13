# Redistributed runtime licensing

This directory supplements the unchanged official `runtime/LICENSE.txt`.
ClairObscurSDK's first-party code remains MIT licensed. The whole binary
distribution is not licensed solely under MIT.

`runtime-dependencies.json` records the reviewed CPython 3.13.15 Windows AMD64
embedded archive, all 34 original member hashes, exact upstream source references,
component applicability, notice paths and hashes, and unresolved questions.
Authentic notice text is stored under `python-incorporated/` and `python-external/`.
The complete pinned CPython incorporated-software document is included as an
upstream reference; its mention of a component does not by itself establish that
the component is in this Windows runtime. Component records distinguish applicable
libraries from absent platforms, test packages and development-only tools.

Preserved notices include their actual copyright holders and grants. The manifest
is review metadata, not a replacement license or legal clearance. In particular,
Microsoft runtime entitlement and downstream redistribution conditions require
separate review; including Microsoft's notice does not establish agreement to
those terms. The SDK's `/MT` linkage and Python's separately bundled Visual C++
runtime DLLs are distinct cases.

## Updating and packaging

1. Keep the official runtime archive/version unchanged unless deliberately updating
   it. For any update, verify the upstream source/build configuration and actual
   shipped modules before changing the reviewed manifest.
2. Retrieve applicable notices from the pinned authoritative sources, preserving
   the text and recording source revisions, URLs and SHA-256 hashes. Resolve or
   explicitly retain applicability questions. Do not mark a review resolved merely
   because a file was added.
3. Update the component records, runtime member hashes and notice inventory only
   after that review. `notices` covers every file under `licenses/` except the
   manifest itself, including this guide. `.gitattributes` preserves notice bytes
   across Windows checkouts; do not normalize the authentic texts.
4. Run `scripts/package_release_candidate.py DESTINATION --version VERSION`.
   It validates the reviewed input before staging, copies this directory to
   `SDK/licenses/`, and re-opens the final ZIP to verify its actual contents.
   Missing, empty, changed or omitted notices and unreviewed runtime changes fail
   packaging. Unresolved review statuses remain visible; a successful integrity
   check is not a declaration of complete legal compliance.
5. Run the packaging regression tests and the installed launcher's `--check` in a
   fresh extraction. Review the generated hashes and component statuses before
   approving publication.

The historical RC4 audit and the subsequent remediation evidence are documented
in `docs/audits/` in the source repository. The licensing candidate is local only;
publication requires separate approval.
