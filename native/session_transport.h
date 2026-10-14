#pragma once
#include "session_protocol.h"
#include <new>

// Backend functions execute only on the target message-pump thread.
uint32_t backend_open(SessionPacket*);
uint32_t backend_command(SessionPacket*);
uint32_t backend_close();
bool backend_shutting_down();
void backend_message(MSG*);
#ifdef E33_MESH_SESSION
bool backend_mesh_wake_needed();
#endif
#ifdef E33_VIEWER_MENU_SESSION
uint64_t backend_menu_frame();
#endif
extern "C" __declspec(dllexport) LRESULT CALLBACK SessionScheduleHook(int, WPARAM, LPARAM);

namespace session_transport {
struct Watch {
    HANDLE owner = nullptr, stop = nullptr;
    DWORD target_thread = 0;
    volatile LONG refs = 1, disconnected = 0;
#ifdef E33_MESH_SESSION
    HANDLE animation_changed = nullptr;
    volatile LONG animation_active = 0, wake_pending = 0;
    WPARAM wake_nonce = 0;
#endif
};
static SessionPacket* packet = nullptr;
static HANDLE mapping = nullptr;
static HHOOK owned_hook = nullptr;
static Watch* watch = nullptr;
static DWORD controller = 0, target_thread = 0;
static uint64_t nonce = 0;
#ifdef E33_VIEWER_MENU_SESSION
static uint64_t menu_frame=0,menu_started=0;
static UINT_PTR menu_timer=0;
static void cancel_menu_tick() {
    if(menu_timer)KillTimer(nullptr,menu_timer);
    menu_timer=0;menu_frame=menu_started=0;
}
#endif
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
#ifdef E33_MESH_SESSION
        if (value->animation_changed) CloseHandle(value->animation_changed);
#endif
        delete value;
    }
}
static DWORD WINAPI watch_owner(void* argument) {
    auto* value = static_cast<Watch*>(argument);
#ifdef E33_MESH_SESSION
    HANDLE waits[] = {value->stop, value->owner, value->animation_changed};
    for (;;) {
        const bool active=InterlockedCompareExchange(&value->animation_active,0,0)!=0;
        const auto result=WaitForMultipleObjects(3,waits,FALSE,active?4:INFINITE);
        if(result==WAIT_OBJECT_0 || result==WAIT_FAILED)break;
        if(result==WAIT_OBJECT_0+1) {
            InterlockedExchange(&value->disconnected,1);
            PostThreadMessageW(value->target_thread,WM_NULL,0,0);break;
        }
        // This worker only wakes the existing GT dispatch. It never reads UE
        // objects, evaluates a pose, or uploads geometry. At most one wake is
        // queued; a stalled/loading game cannot accumulate a message backlog.
        if(result==WAIT_TIMEOUT && InterlockedCompareExchange(&value->animation_active,0,0) &&
           InterlockedCompareExchange(&value->wake_pending,1,0)==0) {
            if(!PostThreadMessageW(value->target_thread,WM_NULL,value->wake_nonce,0))
                InterlockedExchange(&value->wake_pending,0);
        }
    }
#else
    HANDLE waits[] = {value->stop, value->owner};
    if (WaitForMultipleObjects(2, waits, FALSE, INFINITE) == WAIT_OBJECT_0 + 1) {
        InterlockedExchange(&value->disconnected, 1);
        PostThreadMessageW(value->target_thread, WM_NULL, 0, 0);
    }
#endif
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
#ifdef E33_VIEWER_MENU_SESSION
    cancel_menu_tick();
#endif
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
#ifdef E33_MESH_SESSION
    watch->animation_changed=CreateEventW(nullptr,FALSE,FALSE,nullptr);
    watch->wake_nonce=static_cast<WPARAM>(nonce);
    if(!watch->animation_changed){request.error=82;close(BackendFailure);return true;}
#endif
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
#ifdef E33_MESH_SESSION
        if(watch && message->message==WM_NULL && message->wParam==watch->wake_nonce && !message->lParam)
            InterlockedExchange(&watch->wake_pending,0);
#endif
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
#ifdef E33_VIEWER_MENU_SESSION
        if(packet && menu_timer) {
            const auto frame=backend_menu_frame();
            if(!frame || frame<menu_frame || GetTickCount64()-menu_started>2000 || frame!=menu_frame) {
                const bool valid=frame>menu_frame && GetTickCount64()-menu_started<=2000;
                cancel_menu_tick();
                packet->request.error=valid ? guarded_command(packet):90;
                InterlockedIncrement(&packet->request.callbacks);
                InterlockedExchange(&packet->request.state,kComplete);
            }
        }
#endif
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
#ifdef E33_VIEWER_MENU_SESSION
                        if(request.action==SessionMenu && (packet->menu.operation==6 || packet->menu.operation==3)) {
                            menu_frame=backend_menu_frame();menu_started=GetTickCount64();
                            if(menu_frame)menu_timer=SetTimer(nullptr,0,USER_TIMER_MINIMUM,nullptr);
                        }
                        if(!menu_timer) {
#endif
                        request.error = guarded_command(packet);
                        InterlockedIncrement(&request.callbacks);
                        InterlockedExchange(&request.state, kComplete);
#ifdef E33_VIEWER_MENU_SESSION
                        }
#endif
                    }
                }
            }
            if (consumed) { message->message = WM_NULL; message->wParam = 0; message->lParam = 0; }
        }
    }
#ifdef E33_MESH_SESSION
    if(packet && watch) {
        const LONG active=backend_mesh_wake_needed()?1:0;
        if(InterlockedExchange(&watch->animation_active,active)!=active)SetEvent(watch->animation_changed);
    }
#endif
    return CallNextHookEx(nullptr, code, removed, data);
}
