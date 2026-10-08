#include "scheduling_protocol.h"
#include "fixed_invocation.h"
#include "console_construction.h"

extern "C" __declspec(dllexport) LRESULT CALLBACK ResearchScheduleHook(int code, WPARAM removed, LPARAM data) {
    if (code == HC_ACTION && removed == PM_REMOVE && data) {
        auto* message = reinterpret_cast<MSG*>(data);
        static const UINT request_message = RegisterWindowMessageW(kScheduleMessage);
        if (request_message && !message->hwnd && message->message == request_message) {
            wchar_t name[96];
            mapping_name(name, static_cast<DWORD>(message->lParam), message->wParam);
            HANDLE mapping = OpenFileMappingW(FILE_MAP_READ | FILE_MAP_WRITE, FALSE, name);
            if (mapping) {
                auto* packet = static_cast<SchedulePacket*>(MapViewOfFile(mapping, FILE_MAP_READ | FILE_MAP_WRITE, 0, 0, sizeof(SchedulePacket)));
                if (packet) {
                    if (packet->magic == kScheduleMagic && packet->version == 1 &&
                        packet->nonce == message->wParam && packet->target_pid == GetCurrentProcessId() &&
                        packet->target_tid == GetCurrentThreadId() &&
                        InterlockedCompareExchange(&packet->state, kRunning, kRequested) == kRequested) {
                        packet->observed_pid = GetCurrentProcessId();
                        packet->observed_tid = GetCurrentThreadId();
                        packet->error = 0; packet->result = 0;
                        if (packet->action == 0) packet->result = 19 + 23;
                        else if (packet->action == 1) packet->error = invoke_fixed_guarded(packet);
                        else if (packet->action == 2) packet->error = construct_console_guarded(packet);
                        else packet->error = 1;
                        InterlockedIncrement(&packet->callbacks);
                        // Consume only a validated request belonging to this protocol.
                        message->message = WM_NULL; message->wParam = 0; message->lParam = 0;
                        InterlockedExchange(&packet->state, kComplete);
                    }
                    UnmapViewOfFile(packet);
                }
                CloseHandle(mapping);
            }
        }
    }
    return CallNextHookEx(nullptr, code, removed, data);
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(instance);
    return TRUE;
}
