#include "session_protocol.h"
#include "observer_core.h"
static ObserverBuffer native_events{};
static DWORD fixture_thread = 0;
static bool enabled = false;
alignas(8) static void* volatile fixture_slot = nullptr;
static void __fastcall fixture_target(void*, void*, void* output) { *static_cast<uint8_t*>(output) = 42; }
bool backend_shutting_down() { return false; }
#if E33_RUNTIME_CINEMATIC_VERSION>=316
static bool fixture_command_active=false,fixture_nested_poll=false;
void backend_message(MSG*) {if(fixture_command_active)fixture_nested_poll=true;}
#else
void backend_message(MSG*) {}
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=314
bool backend_loading_handoff_active(){return enabled;}
uint64_t backend_loading_handoff_frame(){return GetTickCount64()/16+1;}
#endif
uint32_t backend_open(SessionPacket*) {
    fixture_thread = GetCurrentThreadId();
    if (!fixture_slot) InterlockedExchangePointer(&fixture_slot, reinterpret_cast<void*>(&fixture_target));
    return 0;
}
uint32_t backend_command(SessionPacket* packet) {
    if (GetCurrentThreadId() != fixture_thread) return 70;
    switch (packet->request.action) {
    case SessionEnable:
        if (enabled) return 0;
        native_events = {};
        if (!install_observer(&fixture_slot, fixture_target, &native_events)) return 71;
        enabled = true; return 0;
    case SessionDisable:
        if (!remove_observer()) return 72;
        enabled = false; return 0;
    case SessionInvoke: {
#if E33_RUNTIME_CINEMATIC_VERSION>=316
        fixture_command_active=true;
        if(!PostThreadMessageW(fixture_thread,WM_APP+91,0,0))return 75;
        MSG nested{};
        const bool pumped=PeekMessageW(&nested,nullptr,WM_APP+91,WM_APP+91,PM_REMOVE)!=FALSE;
        fixture_command_active=false;
        if(!pumped||fixture_nested_poll)return 76;
#endif
        uint8_t result = 0;
        auto fn = reinterpret_cast<ObserverEntry>(InterlockedCompareExchangePointer(&fixture_slot, nullptr, nullptr));
        fn(reinterpret_cast<void*>(uint64_t(123)), nullptr, &result);
        packet->request.result = result; return 0;
    }
    case SessionDrain: drain_observer(&packet->events); return 0;
    case SessionPing: packet->request.result = enabled ? 1 : 0; return 0;
    default: return 73;
    }
}
uint32_t backend_close() {
    if (!remove_observer()) return 74;
    enabled = false; return 0;
}
#include "session_transport.h"
extern "C" __declspec(dllexport) LONG FixtureCloseCount() {
    return InterlockedCompareExchange(&session_transport::completed_closes, 0, 0);
}
extern "C" __declspec(dllexport) LONG FixtureCloseReason() {
    return InterlockedCompareExchange(&session_transport::last_close_reason, 0, 0);
}
