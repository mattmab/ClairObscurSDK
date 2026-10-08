#include "fixed_observer_protocol.h"
#include "fixed_invocation.h"
#include "observer_core.h"

static uint32_t observer_experiment(FixedObserverPacket* packet) {
    auto* request = &packet->schedule;
    // A full validation and real baseline invocation must succeed before any
    // UFunction entry is changed. Uses the same proven getter as invoke_proof.
    uint32_t failure = invoke_fixed_guarded(request);
    if (failure) return failure;
    uint64_t base = reinterpret_cast<uint64_t>(GetModuleHandleW(nullptr));
    uint64_t object = fixed_slot(base, request->object_index, request->object_serial);
    uint64_t function = fixed_slot(base, request->function_index, request->function_serial);
    if (!object || !function) return 30;
    auto* slot = reinterpret_cast<void* volatile*>(function + 0xd8);
    auto expected = reinterpret_cast<ObserverEntry>(base + 0x333be80);
    auto dispatch = reinterpret_cast<ObserverEntry>(base + 0x332bb90);
    if (!install_observer(slot, expected, &packet->events)) return 31;
    __try {
        for (int i = 0; i < 2; ++i) {
            uint8_t result = 0xcc;
            dispatch(reinterpret_cast<void*>(object), reinterpret_cast<void*>(function), &result);
            if (result != request->result) { failure = 32; break; }
        }
    } __finally {
        packet->restored = remove_observer() && local_read<uint64_t>(function + 0xd8) == base + 0x333be80;
    }
    if (!packet->restored) return 33;
    if (failure) return failure;
    // A real call after removal must still work and produce no observer event.
    failure = invoke_fixed_guarded(request);
    packet->after_remove_count = packet->events.count;
    if (failure) return failure;
    if (packet->events.count != 2 || packet->events.dropped != 0) return 34;
    for (uint32_t i = 0; i < 2; ++i) {
        const auto& event = packet->events.records[i];
        if (event.object != object || event.thread != GetCurrentThreadId() || event.result != request->result) return 35;
    }
    return 0;
}
static uint32_t guarded_observer(FixedObserverPacket* packet) {
    __try { return observer_experiment(packet); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 39; }
}

extern "C" __declspec(dllexport) LRESULT CALLBACK ResearchObserverSchedule(int code, WPARAM removed, LPARAM data) {
    if (code == HC_ACTION && removed == PM_REMOVE && data) {
        auto* message = reinterpret_cast<MSG*>(data);
        static const UINT request_message = RegisterWindowMessageW(kObserverMessage);
        if (request_message && !message->hwnd && message->message == request_message) {
            wchar_t name[96]; mapping_name(name, static_cast<DWORD>(message->lParam), message->wParam);
            HANDLE mapping = OpenFileMappingW(FILE_MAP_READ | FILE_MAP_WRITE, FALSE, name);
            if (mapping) {
                auto* packet = static_cast<FixedObserverPacket*>(MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(FixedObserverPacket)));
                if (packet) {
                    auto& request = packet->schedule;
                    if (request.magic == kScheduleMagic && request.version == 1 && request.action == 2 &&
                        request.nonce == message->wParam && request.target_pid == GetCurrentProcessId() &&
                        request.target_tid == GetCurrentThreadId() &&
                        InterlockedCompareExchange(&request.state, kRunning, kRequested) == kRequested) {
                        request.observed_pid = GetCurrentProcessId(); request.observed_tid = GetCurrentThreadId();
                        request.error = guarded_observer(packet);
                        InterlockedIncrement(&request.callbacks);
                        message->message = WM_NULL; message->wParam = 0; message->lParam = 0;
                        InterlockedExchange(&request.state, kComplete);
                    }
                    UnmapViewOfFile(packet);
                }
                CloseHandle(mapping);
            }
        }
    }
    return CallNextHookEx(nullptr, code, removed, data);
}
