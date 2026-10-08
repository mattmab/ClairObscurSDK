#pragma once
#include "fixed_observer_protocol.h"

inline bool observer_module_loaded(DWORD pid) {
    Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
    require(snapshot.value != INVALID_HANDLE_VALUE, "OBSERVER_MODULE_SNAPSHOT_FAILED");
    MODULEENTRY32W row{}; row.dwSize = sizeof(row);
    for (BOOL next = Module32FirstW(snapshot.value, &row); next; next = Module32NextW(snapshot.value, &row))
        if (_wcsicmp(row.szModule, kObserverDll) == 0) return true;
    return false;
}

inline void run_fixed_observer(DWORD pid, DWORD thread, int32_t object_index, int32_t object_serial,
                               int32_t function_index, int32_t function_serial) {
    uint64_t nonce = 0;
    require(BCryptGenRandom(nullptr, reinterpret_cast<PUCHAR>(&nonce), sizeof(nonce), BCRYPT_USE_SYSTEM_PREFERRED_RNG) >= 0,
            "OBSERVER_RANDOM_FAILED");
    DWORD controller = GetCurrentProcessId(); wchar_t name[96]; mapping_name(name, controller, nonce);
    Handle mapping(CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, sizeof(FixedObserverPacket), name));
    require(mapping.value && GetLastError() != ERROR_ALREADY_EXISTS, "OBSERVER_MAPPING_FAILED");
    struct Resources {
        FixedObserverPacket* packet = nullptr; HMODULE module = nullptr; HHOOK hook = nullptr;
        ~Resources() {
            if (hook) UnhookWindowsHookEx(hook);
            if (module) FreeLibrary(module);
            if (packet) UnmapViewOfFile(packet);
        }
    } resources;
    resources.packet = static_cast<FixedObserverPacket*>(MapViewOfFile(mapping.value, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(FixedObserverPacket)));
    require(resources.packet != nullptr, "OBSERVER_MAPPING_VIEW_FAILED");
    auto& packet = *resources.packet; auto& request = packet.schedule;
    request.magic = kScheduleMagic; request.version = 1; request.nonce = nonce;
    request.target_pid = pid; request.target_tid = thread; request.action = 2;
    request.object_index = object_index; request.object_serial = object_serial;
    request.function_index = function_index; request.function_serial = function_serial;
    wchar_t executable[32768]; auto size = GetModuleFileNameW(nullptr, executable, 32768);
    require(size > 0 && size < 32768, "OBSERVER_PROBE_PATH_FAILED");
    auto dll = std::filesystem::path(executable).parent_path().parent_path() / L"fixed-observer" / kObserverDll;
    resources.module = LoadLibraryW(dll.c_str()); require(resources.module != nullptr, "OBSERVER_DLL_LOAD_FAILED");
    auto callback = reinterpret_cast<HOOKPROC>(GetProcAddress(resources.module, "ResearchObserverSchedule"));
    require(callback != nullptr, "OBSERVER_EXPORT_MISSING");
    UINT message = RegisterWindowMessageW(kObserverMessage); require(message != 0, "OBSERVER_MESSAGE_FAILED");
    resources.hook = SetWindowsHookExW(WH_GETMESSAGE, callback, resources.module, thread);
    require(resources.hook != nullptr, "OBSERVER_SCHEDULE_HOOK_FAILED win32=" + std::to_string(GetLastError()));
    InterlockedExchange(&request.state, kRequested);
    require(PostThreadMessageW(thread, message, nonce, controller) != FALSE, "OBSERVER_POST_FAILED");
    ULONGLONG start = GetTickCount64();
    while (InterlockedCompareExchange(&request.state, 0, 0) != kComplete && GetTickCount64() - start < 5000) Sleep(5);
    bool completed = InterlockedCompareExchange(&request.state, 0, 0) == kComplete;
    require(UnhookWindowsHookEx(resources.hook) != FALSE, "OBSERVER_SCHEDULE_UNHOOK_FAILED"); resources.hook = nullptr;
    require(completed, "OBSERVER_TIMEOUT restoration not confirmed");
    require(request.error == 0, "OBSERVER_REJECTED code=" + std::to_string(request.error) +
            " restored=" + std::to_string(packet.restored));
    require(request.observed_pid == pid && request.observed_tid == thread && request.callbacks == 1 &&
            request.result <= 1 && packet.restored == 1 && packet.events.count == 2 &&
            packet.events.dropped == 0 && packet.after_remove_count == 2, "OBSERVER_RESULT_INVALID");
    require(observer_module_loaded(pid), "OBSERVER_RESIDENT_MODULE_NOT_FOUND");
    for (uint32_t i = 0; i < packet.events.count; ++i) {
        const auto& event = packet.events.records[i];
        require(event.thread == thread && event.result <= 1, "OBSERVER_EVENT_INVALID");
        std::cout << "{\"event\":\"observed_getter\",\"sequence\":" << (i + 1)
                  << ",\"object_index\":" << object_index << ",\"object_serial\":" << object_serial
                  << ",\"object_address\":" << quote(hex(event.object)) << ",\"thread\":" << event.thread
                  << ",\"result\":" << unsigned(event.result) << "}\n";
    }
    std::cout << "{\"event\":\"observer_proof\",\"entry_restored\":true,\"scheduling_hook_removed\":true,"
                 "\"module_resident\":true,\"events\":2,\"after_remove_count\":2,\"dropped\":0}\n";
}
