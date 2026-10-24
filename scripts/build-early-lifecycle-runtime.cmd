@echo off
setlocal
rem Run from an x64 Native Tools command prompt. No installation is performed.
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
where cl >nul 2>nul
if errorlevel 1 (
  echo MSVC cl.exe is required. Use an x64 Native Tools command prompt.
  exit /b 1
)
set "NATIVE_FLAGS=/DE33_MAP_LOAD_GATE_SESSION /DE33_RETIRED_WORLD_SESSION /DE33_MENU_OPEN_FOCUS_SESSION /DE33_METADATA_STABILIZE_SESSION /DE33_CONSOLE_COLORS_SESSION /DE33_LEASE_RELEASE_BATCH_SESSION /DE33_RUNTIME_CINEMATIC_VERSION=211 /DE33_NPC_PRESENTATION_RESEARCH /DE33_ENEMY_VISUAL_RESEARCH /DE33_BATTLE_PARAMETER_FRAME_RESEARCH /DE33_RUNTIME_CINEMATIC_SESSION /DE33_RUNTIME_SCENE_EDITOR_SESSION /DE33_ENEMY_SPAWN_SESSION /DE33_ZONE_TRAVEL_SESSION /DE33_BUILDER_SELECTION_SESSION /DE33_UI_CONSTRUCTION_SESSION /DE33_KEY_CAPTURE_SESSION /DE33_MESH_SESSION /DE33_SCALAR_ASSIGNMENT_SESSION /DE33_VIEWER_MENU_SESSION /DE33_CATALOG_GAME_OWNED_SESSION /DE33_GAME_OWNED_AUDIO_SESSION /DE33_GAME_OWNED_CINEMATIC_SESSION /DE33_SPAWN_MEMBERSHIP_SESSION /DE33_EMPTY_BINDING_OVERRIDE_SESSION /DE33_SEQUENCE_BINDING_QUERY_SESSION /DE33_SEQUENCE_CAMERA_SESSION /DE33_SOUND_EVENT_DIAGNOSTICS_SESSION /DE33_EXTENDED_OWNED_AUDIO_SESSION /DE33_TIMESPAN_SESSION /DE33_EMPTY_TITLE_SESSION /DE33_COVERAGE_SESSION /DE33_FRAME_TIME_SESSION /DE33_TITLE_MENU_SESSION /DE33_AUDIO_COMPLETION_SESSION /DE33_AUDIO_IDENTITY_SESSION /DE33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION /DE33_WIDGET_ANIMATION_SESSION /DE33_WIDGET_DIAGNOSTICS_SESSION /DE33_GROWING_LEASE_SESSION /DE33_CINEMATIC_WIDGET_SESSION /DE33_ORIGINAL_AUDIO_PAUSE_SESSION /DE33_CINEMATIC_SOUND_EVENT_SESSION /DE33_OWNED_SOUND_SESSION /DE33_MUSIC_AUDIO_GUARD_SESSION /DE33_MUSIC_AUDIO_SESSION /DE33_AUDIO_ISOLATION_SESSION /DE33_SEQUENCE_PLAYER_SESSION /DE33_SEQUENCE_SESSION /DE33_MEDIA_SESSION /DE33_STRING_SESSION /DE33_MENU_ESCAPE_SESSION /DE33_MENU_DIAGNOSTIC_SESSION /DE33_BLUEPRINT_DIRECT_SESSION /DE33_BLUEPRINT_TRACE_SESSION /DE33_LAYOUT_BATCH_SESSION /DE33_PAUSE_MENU_SESSION /DE33_VECTOR_SESSION /DE33_UI_BATCH_SESSION /DE33_KEYBIND_SESSION /DE33_TRACE_SESSION /DE33_MULTI_BUTTON_SESSION /DE33_BUTTON_ACTION_SESSION /DE33_BUTTON_REFERENCE_SESSION /DE33_MENU_SESSION /DE33_ENUM_SESSION /DE33_TEXT_SESSION /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION"
for %%D in ("lease-release-batch-v211" "runtime-session-cinematic-v211" "research-probe-cinematic-v211-lease-batch") do (
  if not exist "%PROJECT_ROOT%\build\release\%%~D" mkdir "%PROJECT_ROOT%\build\release\%%~D"
  if errorlevel 1 exit /b 1
)
pushd "%PROJECT_ROOT%\build\release\lease-release-batch-v211"
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:lease_release_batch_fixture.exe "%PROJECT_ROOT%\native\lease_release_batch_fixture.cpp"
if errorlevel 1 goto :failed
lease_release_batch_fixture.exe
if errorlevel 1 goto :failed
for %%F in (builder_retirement retired_world menu_open_pipeline keybind stable_identity stable_lease menu_focus_controls metadata_stabilization console_colors_layout console_colors_adapter console_colors_callback console_spawn_resolution) do (
  cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /I"%PROJECT_ROOT%\native" /Fe:%%F_fixture.exe "%PROJECT_ROOT%\native\%%F_fixture.cpp"
  if errorlevel 1 goto :failed
  %%F_fixture.exe
  if errorlevel 1 goto :failed
)
popd
pushd "%PROJECT_ROOT%\build\release\runtime-session-cinematic-v211"
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi %NATIVE_FLAGS% /LD /Fe:runtime_session_cinematic_v211.dll /Fd:runtime_session_cinematic_v211.pdb "%PROJECT_ROOT%\native\runtime_session.cpp" /link /DEBUG user32.lib d3d12.lib dxgi.lib
if errorlevel 1 goto :failed
popd
pushd "%PROJECT_ROOT%\build\release\research-probe-cinematic-v211-lease-batch"
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi %NATIVE_FLAGS% /Fe:research_probe.exe /Fd:research_probe.pdb "%PROJECT_ROOT%\native\research_probe.cpp" /link /DEBUG bcrypt.lib user32.lib d3d12.lib dxgi.lib
if errorlevel 1 goto :failed
popd
echo Early lifecycle v211 native build and lease fixture passed.
exit /b 0
:failed
popd
exit /b 1
