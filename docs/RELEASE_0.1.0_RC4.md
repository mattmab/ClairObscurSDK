# SDK 0.1.0-rc4: optional mod distribution

The SDK ZIP now includes only SDKManagement and IntrospectionHarness. Optional
mods have independent release tags and `.sdkmod` downloads in the [Mods catalog](https://github.com/mattmab/ClairObscurSDK/blob/main/mods/README.md).
They are no longer automatically enabled on a fresh install. Existing installed
archives and saved enable choices remain intact on upgrade.

This release includes the current Picto frame-batch runtime, inventory reading,
saved override restoration and UI fixes. The latest restart test restored 51
mastery overrides in 1.18 seconds; baseline plus restoration took 2.99 seconds.
Full Picto enable including UI took 7.25 seconds, not two seconds.

Validation: native runtime/reader rebuilt with warnings as errors; 991 Python
tests passed; staged embedded-runtime integrity check passed with exactly two
bundled mods. Separate archives are hash-validated without executing their code.
The split package was checked offline; no new whole-game regression session was
performed for the distribution-only change.

This remains a build-specific prerelease. Statistics does not claim complete
third-party DLL parity. Cinematics coverage and Stop support remain scene-specific.
See research documents and mod READMEs for recorded evidence and limitations.

SDK and mod source are MIT licensed. Bundled Python retains its upstream license.
