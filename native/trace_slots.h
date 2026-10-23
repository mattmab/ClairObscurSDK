#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <array>
#include <atomic>
#include <utility>

namespace e33_trace {
using Entry = void (__fastcall*)(void*, void*, void*);
using Post = void (*)(void*, void*, void*, void*);

// One permanent pool per runtime module. A published thunk is never reassigned:
// an engine caller can hold its address indefinitely after compare/exchange.
// Caller validates engine slot lifetime and installs/removes on the game thread.
// Post must only perform bounded copying; it runs under the storage lock and
// must not invoke engine functions, Python, or these registration methods.
template<size_t Capacity = 128, size_t ActiveLimit = 16>
class TraceSlots {
    struct Slot {
        std::atomic<Entry> original{nullptr};
        void* volatile* address = nullptr;
        Post post = nullptr;
        void* context = nullptr;
        bool before = false;
    };
    inline static std::array<Slot, Capacity> slots_{};
    inline static SRWLOCK lock_ = SRWLOCK_INIT;
    inline static size_t used_ = 0;
    inline static bool terminal_ = false;
    struct Guard {
        Guard() { AcquireSRWLockExclusive(&lock_); }
        ~Guard() { ReleaseSRWLockExclusive(&lock_); }
    };
    template<size_t Index>
    static void __fastcall invoke(void* object, void* frame, void* result) {
        auto& slot = slots_[Index];
        bool has_post;
        { Guard guard;
          has_post = slot.post != nullptr && !slot.before;
          if (slot.post && slot.before) slot.post(slot.context, object, frame, result);
        }
        // Immutable, release-published before the thunk becomes reachable.
        slot.original.load(std::memory_order_acquire)(object, frame, result);
        if (has_post) {
            Guard guard;
            if (slot.post) slot.post(slot.context, object, frame, result);
        }
    }
    template<size_t... I>
    static constexpr auto entries(std::index_sequence<I...>) {
        return std::array<Entry, Capacity>{&invoke<I>...};
    }
    inline static constexpr auto entries_ = entries(std::make_index_sequence<Capacity>{});
public:
    static bool observes_entry(void* volatile* address) {
        Guard guard;
        for (size_t i=0;i<used_;++i)
            if (slots_[i].address == address && slots_[i].post && slots_[i].before) return true;
        return false;
    }
    static void observe_entry(void* volatile* address, void* object, void* frame, void* result) {
        Guard guard;
        for (size_t i=0;i<used_;++i) {
            auto& slot=slots_[i];
            if (slot.address == address && slot.post && slot.before) {
                slot.post(slot.context, object, frame, result); return;
            }
        }
    }
    // An observation-only PRE registration is dispatched by the shared
    // Blueprint opcode route. It leaves UFunction::Func unchanged, so typed
    // SDK calls keep their ordinary entry/schema validation and dispatch.
    static size_t install(void* volatile* address, Entry expected, Post post, void* context, bool before = false, bool replace_entry = true) {
        if (!address || !expected || !post || (reinterpret_cast<uintptr_t>(address) & 7)) return 0;
        if (!replace_entry && !before) return 0;
        Guard guard;
        if (terminal_) return 0;
        size_t active = 0;
        for (size_t i = 0; i < used_; ++i) {
            if (expected == entries_[i]) return 0;
            if (slots_[i].post) {
                ++active;
                if (slots_[i].address == address) return 0;
            }
        }
        if (used_ == Capacity || active >= ActiveLimit) return 0;
        const auto index = used_++;
        auto& slot = slots_[index];
        HMODULE pinned = nullptr;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                               reinterpret_cast<LPCWSTR>(entries_[index]), &pinned)) return 0;
        slot.original.store(expected, std::memory_order_release);
        slot.address = address; slot.post = post; slot.context = context; slot.before = before;
        if (InterlockedCompareExchangePointer(address, replace_entry ? reinterpret_cast<void*>(entries_[index]) : reinterpret_cast<void*>(expected),
                reinterpret_cast<void*>(expected)) != reinterpret_cast<void*>(expected)) {
            slot.post = nullptr; slot.context = nullptr;
            return 0;
        }
        return index + 1;
    }
    static bool remove(size_t handle) {
        Guard guard;
        if (!handle || handle > used_) return false;
        auto& slot = slots_[handle - 1];
        if (!slot.address) return false;
        auto original_entry = reinterpret_cast<void*>(slot.original.load(std::memory_order_acquire));
        auto thunk = reinterpret_cast<void*>(entries_[handle - 1]);
        // Detach storage even if another owner replaced the function entry.
        slot.post = nullptr; slot.context = nullptr;
        auto previous = InterlockedCompareExchangePointer(slot.address, original_entry, thunk);
        return previous == thunk || previous == original_entry;
    }
    static bool matches(size_t handle, void* volatile* address, Entry expected, Entry current) {
        Guard guard;
        if (!handle || handle > used_) return false;
        const auto& slot = slots_[handle - 1];
        return slot.post && slot.address == address &&
            slot.original.load(std::memory_order_acquire) == expected && entries_[handle - 1] == current;
    }
    static bool detach(size_t handle) {
        Guard guard;
        if (!handle || handle > used_) return false;
        auto& slot = slots_[handle - 1];
        slot.post = nullptr; slot.context = nullptr;
        // The function or entry storage may already be gone. Never touch it.
        return true;
    }
    static void detach_storage() {
        Guard guard;
        terminal_ = true;
        for (size_t i = 0; i < used_; ++i) {
            slots_[i].post = nullptr; slots_[i].context = nullptr;
        }
        // No engine addresses dereferenced during terminal lifetime loss.
    }
};
}
