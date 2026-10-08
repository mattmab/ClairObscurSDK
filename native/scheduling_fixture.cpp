#include "scheduling_protocol.h"
#include <tlhelp32.h>
#include <bcrypt.h>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(std::string(message) + " win32=" + std::to_string(GetLastError()));
}
struct Mapping {
    HANDLE handle = nullptr; SchedulePacket* packet = nullptr;
    ~Mapping() { if (packet) UnmapViewOfFile(packet); if (handle) CloseHandle(handle); }
};
struct Child {
    PROCESS_INFORMATION process{};
    ~Child() {
        if (process.hProcess) {
            if (WaitForSingleObject(process.hProcess, 0) == WAIT_TIMEOUT) {
                PostThreadMessageW(process.dwThreadId, WM_QUIT, 0, 0);
                if (WaitForSingleObject(process.hProcess, 5000) == WAIT_TIMEOUT) {
                    // Only our explicitly created fixture child, never the game.
                    TerminateProcess(process.hProcess, 2); WaitForSingleObject(process.hProcess, 5000);
                }
            }
            CloseHandle(process.hProcess); CloseHandle(process.hThread);
        }
    }
};
struct Hook {
    HMODULE module = nullptr; HHOOK hook = nullptr;
    ~Hook() { if (hook) UnhookWindowsHookEx(hook); if (module) FreeLibrary(module); }
};
template<class Predicate> bool wait_until(Predicate predicate, DWORD timeout = 5000) {
    ULONGLONG start = GetTickCount64();
    while (!predicate()) { if (GetTickCount64() - start >= timeout) return false; Sleep(5); }
    return true;
}
LONG read_atomic(volatile LONG* value) { return InterlockedCompareExchange(value, 0, 0); }
bool module_loaded(DWORD pid) {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    check(snapshot != INVALID_HANDLE_VALUE, "MODULE_SNAPSHOT_FAILED");
    MODULEENTRY32W entry{}; entry.dwSize = sizeof(entry); bool found = false;
    for (BOOL next = Module32FirstW(snapshot, &entry); next; next = Module32NextW(snapshot, &entry))
        if (_wcsicmp(entry.szModule, L"scheduling_hook.dll") == 0) found = true;
    CloseHandle(snapshot); return found;
}
int host(DWORD controller, uint64_t nonce) {
    wchar_t name[96]; mapping_name(name, controller, nonce); Mapping map;
    map.handle = OpenFileMappingW(FILE_MAP_READ | FILE_MAP_WRITE, FALSE, name);
    check(map.handle != nullptr, "HOST_MAPPING_OPEN_FAILED");
    map.packet = static_cast<SchedulePacket*>(MapViewOfFile(map.handle, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SchedulePacket)));
    check(map.packet != nullptr, "HOST_MAPPING_VIEW_FAILED");
    UINT barrier = RegisterWindowMessageW(kBarrierMessage); check(barrier != 0, "HOST_MESSAGE_FAILED");
    MSG message{}; PeekMessageW(&message, nullptr, 0, 0, PM_NOREMOVE);
    InterlockedExchange(&map.packet->ready, 1);
    BOOL result;
    while ((result = GetMessageW(&message, nullptr, 0, 0)) > 0) {
        if (!message.hwnd && message.message == barrier) InterlockedIncrement(&map.packet->barriers);
        else { TranslateMessage(&message); DispatchMessageW(&message); }
    }
    check(result == 0, "HOST_MESSAGE_LOOP_FAILED"); return 0;
}
int self_test() {
    uint64_t nonce = 0;
    check(BCryptGenRandom(nullptr, reinterpret_cast<PUCHAR>(&nonce), sizeof(nonce), BCRYPT_USE_SYSTEM_PREFERRED_RNG) >= 0,
          "RANDOM_FAILED");
    DWORD controller = GetCurrentProcessId(); wchar_t name[96]; mapping_name(name, controller, nonce);
    Mapping map;
    map.handle = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, sizeof(SchedulePacket), name);
    check(map.handle && GetLastError() != ERROR_ALREADY_EXISTS, "MAPPING_CREATE_FAILED");
    map.packet = static_cast<SchedulePacket*>(MapViewOfFile(map.handle, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SchedulePacket)));
    check(map.packet != nullptr, "MAPPING_VIEW_FAILED");
    auto& packet = *map.packet;
    packet.magic = kScheduleMagic; packet.version = 1; packet.nonce = nonce;
    wchar_t executable[32768]; DWORD length = GetModuleFileNameW(nullptr, executable, 32768);
    check(length > 0 && length < 32768, "SELF_PATH_FAILED");
    std::wstring command = L"\"" + std::wstring(executable) + L"\" --host " +
                           std::to_wstring(controller) + L" " + std::to_wstring(nonce);
    STARTUPINFOW startup{}; startup.cb = sizeof(startup); Child child;
    check(CreateProcessW(executable, command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW,
                         nullptr, nullptr, &startup, &child.process) != FALSE, "FIXTURE_CREATE_FAILED");
    packet.target_pid = child.process.dwProcessId; packet.target_tid = child.process.dwThreadId;
    check(wait_until([&] { return read_atomic(&packet.ready) == 1; }), "FIXTURE_QUEUE_TIMEOUT");
    check(!module_loaded(packet.target_pid), "HOOK_ALREADY_LOADED");
    UINT request = RegisterWindowMessageW(kScheduleMessage), barrier = RegisterWindowMessageW(kBarrierMessage);
    check(request && barrier, "MESSAGE_REGISTRATION_FAILED");
    auto post = [&](UINT message) { check(PostThreadMessageW(child.process.dwThreadId, message, nonce, controller) != FALSE, "POST_FAILED"); };
    LONG barriers = 0;
    auto fence = [&] { ++barriers; post(barrier); check(wait_until([&] { return read_atomic(&packet.barriers) == barriers; }), "FENCE_TIMEOUT"); };
    Hook hook;
    auto path = std::filesystem::path(executable).parent_path() / L"scheduling_hook.dll";
    hook.module = LoadLibraryW(path.c_str()); check(hook.module != nullptr, "DLL_LOAD_FAILED");
    auto callback = reinterpret_cast<HOOKPROC>(GetProcAddress(hook.module, "ResearchScheduleHook"));
    check(callback != nullptr, "EXPORT_MISSING");
    hook.hook = SetWindowsHookExW(WH_GETMESSAGE, callback, hook.module, child.process.dwThreadId);
    check(hook.hook != nullptr, "THREAD_HOOK_FAILED");
    InterlockedExchange(&packet.state, kRequested); post(request); fence();
    check(read_atomic(&packet.state) == kComplete && packet.callbacks == 1 && packet.result == 42 &&
          packet.observed_pid == packet.target_pid && packet.observed_tid == packet.target_tid, "CALLBACK_PROOF_FAILED");
    check(module_loaded(packet.target_pid), "REMOTE_DLL_NOT_OBSERVED");
    // Wrong thread identity must fail closed, then a corrected request must work.
    packet.target_tid = 0; InterlockedExchange(&packet.state, kRequested); post(request); fence();
    check(packet.state == kRequested && packet.callbacks == 1, "WRONG_THREAD_ACCEPTED");
    packet.target_tid = child.process.dwThreadId; post(request); fence();
    check(packet.state == kComplete && packet.callbacks == 2, "SECOND_CALLBACK_FAILED");
    packet.action = 1; InterlockedExchange(&packet.state, kRequested); post(request); fence();
    check(packet.state == kComplete && packet.callbacks == 3 && packet.error == 11,
          "NON_GAME_INVOCATION_NOT_REJECTED");
    packet.action = 0; InterlockedExchange(&packet.state, kRequested); post(request); fence();
    check(packet.state == kComplete && packet.callbacks == 4 && packet.error == 0 && packet.result == 42,
          "PING_AFTER_REJECTION_FAILED");
    InterlockedExchange(&packet.state, kRequested);
    check(!wait_until([&] { return read_atomic(&packet.state) == kComplete; }, 100), "MISSING_REQUEST_COMPLETED");
    check(UnhookWindowsHookEx(hook.hook) != FALSE, "UNHOOK_FAILED"); hook.hook = nullptr;
    post(request); fence();
    check(packet.state == kRequested && packet.callbacks == 4, "CALLBACK_AFTER_REMOVAL");
    bool unloaded = wait_until([&] { post(WM_NULL); return !module_loaded(packet.target_pid); }, 2000);
    check(unloaded, "REMOTE_DLL_UNLOAD_NOT_VERIFIED");
    post(WM_QUIT); check(WaitForSingleObject(child.process.hProcess, 5000) == WAIT_OBJECT_0, "CHILD_EXIT_TIMEOUT");
    DWORD exit_code = 1; check(GetExitCodeProcess(child.process.hProcess, &exit_code) && exit_code == 0, "CHILD_EXIT_FAILED");
    std::cout << "{\"fixture_pid\":" << packet.target_pid << ",\"fixture_tid\":" << packet.target_tid
              << ",\"observed_pid\":" << packet.observed_pid << ",\"observed_tid\":" << packet.observed_tid
              << ",\"result\":" << packet.result << ",\"callbacks\":" << packet.callbacks
              << ",\"wrong_thread_rejected\":true,\"non_game_invocation_rejected\":true,\"timeout_verified\":true,\"removal_verified\":true"
              << ",\"remote_module_unloaded\":" << (unloaded ? "true" : "false") << ",\"child_exit\":0}\n";
    return 0;
}
int wmain(int argc, wchar_t** argv) {
    try {
        if (argc == 4 && std::wstring(argv[1]) == L"--host")
            return host(std::stoul(argv[2]), std::stoull(argv[3]));
        check(argc == 2 && std::wstring(argv[1]) == L"--self-test", "USAGE --self-test");
        return self_test();
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
