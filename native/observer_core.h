#pragma once
#include "observer_fixture_protocol.h"

// Shared observer mechanics; callers must validate their specific target.
// Once published, this code remains mapped until process exit, including for
// callers which fetched the observer pointer before removal but enter later.
static SRWLOCK state_lock = SRWLOCK_INIT;
static ObserverEntry original = nullptr;
static void* volatile* owned_slot = nullptr;
static ObserverBuffer* events = nullptr;
static thread_local unsigned depth = 0;

static void __fastcall observe(void* object, void* frame, void* result) {
    ++depth;
    original(object, frame, result);
    if (depth == 1) {
        AcquireSRWLockExclusive(&state_lock);
        if (events) {
            if (events->count < 64) {
                auto& record = events->records[events->count++];
                record = {reinterpret_cast<uint64_t>(object), GetCurrentThreadId(),
                          *static_cast<uint8_t*>(result)};
            } else ++events->dropped;
        }
        ReleaseSRWLockExclusive(&state_lock);
    }
    --depth;
}

inline BOOL install_observer(
    void* volatile* slot, ObserverEntry expected, ObserverBuffer* buffer) {
    if (!slot || !expected || !buffer || (reinterpret_cast<uintptr_t>(slot) & 7)) return FALSE;
    AcquireSRWLockExclusive(&state_lock);
    BOOL ok = FALSE;
    // Keep original immutable forever once any thread might have obtained us.
    if (!events && (!original || original == expected) && (!owned_slot || owned_slot == slot)) {
        HMODULE pinned = nullptr;
        if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                              reinterpret_cast<LPCWSTR>(&observe), &pinned)) {
            if (!original) original = expected;
            owned_slot = slot; events = buffer;
            if (InterlockedCompareExchangePointer(slot, reinterpret_cast<void*>(&observe),
                                                  reinterpret_cast<void*>(expected)) == reinterpret_cast<void*>(expected)) ok = TRUE;
            else events = nullptr;
        }
    }
    ReleaseSRWLockExclusive(&state_lock);
    return ok;
}

inline BOOL remove_observer() {
    AcquireSRWLockExclusive(&state_lock);
    BOOL ok = TRUE;
    if (events) {
        void* previous = InterlockedCompareExchangePointer(owned_slot, reinterpret_cast<void*>(original),
                                                           reinterpret_cast<void*>(&observe));
        ok = previous == reinterpret_cast<void*>(&observe) || previous == reinterpret_cast<void*>(original);
        // Even on a slot conflict detach event storage. Never overwrite another owner.
        events = nullptr;
    }
    ReleaseSRWLockExclusive(&state_lock);
    return ok;
}
