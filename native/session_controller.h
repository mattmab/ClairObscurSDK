#pragma once
#include "session_protocol.h"
#include "target_process_exit.h"
#include "session_wait.h"

inline void decode_console_payload(const std::string& encoded,wchar_t (&out)[32769]) {
    require(encoded.size()%4==0 && encoded.size()/4<=32768,"CONSOLE_PAYLOAD_SIZE");
    auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
        throw std::runtime_error("CONSOLE_PAYLOAD_ENCODING"); };
    for(size_t i=0;i<encoded.size()/4;++i) {
        unsigned low=digit(encoded[i*4])*16+digit(encoded[i*4+1]);
        unsigned high=digit(encoded[i*4+2])*16+digit(encoded[i*4+3]);
        out[i]=static_cast<wchar_t>(low+high*256); require(out[i]!=0,"CONSOLE_PAYLOAD_NUL");
    }
    out[encoded.size()/4]=0;
}
inline std::string console_utf8(const wchar_t* value) {
    size_t length=wcsnlen_s(value,32769); require(length<32769,"CONSOLE_RESPONSE_SIZE");
    if(!length) return {};
    int size=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,value,static_cast<int>(length),nullptr,0,nullptr,nullptr);
    require(size>0,"CONSOLE_RESPONSE_ENCODING"); std::string result(size,0);
    WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,value,static_cast<int>(length),result.data(),size,nullptr,nullptr);
    return result;
}

struct RuntimeSessionController {
    SessionWait completion_wait;
    HANDLE mapping = nullptr;
    HANDLE target_process = nullptr;
    SessionPacket* packet = nullptr;
    HMODULE module = nullptr;
    HHOOK bootstrap = nullptr;
    DWORD tid = 0, controller = GetCurrentProcessId();
    uint64_t nonce = 0;
    bool opened = false;
    ~RuntimeSessionController() {
        if (opened && packet && !InterlockedCompareExchange(&packet->closed, 0, 0) &&
            InterlockedCompareExchange(&packet->request.state, 0, 0) == kComplete) {
            try { command(SessionClose); } catch (...) { /* Target-owned watcher handles controller exit. */ }
        }
        if (bootstrap) UnhookWindowsHookEx(bootstrap);
        if (module) FreeLibrary(module);
        if (packet) UnmapViewOfFile(packet);
        if (mapping) CloseHandle(mapping);
        if (target_process) CloseHandle(target_process);
    }
    void command(DWORD action) {
        require_live_target(target_process);
        require(!InterlockedCompareExchange(&packet->closed, 0, 0), "SESSION_ALREADY_CLOSED");
        packet->request.action = action; packet->request.error = 0;
        InterlockedExchange(&packet->request.state, kRequested);
        UINT message = RegisterWindowMessageW(kSessionMessage);
        if (!message || !PostThreadMessageW(tid, message, nonce, controller)) {
            require_live_target(target_process);
            throw std::runtime_error("SESSION_POST_FAILED");
        }
        ULONGLONG start = GetTickCount64();
        while (InterlockedCompareExchange(&packet->request.state, 0, 0) != kComplete && GetTickCount64() - start < 5000) {
            require_live_target(target_process);
            completion_wait.wait();
        }
        require_live_target(target_process);
        require(InterlockedCompareExchange(&packet->request.state, 0, 0) == kComplete, "SESSION_COMMAND_TIMEOUT");
        require(packet->request.error == 0, "SESSION_BACKEND_ERROR=" + std::to_string(packet->request.error));
        require(!packet->closed || (action == SessionClose && packet->close_reason == ClosedNormally),
                "SESSION_CLOSED reason=" + std::to_string(packet->close_reason));
    }
};
inline void run_runtime_session(DWORD pid, DWORD thread, int32_t object_index, int32_t object_serial,
                                int32_t function_index, int32_t function_serial) {
    RuntimeSessionController connection; connection.tid = thread;
    connection.target_process = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    require(connection.target_process != nullptr, "SESSION_TARGET_HANDLE_FAILED");
    require(BCryptGenRandom(nullptr, reinterpret_cast<PUCHAR>(&connection.nonce), sizeof(connection.nonce), BCRYPT_USE_SYSTEM_PREFERRED_RNG) >= 0,
            "SESSION_RANDOM_FAILED");
    wchar_t name[96]; session_mapping_name(name, connection.controller, connection.nonce);
    connection.mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, sizeof(SessionPacket), name);
    require(connection.mapping && GetLastError() != ERROR_ALREADY_EXISTS, "SESSION_MAPPING_FAILED");
    connection.packet = static_cast<SessionPacket*>(MapViewOfFile(connection.mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SessionPacket)));
    require(connection.packet != nullptr, "SESSION_MAP_VIEW_FAILED");
    auto& packet = *connection.packet;
    packet.controller = connection.controller;
    packet.request.magic = kScheduleMagic; packet.request.version = 1; packet.request.nonce = connection.nonce;
    packet.request.target_pid = pid; packet.request.target_tid = thread;
    packet.request.object_index = object_index; packet.request.object_serial = object_serial;
    packet.request.function_index = function_index; packet.request.function_serial = function_serial;
    wchar_t executable[32768]; require(GetModuleFileNameW(nullptr, executable, 32768) != 0, "SESSION_SELF_PATH");
#ifdef E33_KEYBIND_SESSION
#if defined(E33_MESH_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-worldbuilder-v54-menu" / L"runtime_session_worldbuilder_v54_menu.dll";
#elif defined(E33_VIEWER_MENU_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-viewer-v2" / L"runtime_session_viewer_v2.dll";
#elif defined(E33_CATALOG_GAME_OWNED_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-picto-v4" / L"runtime_session_picto_v4.dll";
#elif defined(E33_GAME_OWNED_AUDIO_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v64-game-owned-audio" / L"runtime_session_v64_game_owned_audio.dll";
#elif defined(E33_GAME_OWNED_CINEMATIC_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v63-game-owned" / L"runtime_session_v63_game_owned.dll";
#elif defined(E33_SPAWN_MEMBERSHIP_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v62-membership" / L"runtime_session_v62_membership.dll";
#elif defined(E33_EMPTY_BINDING_OVERRIDE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v61-binding" / L"runtime_session_v61_binding.dll";
#elif defined(E33_SEQUENCE_BINDING_QUERY_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v60-binding" / L"runtime_session_v60_binding.dll";
#elif defined(E33_SEQUENCE_CAMERA_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v59-camera" / L"runtime_session_v59_camera.dll";
#elif defined(E33_COVERAGE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v58-media-audio" / L"runtime_session_v58_media_audio.dll";
#elif defined(E33_FRAME_TIME_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v54-frametime" / L"runtime_session_v54_frametime.dll";
#elif defined(E33_TITLE_MENU_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v53-titlemenu" / L"runtime_session_v53_titlemenu.dll";
#elif defined(E33_AUDIO_COMPLETION_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v52-audiocompletion" / L"runtime_session_v52_audiocompletion.dll";
#elif defined(E33_AUDIO_IDENTITY_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v51-audioidentity" / L"runtime_session_v51_audioidentity.dll";
#elif defined(E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v50-audiocleanupdiagnostics" / L"runtime_session_v50_audiocleanupdiagnostics.dll";
#elif defined(E33_WIDGET_ANIMATION_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v49-animationdrain" / L"runtime_session_v49_animationdrain.dll";
#elif defined(E33_WIDGET_DIAGNOSTICS_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v48-widgetdiagnostics" / L"runtime_session_v48_widgetdiagnostics.dll";
#elif defined(E33_NUMBERED_CALLBACK_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v47-numberedcallback" / L"runtime_session_v47_numberedcallback.dll";
#elif defined(E33_NUMBERED_WIDGET_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v46-numberedwidget" / L"runtime_session_v46_numberedwidget.dll";
#elif defined(E33_TRACK_DIAGNOSTIC_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v45-trackdiagnostic" / L"runtime_session_v45_trackdiagnostic.dll";
#elif defined(E33_GROWING_LEASE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v44-leasegrowth" / L"runtime_session_v44_leasegrowth.dll";
#elif defined(E33_WIDGET_CAPACITY_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v43-widgetcapacity" / L"runtime_session_v43_widgetcapacity.dll";
#elif defined(E33_CINEMATIC_WIDGET_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v42-widgetownership" / L"runtime_session_v42_widgetownership.dll";
#elif defined(E33_ORIGINAL_AUDIO_PAUSE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v41-originalaudiopause" / L"runtime_session_v41_originalaudiopause.dll";
#elif defined(E33_CINEMATIC_SOUND_EVENT_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-cinematicsoundevent" / L"runtime_session_v40_cinematicsoundevent.dll";
#elif defined(E33_OWNED_SOUND_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-ownedsound" / L"runtime_session_v40_ownedsound.dll";
#elif defined(E33_MUSIC_AUDIO_GUARD_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-musicaudioguard" / L"runtime_session_v40_musicaudioguard.dll";
#elif defined(E33_MUSIC_AUDIO_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-musicaudio" / L"runtime_session_v40_musicaudio.dll";
#elif defined(E33_AUDIO_ISOLATION_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-audioisolation" / L"runtime_session_v40_audioisolation.dll";
#elif defined(E33_SEQUENCE_PLAYER_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-sequenceplayer" / L"runtime_session_v40_sequenceplayer.dll";
#elif defined(E33_SEQUENCE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-sequence" / L"runtime_session_v40_sequence.dll";
#elif defined(E33_MEDIA_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-media" / L"runtime_session_v40_media.dll";
#elif defined(E33_STRING_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-string" / L"runtime_session_v40_string.dll";
#elif defined(E33_MENU_ESCAPE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-menuescape" / L"runtime_session_v40_menuescape.dll";
#elif defined(E33_MENU_DIAGNOSTIC_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v40-menudiag" / L"runtime_session_v40_menudiag.dll";
#elif defined(E33_BLUEPRINT_DIRECT_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v26-statistics" / L"runtime_session_v26_statistics.dll";
#elif defined(E33_BLUEPRINT_TRACE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v25-statistics" / L"runtime_session_v25_statistics.dll";
#elif defined(E33_LAYOUT_BATCH_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v24-layout" / L"runtime_session_v24_layout.dll";
#elif defined(E33_MULTI_PAUSE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v24-multi-pause" / L"runtime_session_v24_multi_pause.dll";
#elif defined(E33_PAUSE_MENU_SESSION) && defined(E33_VECTOR_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v23-pause-vector" / L"runtime_session_v23_pause_vector.dll";
#elif defined(E33_PAUSE_MENU_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v22-pause" / L"runtime_session_v22_pause.dll";
#elif defined(E33_UI_BATCH_SESSION) && defined(E33_VECTOR_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v20-ui-flight" / L"runtime_session_v20_ui.dll";
#elif defined(E33_UI_BATCH_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v20-ui" / L"runtime_session_v20_ui.dll";
#elif defined(E33_VECTOR_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v19-flight" / L"runtime_session_v19_flight.dll";
#else
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v19" / L"runtime_session_v19.dll";
#endif
#elif defined(E33_TRACE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v18" / L"runtime_session_v18.dll";
#elif defined(E33_MULTI_BUTTON_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v17" / L"runtime_session_v17.dll";
#elif defined(E33_BUTTON_ACTION_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v16" / L"runtime_session_v16.dll";
#elif defined(E33_BUTTON_REFERENCE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v15" / L"runtime_session_v15.dll";
#elif defined(E33_MENU_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v14" / L"runtime_session_v14.dll";
#elif defined(E33_ENUM_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v13" / L"runtime_session_v13.dll";
#elif defined(E33_TEXT_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v12" / L"runtime_session_v12.dll";
#elif defined(E33_POD_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v11" / L"runtime_session_v11.dll";
#elif defined(E33_ASSIGNMENT_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v10" / L"runtime_session_v10.dll";
#elif defined(E33_STABLE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v9" / L"runtime_session_v9.dll";
#elif defined(E33_RETAINED_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v8" / L"runtime_session_v8.dll";
#elif defined(E33_LEASE_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v7" / L"runtime_session_v7.dll";
#elif defined(E33_REFLECTED_SESSION)
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session-v6" / L"runtime_session_v6.dll";
#else
    auto path = std::filesystem::path(executable).parent_path().parent_path() / L"runtime-session" / L"runtime_session_v5.dll";
#endif
    connection.module = LoadLibraryW(path.c_str()); require(connection.module != nullptr, "SESSION_DLL_LOAD_FAILED");
    auto callback = reinterpret_cast<HOOKPROC>(GetProcAddress(connection.module, "SessionScheduleHook"));
    require(callback != nullptr, "SESSION_EXPORT_MISSING");
    connection.bootstrap = SetWindowsHookExW(WH_GETMESSAGE, callback, connection.module, thread);
    require(connection.bootstrap != nullptr, "SESSION_BOOTSTRAP_FAILED");
    connection.command(SessionOpen); connection.opened = true;
    require(packet.request.observed_pid == pid && packet.request.observed_tid == thread, "SESSION_THREAD_MISMATCH");
    require(UnhookWindowsHookEx(connection.bootstrap), "SESSION_BOOTSTRAP_REMOVE_FAILED"); connection.bootstrap = nullptr;
    std::cout << "{\"event\":\"session_ready\",\"pid\":" << pid << ",\"game_thread_id\":" << thread
#ifdef E33_MESH_SESSION
              << ",\"mesh_protocol\":3"
#endif
#ifdef E33_CATALOG_GAME_OWNED_SESSION
              << ",\"picto_edit_protocol\":1,\"picto_progression_protocol\":1,\"picto_class_load_protocol\":1,\"picto_cost_protocol\":1,\"picto_startup_protocol\":1,\"picto_stat_clear_protocol\":1,\"picto_stat_remove_protocol\":1,\"picto_inventory_protocol\":1,\"picto_batch_protocol\":1,\"picto_level_batch_protocol\":1,\"picto_mastery_batch_protocol\":1"
#endif
#ifdef E33_REFLECTED_SESSION
              << ",\"reflected_protocol\":1"
#endif
#ifdef E33_LEASE_SESSION
              << ",\"lease_protocol\":1"
#endif
#ifdef E33_RETAINED_SESSION
              << ",\"retained_protocol\":1"
#endif
#ifdef E33_STABLE_SESSION
              << ",\"stable_identity_protocol\":1"
#endif
#ifdef E33_ASSIGNMENT_SESSION
              << ",\"object_assignment_protocol\":1"
#endif
#ifdef E33_VIEWER_MENU_SESSION
              << ",\"menu_input_protocol\":1"
#endif
#ifdef E33_SCALAR_ASSIGNMENT_SESSION
              << ",\"scalar_assignment_protocol\":1"
#endif
#ifdef E33_POD_SESSION
              << ",\"pod_value_protocol\":1"
#endif
#ifdef E33_TEXT_SESSION
              << ",\"text_value_protocol\":1"
#ifdef E33_STRING_SESSION
              << ",\"string_value_protocol\":1"
#endif
#endif
#ifdef E33_ENUM_SESSION
              << ",\"enum_value_protocol\":1"
#endif
#ifdef E33_MENU_SESSION
              << ",\"menu_protocol\":1"
#endif
#ifdef E33_BUTTON_REFERENCE_SESSION
              << ",\"button_reference_protocol\":1"
#endif
#ifdef E33_BUTTON_ACTION_SESSION
              << ",\"button_action_protocol\":1,\"button_action_session\":" << packet.request.nonce
#endif
#ifdef E33_MULTI_BUTTON_SESSION
              << ",\"multi_button_protocol\":1,\"multi_button_capacity\":64"
#endif
#ifdef E33_TRACE_SESSION
              << ",\"trace_protocol\":1,\"trace_capacity\":16"
#ifdef E33_BLUEPRINT_TRACE_SESSION
              << ",\"blueprint_trace_protocol\":1"
#endif
#endif
#ifdef E33_KEYBIND_SESSION
              << ",\"key_capture_protocol\":1,\"keybind_protocol\":1,\"keybind_capacity\":64"
#endif
#ifdef E33_UI_BATCH_SESSION
              << ",\"ui_batch_protocol\":1"
#ifdef E33_LAYOUT_BATCH_SESSION
              << ",\"layout_batch_protocol\":3"
#endif
#endif
#ifdef E33_VECTOR_SESSION
              << ",\"vector_value_protocol\":1"
#endif
#ifdef E33_PAUSE_MENU_SESSION
              << ",\"pause_attachment_protocol\":2,\"trace_renew_protocol\":1"
#endif
#ifdef E33_MEDIA_SESSION
              << ",\"media_owner_protocol\":1"
#endif
#ifdef E33_SEQUENCE_SESSION
              << ",\"asset_load_protocol\":1"
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
              << ",\"sequence_player_protocol\":1"
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
              << ",\"scoped_assignment_protocol\":1"
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
              << ",\"music_audio_protocol\":1"
#endif
#ifdef E33_OWNED_SOUND_SESSION
              << ",\"owned_sound_protocol\":1"
#ifdef E33_EXTENDED_OWNED_AUDIO_SESSION
              << ",\"owned_sound_capacity\":32,\"owned_sound_volume_max\":2"
#endif
#endif
#ifdef E33_GROWING_LEASE_SESSION
              << ",\"lease_policy_protocol\":1"
#endif
#ifdef E33_CINEMATIC_WIDGET_SESSION
              << ",\"cinematic_widget_protocol\":1"
#endif
#ifdef E33_WIDGET_DIAGNOSTICS_SESSION
              << ",\"cinematic_widget_diagnostics_protocol\":1"
#endif
#ifdef E33_WIDGET_ANIMATION_SESSION
              << ",\"cinematic_widget_animation_protocol\":1"
#endif
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
              << ",\"audio_cleanup_diagnostics_protocol\":1"
#endif
#ifdef E33_AUDIO_COMPLETION_SESSION
              << ",\"owned_audio_cleanup_protocol\":1"
#endif
#ifdef E33_TIMESPAN_SESSION
              << ",\"timespan_values_protocol\":1"
#endif
#ifdef E33_SEQUENCE_CAMERA_SESSION
              << ",\"sequence_camera_protocol\":1"
#endif
#ifdef E33_CATALOG_GAME_OWNED_SESSION
              << ",\"original_game_action_protocol\":1"
#endif
#ifdef E33_SEQUENCE_BINDING_QUERY_SESSION
              << ",\"sequence_binding_query_protocol\":1"
#endif
#ifdef E33_FRAME_TIME_SESSION
              << ",\"frame_time_values_protocol\":1"
#endif
#ifdef E33_EMPTY_TITLE_SESSION
              << ",\"cinematic_empty_title_protocol\":1,\"cinematic_title_profiles\":[\"prologue_lumiere\",\"back_at_camp\"]"
#elif defined(E33_COVERAGE_SESSION)
              << ",\"cinematic_title_profiles\":[\"prologue_lumiere\"]"
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
              << ",\"cinematic_sound_event_protocol\":1"
#endif
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
              << ",\"cinematic_sound_diagnostics_protocol\":1"
#endif
#ifdef E33_ORIGINAL_AUDIO_PAUSE_SESSION
              << ",\"original_audio_pause_protocol\":1"
#endif
              << "}\n" << std::flush;
    std::string command;
    while (std::getline(std::cin, command)) {
#ifdef E33_GROWING_LEASE_SESSION
        packet.lease_owner=0;
        if(command.rfind("lease-owner ",0)==0) {
            const auto end=command.find(' ',12);
            require(end!=std::string::npos && end>12 && end-12<=20,"LEASE_OWNER_PREFIX_INVALID");
            const auto value=command.substr(12,end-12);
            require(value.find_first_not_of("0123456789")==std::string::npos,"LEASE_OWNER_INVALID");
            packet.lease_owner=std::stoull(value);
            command.erase(0,end+1);
        }
#endif
        auto separator=command.find(' ');
        packet.console_text[0]=0; packet.console_dropped=0;
#ifdef E33_GROWING_LEASE_SESSION
        bool lease_policy=command.substr(0,separator)=="lease-policy";
        if(lease_policy) {
            require(separator!=std::string::npos,"LEASE_POLICY_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(LeasePolicyPacket)*2,"LEASE_POLICY_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("LEASE_POLICY_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(LeasePolicyPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_CINEMATIC_WIDGET_SESSION
        bool widget_hook=command.substr(0,separator)=="cinematic-widget";
        if(widget_hook) {
            require(separator!=std::string::npos,"WIDGET_HOOK_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(CinematicWidgetPacket)*2,"WIDGET_HOOK_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("WIDGET_HOOK_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(CinematicWidgetPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
        bool sound_event=command.substr(0,separator)=="cinematic-sound-event";
        if(sound_event) {
            require(separator!=std::string::npos,"SOUND_EVENT_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(CinematicSoundEventPacket)*2,"SOUND_EVENT_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("SOUND_EVENT_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(CinematicSoundEventPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
        bool music_audio=command.substr(0,separator)=="music-audio-owner";
        if(music_audio) {
            require(separator!=std::string::npos,"MUSIC_AUDIO_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(MusicAudioOwnerPacket)*2,"MUSIC_AUDIO_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("MUSIC_AUDIO_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(MusicAudioOwnerPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
        bool picto_batch=command.substr(0,separator)=="picto-batch";
        if(picto_batch) {
            require(separator!=std::string::npos,"PICTO_BATCH_PAYLOAD_MISSING");auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(PictoBatchPacket)*2,"PICTO_BATCH_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned {if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw std::runtime_error("PICTO_BATCH_ENCODING");};
            for(size_t i=0;i<sizeof(PictoBatchPacket);++i)destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);separator=std::string::npos;
        }
#ifdef E33_MESH_SESSION
        bool mesh=command.substr(0,separator)=="mesh";
        if(mesh) {
            require(separator!=std::string::npos,"MESH_PAYLOAD_MISSING");auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(MeshPacket)*2,"MESH_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned {if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw std::runtime_error("MESH_ENCODING");};
            for(size_t i=0;i<sizeof(MeshPacket);++i)destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);separator=std::string::npos;
        }
#endif
        bool picto_progress=command.substr(0,separator)=="picto-progression";
        if(picto_progress) {
            require(separator!=std::string::npos,"PICTO_PAYLOAD_MISSING");auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(PictoProgressionPacket)*2,"PICTO_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw std::runtime_error("PICTO_ENCODING"); };
            for(size_t i=0;i<sizeof(PictoProgressionPacket);++i)destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);separator=std::string::npos;
        }
        bool scoped_assignment=command.substr(0,separator)=="scoped-assignment";
        if(scoped_assignment) {
            require(separator!=std::string::npos,"SCOPED_ASSIGNMENT_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(ScopedAssignmentPacket)*2,"SCOPED_ASSIGNMENT_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("SCOPED_ASSIGNMENT_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(ScopedAssignmentPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
        bool sequence=command.substr(0,separator)=="sequence-owner";
        if(sequence) {
            require(separator!=std::string::npos,"SEQUENCE_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(SequenceOwnerPacket)*2,"SEQUENCE_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("SEQUENCE_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(SequenceOwnerPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_MEDIA_SESSION
        bool media=command.substr(0,separator)=="media-owner";
        if(media) {
            require(separator!=std::string::npos,"MEDIA_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(MediaOwnerPacket)*2,"MEDIA_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("MEDIA_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(MediaOwnerPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator); separator=std::string::npos;
        }
#endif
        bool reflected=false;
        bool leased=false;
        bool retained=false;
        bool assignment=false;
        bool text=false;
        bool menu=false;
        bool button_action=false;
        bool multi_button=false;
#ifdef E33_PAUSE_MENU_SESSION
        bool pause=command.substr(0,separator)=="pause-attachment";
        if(pause) {
            require(separator!=std::string::npos,"PAUSE_PAYLOAD_MISSING");
            const auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(PauseAttachmentPacket)*2,"PAUSE_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("PAUSE_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(PauseAttachmentPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_UI_BATCH_SESSION
        bool ui_batch=command.substr(0,separator)=="ui-batch";
        if(ui_batch) {
            require(separator!=std::string::npos,"UI_BATCH_PAYLOAD_MISSING");
            const auto encoded=command.substr(separator+1);
            require(encoded.size()%2==0 && encoded.size()/2>=e33_ui::Header &&
                    encoded.size()/2<=e33_ui::Capacity,"UI_BATCH_SIZE");
            auto* data=reinterpret_cast<uint8_t*>(packet.console_text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("UI_BATCH_ENCODING"); };
            for(size_t i=0;i<encoded.size()/2;++i) data[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            require(e33_ui::header(data,static_cast<uint32_t>(encoded.size()/2),true),"UI_BATCH_HEADER");
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_KEYBIND_SESSION
        bool keys=command.substr(0,separator)=="keys";
        if(keys) {
            require(separator!=std::string::npos,"KEY_PAYLOAD_MISSING");
            const auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(e33_keys::Packet)*2,"KEY_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.keys);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("KEY_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(e33_keys::Packet);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            require(e33_keys::valid_request(packet.keys),"KEY_REQUEST_INVALID");
            command.resize(separator); separator=std::string::npos;
        }
#endif
#ifdef E33_TRACE_SESSION
        bool trace=command.substr(0,separator)=="trace";
        if(trace) {
            require(separator!=std::string::npos,"TRACE_PAYLOAD_MISSING");
            const auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(e33_trace::Packet)*2,"TRACE_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.trace);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("TRACE_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(e33_trace::Packet);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            require(e33_trace::valid_request(packet.trace),"TRACE_REQUEST_INVALID");
            command.resize(separator);
            separator=std::string::npos;
        }
#endif
#ifdef E33_MULTI_BUTTON_SESSION
        multi_button=command.substr(0,separator)=="multi-button";
        if(multi_button) {
            require(separator!=std::string::npos,"MULTI_BUTTON_PAYLOAD_MISSING");
            const auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(MultiButtonPacket)*2,"MULTI_BUTTON_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.multi_button);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("MULTI_BUTTON_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(MultiButtonPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            require(valid_multi_button_request(packet.multi_button),"MULTI_BUTTON_REQUEST_INVALID");
            command.resize(separator);
        }
#endif
#ifdef E33_BUTTON_ACTION_SESSION
        button_action=command.substr(0,separator)=="button-action";
        if(button_action) {
            require(separator!=std::string::npos,"BUTTON_ACTION_PAYLOAD_MISSING");
            const auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(ButtonActionPacket)*2,"BUTTON_ACTION_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.button_action);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("BUTTON_ACTION_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(ButtonActionPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            require(valid_button_action_request(packet.button_action),"BUTTON_ACTION_REQUEST_INVALID");
            command.resize(separator);
        }
#endif
#ifdef E33_MENU_SESSION
        menu=command.substr(0,separator)=="menu";
        if(menu) {
            require(separator!=std::string::npos,"MENU_PAYLOAD_MISSING");
            const auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(MenuPacket)*2,"MENU_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.menu);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("MENU_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(MenuPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);
        }
#endif
#ifdef E33_TEXT_SESSION
        text=command.substr(0,separator)=="text-invoke";
        if(text) {
            require(separator!=std::string::npos,"TEXT_PAYLOAD_MISSING");
            const auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(TextCallPacket)*2,"TEXT_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.text);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("TEXT_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(TextCallPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);
        }
#endif
#ifdef E33_ASSIGNMENT_SESSION
        assignment=command.substr(0,separator)=="object-assign";
        if(assignment) {
            require(separator!=std::string::npos,"ASSIGNMENT_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(AssignmentPacket)*2,"ASSIGNMENT_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.assignment);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("ASSIGNMENT_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(AssignmentPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);
        }
#endif
#ifdef E33_RETAINED_SESSION
        retained=command.substr(0,separator)=="retained-invoke";
        if(retained) {
            require(separator!=std::string::npos,"RETAINED_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(RetainedCallPacket)*2,"RETAINED_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.retained);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("RETAINED_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(RetainedCallPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);
        }
#endif
#ifdef E33_LEASE_SESSION
        auto tag=command.substr(0,separator);
        DWORD lease_action=tag=="lease-acquire" ? SessionLeaseAcquire :
            tag=="lease-release" ? SessionLeaseRelease : tag=="lease-status" ? SessionLeaseStatus : 0;
        leased=lease_action!=0;
        if(leased) {
            require(separator!=std::string::npos,"LEASE_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(LeasePacket)*2,"LEASE_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.lease);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("LEASE_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(LeasePacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);
        }
#endif
#ifdef E33_REFLECTED_SESSION
        reflected=command.substr(0,separator)=="reflected-invoke";
        if(reflected) {
            require(separator!=std::string::npos,"CALL_PAYLOAD_MISSING");
            auto encoded=command.substr(separator+1);
            require(encoded.size()==sizeof(CallPacket)*2,"CALL_PAYLOAD_SIZE");
            auto* destination=reinterpret_cast<uint8_t*>(&packet.call);
            auto digit=[](char c)->unsigned { if(c>='0'&&c<='9') return c-'0'; if(c>='a'&&c<='f') return c-'a'+10;
                throw std::runtime_error("CALL_PAYLOAD_ENCODING"); };
            for(size_t i=0;i<sizeof(CallPacket);++i) destination[i]=static_cast<uint8_t>(digit(encoded[i*2])*16+digit(encoded[i*2+1]));
            command.resize(separator);
        }
#endif
        if(!reflected && !leased && !retained && !assignment && !text && !menu && !button_action && !multi_button && separator!=std::string::npos) { decode_console_payload(command.substr(separator+1),packet.console_text); command.resize(separator); }
        DWORD action = command == "enable" ? SessionEnable : command == "disable" ? SessionDisable :
            command == "invoke" ? SessionInvoke : command == "drain" ? SessionDrain :
            command == "ping" ? SessionPing : command == "close" ? SessionClose :
            command == "console-attach" ? SessionConsoleAttach : command == "console-detach" ? SessionConsoleDetach :
            command == "console-status" ? SessionConsoleStatus : command == "console-poll" ? SessionConsolePoll :
            command == "console-execute" ? SessionConsoleExecute : command == "console-print" ? SessionConsolePrint :
            command == "console-names" ? SessionConsoleNames : command == "console-key" ? SessionConsoleKey : 0;
#ifdef E33_REFLECTED_SESSION
        if(reflected) action=SessionReflectedInvoke;
#endif
#ifdef E33_LEASE_SESSION
        if(leased) action=lease_action;
#endif
#ifdef E33_RETAINED_SESSION
        if(retained) action=SessionRetainedInvoke;
#endif
#ifdef E33_ASSIGNMENT_SESSION
        if(assignment) action=SessionObjectAssign;
#endif
#ifdef E33_TEXT_SESSION
        if(text) action=SessionTextInvoke;
#endif
#ifdef E33_MENU_SESSION
        if(menu) action=SessionMenu;
#endif
#ifdef E33_BUTTON_ACTION_SESSION
        if(button_action) action=SessionButtonAction;
#endif
#ifdef E33_MULTI_BUTTON_SESSION
        if(multi_button) action=SessionMultiButton;
#endif
#ifdef E33_TRACE_SESSION
        if(trace) action=SessionTrace;
#endif
#ifdef E33_KEYBIND_SESSION
        if(keys) action=SessionKeybind;
#endif
#ifdef E33_UI_BATCH_SESSION
        if(ui_batch) action=e33_ui::Action;
#endif
#ifdef E33_PAUSE_MENU_SESSION
        if(pause) action=SessionPauseAttachment;
#endif
#ifdef E33_MEDIA_SESSION
        if(media) action=SessionMediaOwner;
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
        if(sequence) action=SessionSequenceOwner;
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
#ifdef E33_MESH_SESSION
        if(mesh) action=SessionMesh;
#endif
        if(picto_progress) action=SessionPictoProgression;
        if(picto_batch) action=SessionPictoBatch;
        if(scoped_assignment) action=SessionScopedAssignment;
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
        if(music_audio) action=SessionMusicAudioOwner;
#endif
#ifdef E33_GROWING_LEASE_SESSION
        if(lease_policy) action=SessionLeasePolicy;
#endif
#ifdef E33_CINEMATIC_WIDGET_SESSION
        if(widget_hook) action=SessionCinematicWidget;
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
        if(sound_event) action=SessionCinematicSoundEvent;
#endif
        require(action != 0, "SESSION_UNKNOWN_COMMAND");
        connection.command(action);
        std::cout << "{\"event\":\"session_response\",\"command\":" << quote(command)
                  << ",\"result\":" << packet.request.result << ",\"closed\":" << (packet.closed ? "true" : "false")
                  << ",\"close_reason\":" << packet.close_reason << ",\"dropped\":" << (action == SessionDrain ? packet.events.dropped : 0)
                  << ",\"console_text\":" << quote(action==SessionConsolePoll ? console_utf8(packet.console_text) : "")
                  << ",\"console_dropped\":" << packet.console_dropped
                  << ",\"events\":[";
        if (action == SessionDrain) {
            require(packet.events.count <= 64, "SESSION_EVENT_COUNT_INVALID");
            for (uint32_t i = 0; i < packet.events.count; ++i) {
                const auto& event = packet.events.records[i];
                if (i) std::cout << ',';
                std::cout << "{\"object_address\":" << quote(hex(event.object)) << ",\"thread\":" << event.thread
                          << ",\"result\":" << unsigned(event.result) << '}';
            }
        }
        std::cout << ']';
#ifdef E33_GROWING_LEASE_SESSION
        if(lease_policy) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(LeasePolicyPacket)*2,'0');
            for(size_t i=0;i<sizeof(LeasePolicyPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"lease_policy_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_CINEMATIC_WIDGET_SESSION
        if(widget_hook) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(CinematicWidgetPacket)*2,'0');
            for(size_t i=0;i<sizeof(CinematicWidgetPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"cinematic_widget_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
        if(sound_event) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(CinematicSoundEventPacket)*2,'0');
            for(size_t i=0;i<sizeof(CinematicSoundEventPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"cinematic_sound_event_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
        if(music_audio) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(MusicAudioOwnerPacket)*2,'0');
            for(size_t i=0;i<sizeof(MusicAudioOwnerPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"music_audio_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
        if(picto_batch) {
            static const char digits[]="0123456789abcdef";const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(PictoBatchPacket)*2,'0');
            for(size_t i=0;i<sizeof(PictoBatchPacket);++i){encoded[i*2]=digits[source[i]>>4];encoded[i*2+1]=digits[source[i]&15];}
            std::cout << ",\"picto_batch_packet\":" << quote(encoded);
        }
#ifdef E33_MESH_SESSION
        if(mesh) {
            static const char digits[]="0123456789abcdef";const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(MeshPacket)*2,'0');
            for(size_t i=0;i<sizeof(MeshPacket);++i){encoded[i*2]=digits[source[i]>>4];encoded[i*2+1]=digits[source[i]&15];}
            std::cout << ",\"mesh_packet\":" << quote(encoded);
        }
#endif
        if(picto_progress) {
            static const char digits[]="0123456789abcdef";const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(PictoProgressionPacket)*2,'0');
            for(size_t i=0;i<sizeof(PictoProgressionPacket);++i){encoded[i*2]=digits[source[i]>>4];encoded[i*2+1]=digits[source[i]&15];}
            std::cout << ",\"picto_progression_packet\":" << quote(encoded);
        }
        if(scoped_assignment) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(ScopedAssignmentPacket)*2,'0');
            for(size_t i=0;i<sizeof(ScopedAssignmentPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"scoped_assignment_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
        if(sequence) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(SequenceOwnerPacket)*2,'0');
            for(size_t i=0;i<sizeof(SequenceOwnerPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"sequence_owner_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_MEDIA_SESSION
        if(media) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(MediaOwnerPacket)*2,'0');
            for(size_t i=0;i<sizeof(MediaOwnerPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"media_owner_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_PAUSE_MENU_SESSION
        if(pause) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            std::string encoded(sizeof(PauseAttachmentPacket)*2,'0');
            for(size_t i=0;i<sizeof(PauseAttachmentPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"pause_attachment_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_UI_BATCH_SESSION
        if(ui_batch) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(packet.console_text);
            const auto size=e33_ui::word(source+8);
            require(e33_ui::header(source,size,false),"UI_BATCH_RESPONSE");
            std::string encoded(size*2,'0');
            for(size_t i=0;i<size;++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"ui_batch_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_KEYBIND_SESSION
        if(keys) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.keys);
            std::string encoded(sizeof(e33_keys::Packet)*2,'0');
            for(size_t i=0;i<sizeof(e33_keys::Packet);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"key_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_TRACE_SESSION
        if(trace) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.trace);
            std::string encoded(sizeof(e33_trace::Packet)*2,'0');
            for(size_t i=0;i<sizeof(e33_trace::Packet);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"trace_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_MULTI_BUTTON_SESSION
        if(multi_button) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.multi_button);
            std::string encoded(sizeof(MultiButtonPacket)*2,'0');
            for(size_t i=0;i<sizeof(MultiButtonPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"multi_button_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_BUTTON_ACTION_SESSION
        if(button_action) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.button_action);
            std::string encoded(sizeof(ButtonActionPacket)*2,'0');
            for(size_t i=0;i<sizeof(ButtonActionPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"button_action_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_MENU_SESSION
        if(menu) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.menu);
            std::string encoded(sizeof(MenuPacket)*2,'0');
            for(size_t i=0;i<sizeof(MenuPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"menu_packet\":" << quote(encoded);
#ifdef E33_BUTTON_REFERENCE_SESSION
            std::cout << ",\"button_reference_state\":" << packet.request.result;
#endif
        }
#endif
#ifdef E33_TEXT_SESSION
        if(text) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.text);
            std::string encoded(sizeof(TextCallPacket)*2,'0');
            for(size_t i=0;i<sizeof(TextCallPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"text_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_ASSIGNMENT_SESSION
        if(assignment) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.assignment);
            std::string encoded(sizeof(AssignmentPacket)*2,'0');
            for(size_t i=0;i<sizeof(AssignmentPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"assignment_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_RETAINED_SESSION
        if(retained) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.retained);
            std::string encoded(sizeof(RetainedCallPacket)*2,'0');
            for(size_t i=0;i<sizeof(RetainedCallPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"retained_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_LEASE_SESSION
        if(leased) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.lease);
            std::string encoded(sizeof(LeasePacket)*2,'0');
            for(size_t i=0;i<sizeof(LeasePacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"lease_packet\":" << quote(encoded);
        }
#endif
#ifdef E33_REFLECTED_SESSION
        if(reflected) {
            static const char digits[]="0123456789abcdef";
            const auto* source=reinterpret_cast<const uint8_t*>(&packet.call);
            std::string encoded(sizeof(CallPacket)*2,'0');
            for(size_t i=0;i<sizeof(CallPacket);++i) { encoded[i*2]=digits[source[i]>>4]; encoded[i*2+1]=digits[source[i]&15]; }
            std::cout << ",\"call_packet\":" << quote(encoded);
        }
#endif
        std::cout << "}\n" << std::flush;
        if (action == SessionClose) break;
    }
}
