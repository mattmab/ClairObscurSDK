#pragma once
#include "scheduling_protocol.h"

// Included by the fingerprint-validating research probe. Only a fixed ping can
// execute; target PID/TID come from validated runtime discovery, not CLI input.
inline bool ping_module_loaded(DWORD pid) {
    Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
    require(snapshot.value != INVALID_HANDLE_VALUE, "PING_MODULE_SNAPSHOT_FAILED");
    MODULEENTRY32W row{}; row.dwSize = sizeof(row);
    for (BOOL next = Module32FirstW(snapshot.value, &row); next; next = Module32NextW(snapshot.value, &row))
        if (_wcsicmp(row.szModule, L"scheduling_hook.dll") == 0) return true;
    return false;
}
inline void run_thread_ping(DWORD pid, DWORD thread, DWORD action = 0,
                            int32_t object_index = 0, int32_t object_serial = 0,
                            int32_t function_index = 0, int32_t function_serial = 0) {
    uint64_t nonce = 0;
    require(BCryptGenRandom(nullptr, reinterpret_cast<PUCHAR>(&nonce), sizeof(nonce), BCRYPT_USE_SYSTEM_PREFERRED_RNG) >= 0,
            "PING_RANDOM_FAILED");
    DWORD controller = GetCurrentProcessId(); wchar_t name[96]; mapping_name(name, controller, nonce);
    Handle mapping(CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, sizeof(SchedulePacket), name));
    require(mapping.value && GetLastError() != ERROR_ALREADY_EXISTS, "PING_MAPPING_FAILED");
    struct Resources {
        SchedulePacket* packet = nullptr; HMODULE module = nullptr; HHOOK hook = nullptr;
        ~Resources() {
            if (hook) UnhookWindowsHookEx(hook);
            if (module) FreeLibrary(module);
            if (packet) UnmapViewOfFile(packet);
        }
    } resources;
    resources.packet = static_cast<SchedulePacket*>(MapViewOfFile(mapping.value, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SchedulePacket)));
    require(resources.packet != nullptr, "PING_MAPPING_VIEW_FAILED");
    auto& packet = *resources.packet;
    packet.magic = kScheduleMagic; packet.version = 1; packet.nonce = nonce;
    packet.target_pid = pid; packet.target_tid = thread;
    packet.action = action; packet.object_index = object_index; packet.object_serial = object_serial;
    packet.function_index = function_index; packet.function_serial = function_serial;
    wchar_t executable[32768]; auto size = GetModuleFileNameW(nullptr, executable, 32768);
    require(size > 0 && size < 32768, "PING_PROBE_PATH_FAILED");
    auto dll = std::filesystem::path(executable).parent_path().parent_path() / L"scheduling-fixture" / L"scheduling_hook.dll";
    require(!ping_module_loaded(pid), "PING_DLL_ALREADY_LOADED");
    resources.module = LoadLibraryW(dll.c_str());
    require(resources.module != nullptr, "PING_DLL_LOAD_FAILED");
    auto callback = reinterpret_cast<HOOKPROC>(GetProcAddress(resources.module, "ResearchScheduleHook"));
    require(callback != nullptr, "PING_EXPORT_MISSING");
    UINT message = RegisterWindowMessageW(kScheduleMessage);
    require(message != 0, "PING_MESSAGE_REGISTRATION_FAILED");
    resources.hook = SetWindowsHookExW(WH_GETMESSAGE, callback, resources.module, thread);
    require(resources.hook != nullptr, "PING_HOOK_FAILED win32=" + std::to_string(GetLastError()));
    InterlockedExchange(&packet.state, kRequested);
    require(PostThreadMessageW(thread, message, nonce, controller) != FALSE, "PING_POST_FAILED");
    ULONGLONG start = GetTickCount64();
    while (InterlockedCompareExchange(&packet.state, 0, 0) != kComplete && GetTickCount64() - start < 5000) Sleep(5);
    bool completed = InterlockedCompareExchange(&packet.state, 0, 0) == kComplete;
    // Remove even when the target did not service the message. Windows owns the
    // remote DLL reference; we never force-unload code from the game.
    require(UnhookWindowsHookEx(resources.hook) != FALSE, "PING_UNHOOK_FAILED"); resources.hook = nullptr;
    start = GetTickCount64();
    bool unloaded = false;
    do {
        PostThreadMessageW(thread, WM_NULL, 0, 0);
        unloaded = !ping_module_loaded(pid);
        if (unloaded) break;
        Sleep(10);
    } while (GetTickCount64() - start < 5000);
    require(unloaded, "PING_REMOTE_DLL_UNLOAD_NOT_VERIFIED");
    require(completed, "PING_CALLBACK_TIMEOUT");
    require(packet.error == 0, "FIXED_INVOCATION_REJECTED code=" + std::to_string(packet.error));
    require(packet.observed_pid == pid && packet.observed_tid == thread &&
            (action == 0 ? packet.result == 42 : packet.result <= 1) && packet.callbacks == 1,
            "PING_IDENTITY_OR_RESULT_MISMATCH");
    std::cout << "{\"event\":" << quote(action == 0 ? "thread_ping" : "fixed_invocation") << ",\"observed_pid\":" << packet.observed_pid
              << ",\"observed_tid\":" << packet.observed_tid << ",\"result\":" << packet.result << ",\"callbacks\":1"
              << ",\"hook_removed\":true,\"remote_module_unloaded\":true}\n";
}
