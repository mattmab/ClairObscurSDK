#pragma once
#include "scheduling_protocol.h"
#include "observer_fixture_protocol.h"
#ifdef E33_REFLECTED_SESSION
#include "invocation_protocol.h"
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v6";
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v5";
#endif
enum : DWORD { SessionOpen=10, SessionEnable, SessionDisable, SessionInvoke, SessionDrain, SessionClose, SessionPing,
               SessionConsoleAttach, SessionConsoleDetach, SessionConsoleStatus,
               SessionConsolePoll, SessionConsoleExecute, SessionConsolePrint, SessionConsoleNames, SessionConsoleKey };
#ifdef E33_REFLECTED_SESSION
constexpr DWORD SessionReflectedInvoke=100;
#endif
enum : LONG { ClosedNormally=1, ControllerExited=2, BackendFailure=3, TargetShuttingDown=4 };
struct SessionPacket {
    SchedulePacket request;
    ObserverBuffer events;
    DWORD controller;
    volatile LONG closed;
    LONG close_reason;
    wchar_t console_text[32769];
    uint32_t console_dropped;
#ifdef E33_REFLECTED_SESSION
    CallPacket call;
#endif
};
inline void session_mapping_name(wchar_t (&name)[96], DWORD controller, uint64_t nonce) {
#ifdef E33_REFLECTED_SESSION
    swprintf_s(name, L"Local\\E33Session6_%lu_%016llx", controller, nonce);
#else
    swprintf_s(name, L"Local\\E33Session5_%lu_%016llx", controller, nonce);
#endif
}
