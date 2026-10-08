#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cstdint>
#include <cwchar>

// Fixed-size research protocol: ping or one validated reflected getter.
// No arbitrary pointers, function addresses, or executable command strings.
constexpr uint32_t kScheduleMagic = 0x45333353;
constexpr wchar_t kScheduleMessage[] = L"E33SDK.Research.SchedulingFixture.v1";
constexpr wchar_t kBarrierMessage[] = L"E33SDK.Research.FixtureBarrier.v1";
enum : LONG { kIdle = 0, kRequested = 1, kRunning = 2, kComplete = 3 };
struct SchedulePacket {
    uint32_t magic, version;
    uint64_t nonce;
    DWORD target_pid, target_tid;
    volatile LONG ready, state, callbacks, barriers;
    DWORD observed_pid, observed_tid;
    uint64_t result;
    DWORD action;
    int32_t object_index, object_serial, function_index, function_serial;
    uint32_t error;
};
static_assert(sizeof(SchedulePacket) == 80);
inline void mapping_name(wchar_t (&name)[96], DWORD controller, uint64_t nonce) {
    swprintf_s(name, L"Local\\E33SchedulingFixture_%lu_%016llx", controller, nonce);
}
