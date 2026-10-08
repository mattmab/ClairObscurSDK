#include "session_protocol.h"
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <bcrypt.h>

static void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
template<class F> static bool wait_for(F condition) {
    auto start = GetTickCount64();
    while (!condition()) { if (GetTickCount64() - start > 5000) return false; Sleep(2); }
    return true;
}
static LONG atomic_read(volatile LONG* value) { return InterlockedCompareExchange(value, 0, 0); }
static std::filesystem::path self_path() {
    wchar_t path[32768]; require(GetModuleFileNameW(nullptr, path, 32768) != 0, "SELF_PATH"); return path;
}
struct Controller {
    HANDLE mapping = nullptr;
    SessionPacket* packet = nullptr;
    HMODULE module = nullptr;
    HHOOK bootstrap = nullptr;
    DWORD tid = 0; uint64_t nonce = 0;
    ~Controller() {
        if (bootstrap) UnhookWindowsHookEx(bootstrap);
        if (module) FreeLibrary(module);
        if (packet) UnmapViewOfFile(packet);
        if (mapping) CloseHandle(mapping);
    }
    void command(DWORD action) {
        packet->request.action = action; packet->request.error = 0;
        InterlockedExchange(&packet->request.state, kRequested);
        UINT message = RegisterWindowMessageW(kSessionMessage);
        require(message && PostThreadMessageW(tid, message, nonce, GetCurrentProcessId()), "POST");
        require(wait_for([&] { return atomic_read(&packet->request.state) == kComplete; }), "REQUEST_TIMEOUT");
        if (packet->request.error) throw std::runtime_error("BACKEND_ERROR=" + std::to_string(packet->request.error));
    }
};
static int controller(DWORD pid, DWORD tid, uint64_t nonce, bool abrupt) {
    Controller connection; connection.tid = tid; connection.nonce = nonce;
    wchar_t name[96]; session_mapping_name(name, GetCurrentProcessId(), nonce);
    connection.mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, sizeof(SessionPacket), name);
    require(connection.mapping && GetLastError() != ERROR_ALREADY_EXISTS, "CREATE_MAPPING");
    connection.packet = static_cast<SessionPacket*>(MapViewOfFile(connection.mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SessionPacket)));
    require(connection.packet != nullptr, "MAP_VIEW");
    auto& packet = *connection.packet;
    packet.request.magic = kScheduleMagic; packet.request.version = 1; packet.request.nonce = nonce;
    packet.request.target_pid = pid; packet.request.target_tid = tid; packet.controller = GetCurrentProcessId();
    connection.module = LoadLibraryW((self_path().parent_path() / L"session_fixture.dll").c_str());
    require(connection.module != nullptr, "LOAD_DLL");
    auto hook = reinterpret_cast<HOOKPROC>(GetProcAddress(connection.module, "SessionScheduleHook"));
    require(hook != nullptr, "EXPORT");
    connection.bootstrap = SetWindowsHookExW(WH_GETMESSAGE, hook, connection.module, tid);
    require(connection.bootstrap != nullptr, "BOOTSTRAP_HOOK");
    connection.command(SessionOpen);
    require(packet.request.observed_pid == pid && packet.request.observed_tid == tid, "THREAD_IDENTITY");
    require(UnhookWindowsHookEx(connection.bootstrap), "BOOTSTRAP_REMOVE"); connection.bootstrap = nullptr;
    connection.command(SessionEnable); connection.command(SessionEnable);
    connection.command(SessionInvoke); require(packet.request.result == 42, "RESULT");
    connection.command(SessionDrain);
    require(packet.events.count == 1 && packet.events.dropped == 0 && packet.events.records[0].object == 123 &&
            packet.events.records[0].thread == tid && packet.events.records[0].result == 42, "EVENT_CONTEXT");
    connection.command(SessionDrain); require(packet.events.count == 0, "DRAIN_NOT_CONSUMED");
    connection.command(SessionDisable); connection.command(SessionDisable);
    connection.command(SessionInvoke); require(packet.request.result == 42, "REMOVED_RESULT");
    connection.command(SessionDrain); require(packet.events.count == 0, "REMOVED_EVENT");
    connection.command(SessionEnable); connection.command(SessionInvoke);
    connection.command(SessionDrain); require(packet.events.count == 1, "REENABLE_DUPLICATION");
    if (abrupt) ExitProcess(0); // Own fixture controller only: deliberately omit graceful close.
    connection.command(SessionClose);
    require(atomic_read(&packet.closed) == 1 && packet.close_reason == ClosedNormally, "CLOSE_ACK");
    return 0;
}
static DWORD WINAPI pump(void* argument) {
    MSG message{}; PeekMessageW(&message, nullptr, 0, 0, PM_NOREMOVE); SetEvent(argument);
    while (GetMessageW(&message, nullptr, 0, 0) > 0) { TranslateMessage(&message); DispatchMessageW(&message); }
    return 0;
}
struct Host {
    HANDLE ready = nullptr, thread = nullptr; DWORD tid = 0; HMODULE module = nullptr;
    ~Host() {
        if (thread) { PostThreadMessageW(tid, WM_QUIT, 0, 0); WaitForSingleObject(thread, 5000); CloseHandle(thread); }
        if (ready) CloseHandle(ready);
        if (module) FreeLibrary(module);
    }
};
static int self_test() {
    Host host;
    host.ready = CreateEventW(nullptr, TRUE, FALSE, nullptr); require(host.ready != nullptr, "READY_EVENT");
    host.thread = CreateThread(nullptr, 0, pump, host.ready, 0, &host.tid);
    require(host.thread && WaitForSingleObject(host.ready, 5000) == WAIT_OBJECT_0, "PUMP_START");
    host.module = LoadLibraryW((self_path().parent_path() / L"session_fixture.dll").c_str()); require(host.module != nullptr, "HOST_DLL");
    auto count = reinterpret_cast<LONG(*)()>(GetProcAddress(host.module, "FixtureCloseCount"));
    auto reason = reinterpret_cast<LONG(*)()>(GetProcAddress(host.module, "FixtureCloseReason"));
    require(count && reason, "STATUS_EXPORTS");
    for (int iteration = 0; iteration < 6; ++iteration) {
        bool abrupt = (iteration % 2) != 0;
        uint64_t nonce = 0; require(BCryptGenRandom(nullptr, reinterpret_cast<PUCHAR>(&nonce), sizeof(nonce), BCRYPT_USE_SYSTEM_PREFERRED_RNG) >= 0, "NONCE");
        std::wstring command = L"\"" + self_path().wstring() + L"\" --controller " + std::to_wstring(GetCurrentProcessId()) +
            L" " + std::to_wstring(host.tid) + L" " + std::to_wstring(nonce) + L" " + (abrupt ? L"1" : L"0");
        STARTUPINFOW startup{}; startup.cb = sizeof(startup); PROCESS_INFORMATION child{};
        require(CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &startup, &child), "CONTROLLER_START");
        DWORD wait = WaitForSingleObject(child.hProcess, 15000), exit_code = 99;
        GetExitCodeProcess(child.hProcess, &exit_code);
        if (wait == WAIT_TIMEOUT) TerminateProcess(child.hProcess, 99); // Only this fixture's own child.
        CloseHandle(child.hThread); CloseHandle(child.hProcess);
        require(wait == WAIT_OBJECT_0 && exit_code == 0, "CONTROLLER_FAILED");
        require(wait_for([&] { return count() == iteration + 1; }), "DISCONNECT_CLEANUP_TIMEOUT");
        require(reason() == (abrupt ? ControllerExited : ClosedNormally), "CLOSE_REASON");
    }
    std::cout << "{\"fixture_only\":true,\"sessions\":6,\"normal_close\":3,\"abrupt_disconnect\":3,"
                 "\"target_owned_scheduling\":true,\"reopen\":true,\"idempotent_enable_disable\":true,\"copied_events\":true}\n";
    return 0;
}
int wmain(int argc, wchar_t** argv) {
    try {
        if (argc == 6 && std::wstring(argv[1]) == L"--controller")
            return controller(std::stoul(argv[2]), std::stoul(argv[3]), std::stoull(argv[4]), std::wstring(argv[5]) == L"1");
        require(argc == 2 && std::wstring(argv[1]) == L"--self-test", "USAGE --self-test");
        return self_test();
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
