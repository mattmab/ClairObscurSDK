#pragma once
#if defined(E33_TEXT_SESSION) && !defined(E33_POD_SESSION)
#error Text session requires the complete v11 capability chain
#endif
#if defined(E33_POD_SESSION) && (!defined(E33_REFLECTED_SESSION) || !defined(E33_ASSIGNMENT_SESSION) || !defined(E33_STABLE_SESSION) || !defined(E33_RETAINED_SESSION) || !defined(E33_LEASE_SESSION))
#error POD session requires the complete v10 capability chain
#endif
#include "scheduling_protocol.h"
#include "observer_fixture_protocol.h"
#ifdef E33_REFLECTED_SESSION
#include "invocation_protocol.h"
#ifdef E33_LEASE_SESSION
#include "lease_protocol.h"
#ifdef E33_RETAINED_SESSION
#include "retained_call_protocol.h"
#ifdef E33_STABLE_SESSION
#ifdef E33_ASSIGNMENT_SESSION
#include "assignment_protocol.h"
#ifdef E33_POD_SESSION
#ifdef E33_TEXT_SESSION
#include "text_call_protocol.h"
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v12";
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v11";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v10";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v9";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v8";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v7";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v6";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v5";
#endif
enum : DWORD { SessionOpen=10, SessionEnable, SessionDisable, SessionInvoke, SessionDrain, SessionClose, SessionPing,
               SessionConsoleAttach, SessionConsoleDetach, SessionConsoleStatus,
               SessionConsolePoll, SessionConsoleExecute, SessionConsolePrint, SessionConsoleNames, SessionConsoleKey };
#ifdef E33_REFLECTED_SESSION
constexpr DWORD SessionReflectedInvoke=100;
#endif
#ifdef E33_LEASE_SESSION
constexpr DWORD SessionLeaseAcquire=101, SessionLeaseRelease=102, SessionLeaseStatus=103;
constexpr uint32_t kSessionCloseDeferred=407;
#endif
#ifdef E33_RETAINED_SESSION
constexpr DWORD SessionRetainedInvoke=104;
#endif
#ifdef E33_ASSIGNMENT_SESSION
constexpr DWORD SessionObjectAssign=105;
#endif
#ifdef E33_TEXT_SESSION
constexpr DWORD SessionTextInvoke=106;
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
#ifdef E33_LEASE_SESSION
    LeasePacket lease;
#endif
#ifdef E33_RETAINED_SESSION
    RetainedCallPacket retained;
#endif
#ifdef E33_ASSIGNMENT_SESSION
    AssignmentPacket assignment;
#endif
#ifdef E33_TEXT_SESSION
    TextCallPacket text;
#endif
};
inline void session_mapping_name(wchar_t (&name)[96], DWORD controller, uint64_t nonce) {
#ifdef E33_TEXT_SESSION
    swprintf_s(name, L"Local\\E33Session12_%lu_%016llx", controller, nonce);
#elif defined(E33_ASSIGNMENT_SESSION)
    swprintf_s(name, L"Local\\E33Session10_%lu_%016llx", controller, nonce);
#elif defined(E33_STABLE_SESSION)
    swprintf_s(name, L"Local\\E33Session9_%lu_%016llx", controller, nonce);
#elif defined(E33_RETAINED_SESSION)
    swprintf_s(name, L"Local\\E33Session8_%lu_%016llx", controller, nonce);
#elif defined(E33_LEASE_SESSION)
    swprintf_s(name, L"Local\\E33Session7_%lu_%016llx", controller, nonce);
#elif defined(E33_REFLECTED_SESSION)
    swprintf_s(name, L"Local\\E33Session6_%lu_%016llx", controller, nonce);
#else
    swprintf_s(name, L"Local\\E33Session5_%lu_%016llx", controller, nonce);
#endif
}
