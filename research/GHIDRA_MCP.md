# GHIDRA_MCP

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Fixture persistence was proven and game runtime findings were obtained. Backend recovered after a 16 GB heap exhaustion; whole-image analysis restarted with 32 GB. See the dated recovery entries below and the runtime journals for already-proven layouts.

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

## 2026-10-08 native build validation

PROVEN: Visual Studio Build Tools installer completed with exit code 0. Repository fixture native/fixtures/mcp_smoke.c compiled using MSVC 14.44.35207, x64 vcvarsall environment, and installed Windows SDK; build/mcp-smoke/mcp_smoke.exe executed and printed `Expedition 33 research fixture: 42`, exit 0. Earlier missing stdio.h result is superseded: SDK installation had not finished at that time.

PROVEN: Existing Ghidra source dependency-fetch task completed successfully (Gradle 9.8.0, Java 25), exit 0. Distribution compilation is running; this does not yet prove a launchable Ghidra or operational backend.

OBSERVED: Computer Use window enumeration now succeeds after the earlier Escape interruption. No further intervention requested.

STALE/DISPROVEN build environment: first distribution build exited 1 after 273 tasks because native toolchain discovery ran before Windows SDK installation completed; it retained `!WindowsSdkDir!` and an empty SDK version. The independently reproduced C++ fixture succeeds after installer exit 0. Retrying distribution with --no-daemon to force fresh native SDK discovery; preserving first failure in evidence/ghidra-build.log and retry in evidence/ghidra-build-sdk-ready.log.

PROVEN retry progress: fresh Gradle discovery reports C:/Program Files (x86)/Windows Kits/10 and SDK 10.0.26100.0; native decompiler compilation and linking completed. Initial missing-SDK build failure was transient installation timing, not an unresolved compiler incompatibility.

OBSERVED launcher detail: Ghidra LaunchSupport AppConfig reads application.settingsdir from support/launch.properties when saving its JDK selection. Passing the property only as a caller JVM argument would redirect the main application but not this earlier step. scripts/configure-ghidra.ps1 applies the D: directories to the built distribution's launch.properties before its first launch. It is prepared, not yet executed against a finished distribution.

PROVEN: Existing source built successfully with 719 Gradle tasks on the SDK-ready retry. Archive build/dist/ghidra_12.3_DEV_20261008.zip extracted under the same source tree at build/local-install/ghidra_12.3_DEV. Ghidra GUI launched, startup completed, and Computer Use installed the GhidraMCP 7.0.0 ZIP stamped 12.3.

Compatibility experiment: unmodified extension failed compilation at three DataTypeManager.remove(DataType, null) calls. Ghidra 12.3 DataTypeManager.java exposes boolean remove(DataType), with the monitored overload now taking a list. Adapted the three calls to the singleton overload; buildExtension succeeded. Reproducible patch: patches/ghidra-mcp-7.0.0-ghidra12.3.patch, against reference commit 9cc29c0f1efb6c63a7d6898c9a23aff39397f992. Java 25 override remains in scripts/ghidra-mcp-java25.init.gradle. This is local tooling compatibility, not any target-game discovery.

OBSERVED persistent locations: extension under D:/HobbyDevelopment/Analysis/ClairObscurSDK/settings/Matt-ghidra/ghidra_12.3_DEV/Extensions/GhidraMCP; LaunchSupport java_home.save under settings/ghidra/ghidra_12.3_DEV. Both satisfy D: placement. Plugin enabling and live MCP tests remain pending.

## Stage 2 proven: actual MCP fixture experiment

PROVEN 2026-10-08: local GUI backend responds as GhidraMCP 7.0.0 at http://127.0.0.1:8089; the Python MCP stdio client discovers 212 tools with backend attached. GUI confirms GhidraMCPPlugin enabled in the project window. Non-shared project: D:/HobbyDevelopment/Analysis/ClairObscurSDK/Expedition33-23765773.gpr.

MCP imported build/mcp-smoke/mcp_smoke.exe into /fixtures, auto-analyzed it, and returned x86:LE:64:default / Windows compiler / preferred base 0x140000000 / 5988 functions. find_functions enumerated a bounded page (its total 5896 excludes external functions; metadata counts 5988). get_functions returned research_add at 0x140007280 with signature int research_add(int,int) and decompilation returning param_1 + param_2, independently agreeing with our C source.

set_comment wrote a unique plate annotation at 0x140007280. save_program succeeded; close_program returned closed_count 1 and released_cache true; open_program reopened /fixtures/mcp_smoke.exe without reanalysis. get_comment returned the exact annotation. This proves metadata, enumeration, decompilation, write and database persistence through the actual MCP path.

Evidence files under evidence/: mcp-connected-tools.json, mcp-import-fixture-result.json, mcp-fixture-metadata.json, mcp-fixture-functions.json, mcp-fixture-decompile.json, mcp-fixture-comment-written.json, mcp-fixture-saved.json, mcp-fixture-closed.json, mcp-fixture-reopened.json, mcp-fixture-persisted-comment.json. Corresponding argument JSON and scripts/ghidra_mcp_client.py reproduce each request. Game layouts remain unvalidated; this proves the research instrument only.

## 2026-10-08 heap exhaustion and recovery

OBSERVED: application.log at 15:18:56-15:19:01 reports Java heap space OutOfMemoryError and Auto Analysis command failure, maximum heap 17,179,869,184 bytes. Whole-image analysis did not complete. A stale progress indicator is not evidence that it is still progressing. GUI normal cancellation was attempted; analysis then remained waiting for a database write lock in ProgramRegisterContextDB.flushProcessorContextWriteCache during endTransaction. A later GUI Save attempt did not complete; the EDT also waits on that lock. The exact source of the retained lock is not proven.

Preservation: copied the .gpr/.rep into D:/HobbyDevelopment/Analysis/ClairObscurSDK/recovery-20261008-oom while the process remained open. This diagnostic copy is not claimed transaction-consistent. jcmd 21416 GC.heap_dump -all -gz=1 completed successfully in 77.721 seconds, producing ghidra21416.hprof.gz (9,024,382,398 bytes). The heap snapshot is diagnostic evidence, not a directly reopenable Ghidra project. Log and thread dumps: evidence/ghidra-oom-20261008.log, ghidra-oom-threads.txt, ghidra-after-save-threads.txt.

User approval requested before terminating the stuck process, because unsaved analysis may need rerunning. No termination performed as of this entry. scripts/launch-ghidra.ps1 is prepared for a 32 GB heap and rejects a duplicate running Ghidra instance; its actual launch/recovery remains untested. Machine has approximately 64 GB RAM. Runtime enumeration, reflected invocation and their evidence remain independent of this analysis failure.

## Recovery completed; analysis restarted

PROVEN: user manually stopped the old Ghidra and explicitly requested restart. scripts/launch-ghidra.ps1 launched new JVM PID37224; jcmd VM.flags reports MaxHeapSize=34359738368. Existing project reopened through Computer Use. CodeBrowser prompted for its installed MCP plugin; enabled it and saved the tool configuration through File > Save Tool.

MCP get_metadata succeeded: shipping program retained 288,587 functions and 290,527 symbols. This is fewer than the last pre-failure count; the unsaved analysis did not all survive. Replayed the preserved registry/name/dispatcher annotations and recreated runtime-validated getter boundaries at 14333be80 (31 bytes) and 143339a70 (32 bytes). save_program returned saved=true after both batches. Evidence: mcp-recovered-shipping-metadata.json, recovery-annotate-*.json, recovery-anchors-saved.json, recovery-*-thunk.json and recovery-thunks-saved.json under evidence/.

Computer Use reviewed standard x64 analysis defaults (Decompiler Parameter ID and aggressive instruction finder off), then clicked Analyze. MCP analysis_status reported analyzing=true and 290,732 functions in recovery-analysis-started.json. Its analyzed=true flag alone is not completion evidence while analyzing=true. Full analysis still needs completion and a verified save.

