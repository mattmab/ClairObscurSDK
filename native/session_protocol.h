#pragma once
#include "scheduling_protocol.h"
#include "observer_fixture_protocol.h"
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v2";
enum : DWORD { SessionOpen=10, SessionEnable, SessionDisable, SessionInvoke, SessionDrain, SessionClose, SessionPing,
               SessionConsoleAttach, SessionConsoleDetach, SessionConsoleStatus };
enum : LONG { ClosedNormally=1, ControllerExited=2, BackendFailure=3, TargetShuttingDown=4 };
struct SessionPacket {
    SchedulePacket request;
    ObserverBuffer events;
    DWORD controller;
    volatile LONG closed;
    LONG close_reason;
};
inline void session_mapping_name(wchar_t (&name)[96], DWORD controller, uint64_t nonce) {
    swprintf_s(name, L"Local\\E33Session2_%lu_%016llx", controller, nonce);
}
