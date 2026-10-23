@echo off
setlocal
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
where cl >nul 2>nul
if errorlevel 1 exit /b 1

if not exist "%PROJECT_ROOT%\build\arena-approach-v202" mkdir "%PROJECT_ROOT%\build\arena-approach-v202"
pushd "%PROJECT_ROOT%\build\arena-approach-v202"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:retired_owned_actor_fixture.exe "%PROJECT_ROOT%\native\retired_owned_actor_fixture.cpp"
if errorlevel 1 exit /b 1
retired_owned_actor_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:arena_approach_fixture.exe "%PROJECT_ROOT%\native\arena_approach_fixture.cpp"
if errorlevel 1 exit /b 1
arena_approach_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:owned_battle_arena_fixture.exe "%PROJECT_ROOT%\native\owned_battle_arena_fixture.cpp"
if errorlevel 1 exit /b 1
owned_battle_arena_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:owned_arena_value_fixture.exe "%PROJECT_ROOT%\native\owned_arena_value_fixture.cpp"
if errorlevel 1 exit /b 1
owned_arena_value_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:helper_entry_lifetime_fixture.exe "%PROJECT_ROOT%\native\helper_entry_lifetime_fixture.cpp"
if errorlevel 1 exit /b 1
helper_entry_lifetime_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:encounter_tuning_fixture.exe "%PROJECT_ROOT%\native\encounter_tuning_fixture.cpp"
if errorlevel 1 exit /b 1
encounter_tuning_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:blueprint_route_ownership_fixture.exe "%PROJECT_ROOT%\native\blueprint_route_ownership_fixture.cpp"
if errorlevel 1 exit /b 1
blueprint_route_ownership_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:blueprint_observation_fixture.exe "%PROJECT_ROOT%\native\blueprint_observation_fixture.cpp"
if errorlevel 1 exit /b 1
blueprint_observation_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:trace_slots_fixture.exe "%PROJECT_ROOT%\native\trace_slots_fixture.cpp"
if errorlevel 1 exit /b 1
trace_slots_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:trace_registry_fixture.exe "%PROJECT_ROOT%\native\trace_registry_fixture.cpp"
if errorlevel 1 exit /b 1
trace_registry_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:blueprint_trace_fixture.exe "%PROJECT_ROOT%\native\blueprint_trace_fixture.cpp"
if errorlevel 1 exit /b 1
blueprint_trace_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:enemy_arena_binding_fixture.exe "%PROJECT_ROOT%\native\enemy_arena_binding_fixture.cpp"
if errorlevel 1 exit /b 1
enemy_arena_binding_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:owned_arena_slots_fixture.exe "%PROJECT_ROOT%\native\owned_arena_slots_fixture.cpp"
if errorlevel 1 exit /b 1
owned_arena_slots_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:owned_actor_construction_fixture.exe "%PROJECT_ROOT%\native\owned_actor_construction_fixture.cpp"
if errorlevel 1 exit /b 1
owned_actor_construction_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:helper_component_pose_fixture.exe "%PROJECT_ROOT%\native\helper_component_pose_fixture.cpp"
if errorlevel 1 exit /b 1
helper_component_pose_fixture.exe
if errorlevel 1 exit /b 1
popd

if "%~1"=="fixtures" exit /b 0

where cl >nul 2>nul
if errorlevel 1 (
  echo Run from an x64 Native Tools Command Prompt for Visual Studio.
  exit /b 1
)
if not exist "%PROJECT_ROOT%\build\release\runtime-session-cinematic-v202" mkdir "%PROJECT_ROOT%\build\release\runtime-session-cinematic-v202"
if not exist "%PROJECT_ROOT%\build\release\research-probe-cinematic-v202-extra-spots" mkdir "%PROJECT_ROOT%\build\release\research-probe-cinematic-v202-extra-spots"
pushd "%PROJECT_ROOT%\build\release\runtime-session-cinematic-v202"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /DE33_RUNTIME_CINEMATIC_VERSION=202 /DE33_NPC_PRESENTATION_RESEARCH /DE33_ENEMY_VISUAL_RESEARCH /DE33_BATTLE_PARAMETER_FRAME_RESEARCH /DE33_RUNTIME_CINEMATIC_SESSION /DE33_RUNTIME_SCENE_EDITOR_SESSION /DE33_ENEMY_SPAWN_SESSION /DE33_ZONE_TRAVEL_SESSION /DE33_BUILDER_SELECTION_SESSION /DE33_UI_CONSTRUCTION_SESSION /DE33_KEY_CAPTURE_SESSION /DE33_MESH_SESSION /DE33_SCALAR_ASSIGNMENT_SESSION /DE33_VIEWER_MENU_SESSION /DE33_CATALOG_GAME_OWNED_SESSION /DE33_GAME_OWNED_AUDIO_SESSION /DE33_GAME_OWNED_CINEMATIC_SESSION /DE33_SPAWN_MEMBERSHIP_SESSION /DE33_EMPTY_BINDING_OVERRIDE_SESSION /DE33_SEQUENCE_BINDING_QUERY_SESSION /DE33_SEQUENCE_CAMERA_SESSION /DE33_SOUND_EVENT_DIAGNOSTICS_SESSION /DE33_EXTENDED_OWNED_AUDIO_SESSION /DE33_TIMESPAN_SESSION /DE33_EMPTY_TITLE_SESSION /DE33_COVERAGE_SESSION /DE33_FRAME_TIME_SESSION /DE33_TITLE_MENU_SESSION /DE33_AUDIO_COMPLETION_SESSION /DE33_AUDIO_IDENTITY_SESSION /DE33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION /DE33_WIDGET_ANIMATION_SESSION /DE33_WIDGET_DIAGNOSTICS_SESSION /DE33_GROWING_LEASE_SESSION /DE33_CINEMATIC_WIDGET_SESSION /DE33_ORIGINAL_AUDIO_PAUSE_SESSION /DE33_CINEMATIC_SOUND_EVENT_SESSION /DE33_OWNED_SOUND_SESSION /DE33_MUSIC_AUDIO_GUARD_SESSION /DE33_MUSIC_AUDIO_SESSION /DE33_AUDIO_ISOLATION_SESSION /DE33_SEQUENCE_PLAYER_SESSION /DE33_SEQUENCE_SESSION /DE33_MEDIA_SESSION /DE33_STRING_SESSION /DE33_MENU_ESCAPE_SESSION /DE33_MENU_DIAGNOSTIC_SESSION /DE33_BLUEPRINT_DIRECT_SESSION /DE33_BLUEPRINT_TRACE_SESSION /DE33_LAYOUT_BATCH_SESSION /DE33_PAUSE_MENU_SESSION /DE33_VECTOR_SESSION /DE33_UI_BATCH_SESSION /DE33_KEYBIND_SESSION /DE33_TRACE_SESSION /DE33_MULTI_BUTTON_SESSION /DE33_BUTTON_ACTION_SESSION /DE33_BUTTON_REFERENCE_SESSION /DE33_MENU_SESSION /DE33_ENUM_SESSION /DE33_TEXT_SESSION /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /LD /Fe:runtime_session_cinematic_v202.dll /Fd:runtime_session_cinematic_v202.pdb "%PROJECT_ROOT%\native\runtime_session.cpp" /link /DEBUG user32.lib d3d12.lib dxgi.lib
set "BUILD_RESULT=%errorlevel%"
popd
if not "%BUILD_RESULT%"=="0" exit /b %BUILD_RESULT%
pushd "%PROJECT_ROOT%\build\release\research-probe-cinematic-v202-extra-spots"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /DE33_RUNTIME_CINEMATIC_VERSION=202 /DE33_NPC_PRESENTATION_RESEARCH /DE33_ENEMY_VISUAL_RESEARCH /DE33_BATTLE_PARAMETER_FRAME_RESEARCH /DE33_RUNTIME_CINEMATIC_SESSION /DE33_RUNTIME_SCENE_EDITOR_SESSION /DE33_ENEMY_SPAWN_SESSION /DE33_ZONE_TRAVEL_SESSION /DE33_BUILDER_SELECTION_SESSION /DE33_UI_CONSTRUCTION_SESSION /DE33_KEY_CAPTURE_SESSION /DE33_MESH_SESSION /DE33_SCALAR_ASSIGNMENT_SESSION /DE33_VIEWER_MENU_SESSION /DE33_CATALOG_GAME_OWNED_SESSION /DE33_GAME_OWNED_AUDIO_SESSION /DE33_GAME_OWNED_CINEMATIC_SESSION /DE33_SPAWN_MEMBERSHIP_SESSION /DE33_EMPTY_BINDING_OVERRIDE_SESSION /DE33_SEQUENCE_BINDING_QUERY_SESSION /DE33_SEQUENCE_CAMERA_SESSION /DE33_SOUND_EVENT_DIAGNOSTICS_SESSION /DE33_EXTENDED_OWNED_AUDIO_SESSION /DE33_TIMESPAN_SESSION /DE33_EMPTY_TITLE_SESSION /DE33_COVERAGE_SESSION /DE33_FRAME_TIME_SESSION /DE33_TITLE_MENU_SESSION /DE33_AUDIO_COMPLETION_SESSION /DE33_AUDIO_IDENTITY_SESSION /DE33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION /DE33_WIDGET_ANIMATION_SESSION /DE33_WIDGET_DIAGNOSTICS_SESSION /DE33_GROWING_LEASE_SESSION /DE33_CINEMATIC_WIDGET_SESSION /DE33_ORIGINAL_AUDIO_PAUSE_SESSION /DE33_CINEMATIC_SOUND_EVENT_SESSION /DE33_OWNED_SOUND_SESSION /DE33_MUSIC_AUDIO_GUARD_SESSION /DE33_MUSIC_AUDIO_SESSION /DE33_AUDIO_ISOLATION_SESSION /DE33_SEQUENCE_PLAYER_SESSION /DE33_SEQUENCE_SESSION /DE33_MEDIA_SESSION /DE33_STRING_SESSION /DE33_MENU_ESCAPE_SESSION /DE33_MENU_DIAGNOSTIC_SESSION /DE33_BLUEPRINT_DIRECT_SESSION /DE33_BLUEPRINT_TRACE_SESSION /DE33_LAYOUT_BATCH_SESSION /DE33_PAUSE_MENU_SESSION /DE33_VECTOR_SESSION /DE33_UI_BATCH_SESSION /DE33_KEYBIND_SESSION /DE33_TRACE_SESSION /DE33_MULTI_BUTTON_SESSION /DE33_BUTTON_ACTION_SESSION /DE33_BUTTON_REFERENCE_SESSION /DE33_MENU_SESSION /DE33_ENUM_SESSION /DE33_TEXT_SESSION /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /Fe:research_probe.exe /Fd:research_probe.pdb "%PROJECT_ROOT%\native\research_probe.cpp" /link /DEBUG bcrypt.lib user32.lib d3d12.lib dxgi.lib
set "BUILD_RESULT=%errorlevel%"
popd
if not "%BUILD_RESULT%"=="0" exit /b %BUILD_RESULT%
exit /b %BUILD_RESULT%
