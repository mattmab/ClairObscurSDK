#pragma once
#include "picto_progression_protocol.h"
#ifdef E33_GROWING_LEASE_SESSION
#include "lease_policy_protocol.h"
#endif
#ifdef E33_CINEMATIC_WIDGET_SESSION
#include "cinematic_widget_protocol.h"
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
#include "cinematic_sound_event_protocol.h"
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
#include "music_audio_owner_protocol.h"
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
#include "scoped_assignment_protocol.h"
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
#include "sequence_owner_protocol.h"
#endif
#ifdef E33_MEDIA_SESSION
#include "media_owner_protocol.h"
#endif
#ifdef E33_PAUSE_MENU_SESSION
#include "pause_attachment_protocol.h"
#endif
#ifdef E33_KEYBIND_SESSION
#ifdef E33_UI_BATCH_SESSION
#include "ui_batch_protocol.h"
#endif
#ifndef E33_TRACE_SESSION
#error Keybind runtime requires the complete v18 capability chain
#endif
#include "keybind_protocol.h"
constexpr uint32_t SessionKeybind = 111;
#endif
#ifdef E33_TRACE_SESSION
#ifndef E33_MULTI_BUTTON_SESSION
#error Trace runtime requires the complete v17 capability chain
#endif
#include "trace_protocol.h"
constexpr uint32_t SessionTrace = 110;
#endif
#ifdef E33_MULTI_BUTTON_SESSION
#ifndef E33_BUTTON_ACTION_SESSION
#error Multi-button runtime requires the v16 capability chain
#endif
#include "multi_button_protocol.h"
constexpr uint32_t SessionMultiButton=109;
#endif
#if defined(E33_BUTTON_ACTION_SESSION) && !defined(E33_BUTTON_REFERENCE_SESSION)
#error Button action candidate requires retained button ownership
#endif
#ifdef E33_BUTTON_ACTION_SESSION
#include "button_action_protocol.h"
constexpr uint32_t SessionButtonAction=108;
#endif
#if defined(E33_BUTTON_REFERENCE_SESSION) && !defined(E33_MENU_SESSION)
#error Button reference candidate requires the menu session
#endif
#ifdef E33_MENU_SESSION
#ifndef E33_ENUM_SESSION
#error Menu candidate requires the complete enum session feature set
#endif
#include "menu_protocol.h"
constexpr uint32_t SessionMenu=107;
#endif
#if defined(E33_ENUM_SESSION) && !defined(E33_TEXT_SESSION)
#error Enum session requires the complete v12 capability chain
#endif
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
#ifdef E33_ENUM_SESSION
#ifdef E33_MENU_SESSION
#ifdef E33_BUTTON_REFERENCE_SESSION
#ifdef E33_BUTTON_ACTION_SESSION
#ifdef E33_MULTI_BUTTON_SESSION
#ifdef E33_TRACE_SESSION
#ifdef E33_KEYBIND_SESSION
#ifdef E33_UI_BATCH_SESSION
#ifdef E33_PAUSE_MENU_SESSION
#ifdef E33_VECTOR_SESSION
#ifdef E33_LAYOUT_BATCH_SESSION
#ifdef E33_BLUEPRINT_TRACE_SESSION
#ifdef E33_BLUEPRINT_DIRECT_SESSION
#if defined(E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION)
#if defined(E33_COVERAGE_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v58mediaaudio";
#elif defined(E33_FRAME_TIME_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v54frametime";
#elif defined(E33_TITLE_MENU_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v53titlemenu";
#elif defined(E33_AUDIO_COMPLETION_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v52audiocompletion";
#elif defined(E33_AUDIO_IDENTITY_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v51audioidentity";
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v50audiocleanupdiagnostics";
#endif
#elif defined(E33_WIDGET_ANIMATION_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v49animationdrain";
#elif defined(E33_WIDGET_DIAGNOSTICS_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v48widgetdiagnostics";
#elif defined(E33_NUMBERED_CALLBACK_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v47numberedcallback";
#elif defined(E33_NUMBERED_WIDGET_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v46numberedwidget";
#elif defined(E33_TRACK_DIAGNOSTIC_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v45trackdiagnostic";
#elif defined(E33_GROWING_LEASE_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v44leasegrowth";
#elif defined(E33_WIDGET_CAPACITY_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v43widgetcapacity";
#elif defined(E33_CINEMATIC_WIDGET_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v42widgetownership";
#elif defined(E33_ORIGINAL_AUDIO_PAUSE_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v41originalaudiopause";
#elif defined(E33_CINEMATIC_SOUND_EVENT_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v40cinematicsoundevent";
#elif defined(E33_OWNED_SOUND_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v39ownedsound";
#elif defined(E33_MUSIC_AUDIO_GUARD_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v38musicaudioguard";
#elif defined(E33_MUSIC_AUDIO_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v37musicaudio";
#elif defined(E33_AUDIO_ISOLATION_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v36audioisolation";
#elif defined(E33_SEQUENCE_PLAYER_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v35sequenceplayer";
#elif defined(E33_SEQUENCE_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v34sequence";
#elif defined(E33_MEDIA_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v33media";
#elif defined(E33_STRING_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v31string";
#elif defined(E33_MENU_ESCAPE_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v30menuescape";
#elif defined(E33_MENU_DIAGNOSTIC_SESSION)
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v29menudiag";
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v26statistics";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v25statistics";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v24layout";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v23pausevector";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v22pause";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v20ui";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v19";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v18";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v17";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v16";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v15";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v14";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v13";
#endif
#else
constexpr wchar_t kSessionMessage[] = L"E33SDK.Session.v12";
#endif
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
#ifdef E33_GROWING_LEASE_SESSION
    uint64_t lease_owner;
#endif
    ObserverBuffer events;
    DWORD controller;
    volatile LONG closed;
    LONG close_reason;
    wchar_t console_text[32769];
    uint32_t console_dropped;
#ifdef E33_KEYBIND_SESSION
    e33_keys::Packet keys;
#endif
#ifdef E33_TRACE_SESSION
    e33_trace::Packet trace;
#endif
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
#ifdef E33_MENU_SESSION
    MenuPacket menu;
#endif
#ifdef E33_BUTTON_ACTION_SESSION
    ButtonActionPacket button_action;
#ifdef E33_MULTI_BUTTON_SESSION
    MultiButtonPacket multi_button;
#endif
#endif
};
inline void session_mapping_name(wchar_t (&name)[96], DWORD controller, uint64_t nonce) {
#ifdef E33_UI_BATCH_SESSION
#ifdef E33_PAUSE_MENU_SESSION
#ifdef E33_VECTOR_SESSION
#ifdef E33_LAYOUT_BATCH_SESSION
#ifdef E33_BLUEPRINT_TRACE_SESSION
#ifdef E33_BLUEPRINT_DIRECT_SESSION
#ifdef E33_MENU_DIAGNOSTIC_SESSION
    swprintf_s(name, L"Local\\E33Session29menudiag_%lu_%016llx", controller, nonce);
#else
    swprintf_s(name, L"Local\\E33Session26statistics_%lu_%016llx", controller, nonce);
#endif
#else
    swprintf_s(name, L"Local\\E33Session25statistics_%lu_%016llx", controller, nonce);
#endif
#else
    swprintf_s(name, L"Local\\E33Session24layout_%lu_%016llx", controller, nonce);
#endif
#else
    swprintf_s(name, L"Local\\E33Session23pausevector_%lu_%016llx", controller, nonce);
#endif
#else
    swprintf_s(name, L"Local\\E33Session22pause_%lu_%016llx", controller, nonce);
#endif
#else
    swprintf_s(name, L"Local\\E33Session20ui_%lu_%016llx", controller, nonce);
#endif
#elif defined(E33_KEYBIND_SESSION)
    swprintf_s(name, L"Local\\E33Session19_%lu_%016llx", controller, nonce);
#elif defined(E33_TRACE_SESSION)
    swprintf_s(name, L"Local\\E33Session18_%lu_%016llx", controller, nonce);
#elif defined(E33_BUTTON_ACTION_SESSION)
#ifdef E33_MULTI_BUTTON_SESSION
    swprintf_s(name, L"Local\\E33Session17_%lu_%016llx", controller, nonce);
#else
    swprintf_s(name, L"Local\\E33Session16_%lu_%016llx", controller, nonce);
#endif
#elif defined(E33_BUTTON_REFERENCE_SESSION)
    swprintf_s(name, L"Local\\E33Session15_%lu_%016llx", controller, nonce);
#elif defined(E33_MENU_SESSION)
    swprintf_s(name, L"Local\\E33Session14_%lu_%016llx", controller, nonce);
#elif defined(E33_ENUM_SESSION)
    swprintf_s(name, L"Local\\E33Session13_%lu_%016llx", controller, nonce);
#elif defined(E33_TEXT_SESSION)
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

