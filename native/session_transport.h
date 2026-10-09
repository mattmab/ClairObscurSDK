#pragma once
#include "session_protocol.h"
#include <new>

// Backend functions execute only on the target message-pump thread.
uint32_t backend_open(SessionPacket*);
uint32_t backend_command(SessionPacket*);
uint32_t backend_close();
bool backend_shutting_down();
void backend_message(MSG*);
extern "C" __declspec(dllexport) LRESULT CALLBACK SessionScheduleHook(int, WPARAM, LPARAM);

namespace session_transport {
struct Watch {
    HANDLE owner = nullptr, stop = nullptr;
    DWORD target_thread = 0;
    volatile LONG refs = 1, disconnected = 0;
};
static SessionPacket* packet = nullptr;
static HANDLE mapping = nullptr;
static HHOOK owned_hook = nullptr;
static Watch* watch = nullptr;
static DWORD controller = 0, target_thread = 0;
static uint64_t nonce = 0;
static volatile LONG completed_closes = 0;
static volatile LONG last_close_reason = 0;
static volatile LONG owner_tid = 0;
#ifdef E33_LEASE_SESSION
static LONG pending_close_reason=0;
#endif
inline void release(Watch* value) {
    if (InterlockedDecrement(&value->refs) == 0) {
        if (value->owner) CloseHandle(value->owner);
        if (value->stop) CloseHandle(value->stop);
        delete value;
    }
}
static DWORD WINAPI watch_owner(void* argument) {
    auto* value = static_cast<Watch*>(argument);
    HANDLE waits[] = {value->stop, value->owner};
    if (WaitForMultipleObjects(2, waits, FALSE, INFINITE) == WAIT_OBJECT_0 + 1) {
        InterlockedExchange(&value->disconnected, 1);
        PostThreadMessageW(value->target_thread, WM_NULL, 0, 0);
    }
    release(value);
    return 0;
}
static uint32_t guarded_close() {
    __try { return backend_close(); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 89; }
}
static void close(LONG reason) {
    auto* closing = packet;
    if (!closing) return;
    uint32_t error = reason == BackendFailure ? closing->request.error : 0;
    uint32_t cleanup_error = guarded_close();
#ifdef E33_LEASE_SESSION
    if(cleanup_error==kSessionCloseDeferred) { pending_close_reason=reason; return; }
    pending_close_reason=0;
#endif
    if (cleanup_error) error = cleanup_error;
    if (owned_hook) { if (!UnhookWindowsHookEx(owned_hook) && !error) error = 88; owned_hook = nullptr; }
    if (watch) { SetEvent(watch->stop); release(watch); watch = nullptr; }
    closing->request.error = error;
    closing->close_reason = reason;
    InterlockedExchange(&closing->closed, 1);
    InterlockedExchange(&closing->request.state, kComplete);
    InterlockedExchange(&last_close_reason, reason);
    InterlockedIncrement(&completed_closes);
    packet = nullptr; controller = target_thread = 0; nonce = 0;
    UnmapViewOfFile(closing); CloseHandle(mapping); mapping = nullptr;
    InterlockedExchange(&owner_tid, 0);
}
static uint32_t guarded_open(SessionPacket* value) {
    __try { return backend_open(value); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 87; }
}
static uint32_t guarded_command(SessionPacket* value) {
    __try { return backend_command(value); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 86; }
}
static void guarded_message(MSG* value) {
    __try { backend_message(value); }
    __except(EXCEPTION_EXECUTE_HANDLER) { close(BackendFailure); }
}
static bool open(MSG* message) {
    wchar_t name[96];
    DWORD requested_controller = static_cast<DWORD>(message->lParam);
    session_mapping_name(name, requested_controller, message->wParam);
    HANDLE candidate_mapping = OpenFileMappingW(FILE_MAP_ALL_ACCESS, FALSE, name);
    if (!candidate_mapping) return false;
    auto* candidate = static_cast<SessionPacket*>(MapViewOfFile(candidate_mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SessionPacket)));
    if (!candidate) { CloseHandle(candidate_mapping); return false; }
    auto& request = candidate->request;
    bool valid = request.magic == kScheduleMagic && request.version == 1 && request.action == SessionOpen &&
        candidate->controller == requested_controller && request.nonce == message->wParam &&
        request.target_pid == GetCurrentProcessId() && request.target_tid == GetCurrentThreadId() &&
        InterlockedCompareExchange(&request.state, kRunning, kRequested) == kRequested;
    if (!valid) { UnmapViewOfFile(candidate); CloseHandle(candidate_mapping); return false; }
    if (InterlockedCompareExchange(&owner_tid, static_cast<LONG>(GetCurrentThreadId()), 0) != 0) {
        request.error = 84; InterlockedExchange(&request.state, kComplete);
        UnmapViewOfFile(candidate); CloseHandle(candidate_mapping); return true;
    }
    packet = candidate; mapping = candidate_mapping; controller = requested_controller;
    target_thread = GetCurrentThreadId(); nonce = message->wParam;
    request.observed_pid = GetCurrentProcessId(); request.observed_tid = target_thread;
    request.error = guarded_open(candidate);
    if (request.error) {
        close(BackendFailure);
        return true;
    }
    HMODULE module = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                           reinterpret_cast<LPCWSTR>(&SessionScheduleHook), &module)) {
        request.error = 80; close(BackendFailure); return true;
    }
    owned_hook = SetWindowsHookExW(WH_GETMESSAGE, SessionScheduleHook, module, target_thread);
    watch = new (std::nothrow) Watch;
    if (!owned_hook || !watch) { request.error = 81; close(BackendFailure); return true; }
    watch->target_thread = target_thread;
    watch->owner = OpenProcess(SYNCHRONIZE, FALSE, controller);
    watch->stop = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    if (!watch->owner || !watch->stop) { request.error = 82; close(BackendFailure); return true; }
    InterlockedIncrement(&watch->refs);
    HANDLE worker = CreateThread(nullptr, 0, watch_owner, watch, 0, nullptr);
    if (!worker) { release(watch); request.error = 83; close(BackendFailure); return true; }
    CloseHandle(worker);
    InterlockedIncrement(&request.callbacks);
    InterlockedExchange(&request.state, kComplete);
    return true;
}
}

extern "C" __declspec(dllexport) LRESULT CALLBACK SessionScheduleHook(int code, WPARAM removed, LPARAM data) {
    using namespace session_transport;
    LONG owner = InterlockedCompareExchange(&owner_tid, 0, 0);
    if (owner && static_cast<DWORD>(owner) != GetCurrentThreadId()) return CallNextHookEx(nullptr, code, removed, data);
    if (code == HC_ACTION && removed == PM_REMOVE && data) {
        auto* message = reinterpret_cast<MSG*>(data);
        static const UINT request_message = RegisterWindowMessageW(kSessionMessage);
#ifdef E33_LEASE_SESSION
        if(packet && pending_close_reason) close(pending_close_reason);
#endif
        // A watcher only requests cleanup; it never touches backend/engine state.
        if (packet && GetCurrentThreadId() == target_thread && watch &&
            InterlockedCompareExchange(&watch->disconnected, 0, 0)) close(ControllerExited);
        if (packet && GetCurrentThreadId() == target_thread && backend_shutting_down()) close(TargetShuttingDown);
        if (packet && GetCurrentThreadId() == target_thread
#ifdef E33_LEASE_SESSION
            && !pending_close_reason
#endif
            ) guarded_message(message);
        if (request_message && !message->hwnd && message->message == request_message) {
            bool consumed = false;
            if (!packet) consumed = open(message);
            else if (GetCurrentThreadId() == target_thread && message->wParam == nonce &&
#ifdef E33_LEASE_SESSION
                     !pending_close_reason &&
#endif
                     static_cast<DWORD>(message->lParam) == controller) {
                auto& request = packet->request;
                if (InterlockedCompareExchange(&request.state, kRunning, kRequested) == kRequested) {
                    consumed = true;
                    if (request.action == SessionClose) close(ClosedNormally);
                    else {
                        request.error = guarded_command(packet);
                        InterlockedIncrement(&request.callbacks);
                        InterlockedExchange(&request.state, kComplete);
                    }
                }
            }
            if (consumed) { message->message = WM_NULL; message->wParam = 0; message->lParam = 0; }
        }
    }
    return CallNextHookEx(nullptr, code, removed, data);
}
