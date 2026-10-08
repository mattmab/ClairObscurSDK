#pragma once
#include "scheduling_protocol.h"
#include "observer_fixture_protocol.h"

constexpr wchar_t kObserverMessage[] = L"E33SDK.Research.FixedObserver.v1";
constexpr wchar_t kObserverDll[] = L"fixed_observer_v1.dll";
struct FixedObserverPacket {
    SchedulePacket schedule;
    ObserverBuffer events;
    uint32_t restored, after_remove_count;
};
