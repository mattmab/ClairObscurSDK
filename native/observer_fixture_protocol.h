#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cstdint>

using ObserverEntry = void (__fastcall*)(void*, void*, void*);
struct ObserverRecord { uint64_t object; DWORD thread; uint8_t result; };
struct ObserverBuffer {
    uint32_t count = 0, dropped = 0;
    ObserverRecord records[64]{};
};
using InstallObserver = BOOL (*)(void* volatile*, ObserverEntry, ObserverBuffer*);
using RemoveObserver = BOOL (*)();
