#pragma once
#include "session_protocol.h"
#include "target_process_exit.h"

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
            Sleep(2);
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
#ifdef E33_BUTTON_ACTION_SESSION
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
#ifdef E33_POD_SESSION
              << ",\"pod_value_protocol\":1"
#endif
#ifdef E33_TEXT_SESSION
              << ",\"text_value_protocol\":1"
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
              << "}\n" << std::flush;
    std::string command;
    while (std::getline(std::cin, command)) {
        auto separator=command.find(' ');
        packet.console_text[0]=0; packet.console_dropped=0;
        bool reflected=false;
        bool leased=false;
        bool retained=false;
        bool assignment=false;
        bool text=false;
        bool menu=false;
        bool button_action=false;
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
        if(!reflected && !leased && !retained && !assignment && !text && !menu && !button_action && separator!=std::string::npos) { decode_console_payload(command.substr(separator+1),packet.console_text); command.resize(separator); }
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
