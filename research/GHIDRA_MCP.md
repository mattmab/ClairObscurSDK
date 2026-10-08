# GHIDRA_MCP

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Not yet investigated. No Expedition 33 layouts, offsets, or runtime APIs are validated.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Environment experiment

OBSERVED: D:/HobbyDevelopment/Tools/ghidra-master is Ghidra 12.3 DEV source (Ghidra/application.properties), requiring Java 25 and Gradle >=9.1. No built launchable distribution is present at its root. Confirmed by filesystem and File Explorer accessibility inspection through Computer Use.

OBSERVED: Existing JDK C:/Program Files/Eclipse Adoptium/jdk-25.0.4.101-hotspot can be reused. No java on initial PATH. No CMake/compiler found yet. Ghidra source build is being attempted, respecting the request not to reinstall Ghidra.

OBSERVED: bethington/ghidra-mcp clone README targets Ghidra 12.1.4; compatibility with this 12.3 DEV source is not proven. Prefer Gradle build against actual Ghidra jars. Do not run default deploy blindly: README says it writes extensions/config to user profile, conflicting with D: rule. Redirect Ghidra user directories explicitly first.

OBSERVED: Sandbox git could not resolve github.com. Authorized escalated clone succeeded in progressing through all references. Network restriction is environmental, not a missing repository.

PENDING proof: harmless binary import; MCP metadata; function enumeration; decompile; annotation; re-query after save/reopen. Installation alone is not success.

## Toolchain setup progress

OBSERVED: No installed native C++ toolchain was found through PATH, standard install directories, or uninstall metadata. Downloaded Microsoft-signed Build Tools bootstrapper 17.14.37710.0 from https://aka.ms/vs/17/release/vs_buildtools.exe. Microsoft signature validated before launch.

Installation requested D:/HobbyDevelopment/Tools/VSBuildTools, shared D:/HobbyDevelopment/Tools/VSShared, cache D:/HobbyDevelopment/Caches/VisualStudio, with C++ tools, ATL and Windows SDK. UI confirmed active installation (not complete yet). Microsoft installer/elevated child nevertheless stages transient payloads/logs under LocalAppData/Temp and installs its controller under Program Files (x86). This is recorded as installer-managed C: usage; project environments, source, analysis and persistent package cache remain D:.

PROVEN: Isolated D:/HobbyDevelopment/Python/expedition33-tools environment installs/imports pefile and Ghidra MCP bridge 7.0.0. Exact packages in tooling-requirements.lock.txt. This is NOT proof of an operational MCP-to-Ghidra connection.

OBSERVED in Ghidra ApplicationUtilities.java: JVM system properties application.settingsdir, application.cachedir, application.tempdir can redirect user state to D:. Use these when launching.
