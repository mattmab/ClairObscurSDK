#include "trace_registration.h"
#include <cassert>
#include <cstdio>
#include <thread>

using namespace e33_trace;
using Pool = TraceSlots<16, 4>;
using Owner = Registration<Pool, 4>;
static void __fastcall original(void*, void*, void* result) { *static_cast<uint8_t*>(result) = 73; }
static void __fastcall third_party(void*, void*, void*) {}
static bool collect(void* context, void*, void*, void* result, Identity& object, Copy& copied) {
    ++*static_cast<unsigned*>(context);
    object = {1, 2, 3}; copied.size = 1; copied.bytes[0] = *static_cast<uint8_t*>(result); return true;
}
int main() {
    const auto thread = GetCurrentThreadId();
    unsigned collected = 0; uint8_t result = 0; Event event{};
    alignas(8) void* volatile entry = reinterpret_cast<void*>(&original);
    {
        Owner owner;
        assert(owner.open(&entry, original, {1, 1}, thread, 10000, 1, collect, &collected));
        auto thunk = reinterpret_cast<Entry>(entry);
        std::thread foreign([&] {
            uint8_t value{}; thunk(nullptr, nullptr, &value); assert(value == 73);
            assert(owner.stop(true) == Cleanup::wrong_thread);
        }); foreign.join();
        assert(collected == 0);
        thunk(nullptr, nullptr, &result);
        assert(collected == 1 && owner.status(GetTickCount64()).state == State::capped);
        thunk(nullptr, nullptr, &result); assert(collected == 1);
        assert(owner.maintain(true, GetTickCount64()) == Cleanup::restored);
        assert(entry == reinterpret_cast<void*>(&original));
        assert(owner.pop({1, 1}, event) && event.value.bytes[0] == 73);
        assert(owner.close(true) == Cleanup::restored);
        thunk(nullptr, nullptr, &result); assert(collected == 1);
        assert(!owner.open(&entry, original, {1, 2}, thread, 10000, 1, collect, &collected));
    }
    {
        Owner owner;
        assert(owner.open(&entry, original, {2, 1}, thread, 10000, 10, collect, &collected));
        assert(owner.maintain(true, GetTickCount64() + 10000) == Cleanup::restored);
        assert(owner.status(GetTickCount64()).state == State::expired);
    }
    {
        Owner owner;
        assert(owner.open(&entry, original, {3, 1}, thread, 10000, 10, collect, &collected));
        auto thunk = reinterpret_cast<Entry>(entry);
        entry = reinterpret_cast<void*>(&third_party);
        assert(owner.stop(true) == Cleanup::conflict);
        assert(entry == reinterpret_cast<void*>(&third_party));
        thunk(nullptr, nullptr, &result); assert(collected == 1);
    }
    entry = reinterpret_cast<void*>(&original);
    Entry late{};
    {
        Owner owner;
        assert(owner.open(&entry, original, {4, 1}, thread, 10000, 10, collect, &collected));
        late = reinterpret_cast<Entry>(entry);
        // Explicit lifetime-loss detachment does not dereference the entry.
        assert(owner.close(false) == Cleanup::storage_lost);
        assert(reinterpret_cast<Entry>(entry) == late);
    }
    late(nullptr, nullptr, &result); assert(collected == 1 && result == 73);
    entry = reinterpret_cast<void*>(&original);
    {
        Owner owner;
        assert(owner.open(&entry, original, {5, 1}, thread, 10000, 10, collect, &collected));
        late = reinterpret_cast<Entry>(entry);
        // Destructor fallback detaches context without assuming entry lifetime.
    }
    late(nullptr, nullptr, &result); assert(collected == 1 && result == 73);
    {
        auto* page = static_cast<void* volatile*>(VirtualAlloc(nullptr, 4096,
            MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE));
        assert(page); *page = reinterpret_cast<void*>(&original);
        Owner owner;
        assert(owner.open(page, original, {6, 1}, thread, 10000, 10, collect, &collected));
        late = reinterpret_cast<Entry>(*page);
        DWORD previous{};
        assert(VirtualProtect(const_cast<void**>(page), 4096, PAGE_NOACCESS, &previous));
        assert(owner.close(false) == Cleanup::storage_lost);
        assert(VirtualFree(const_cast<void**>(page), 0, MEM_RELEASE));
        late(nullptr, nullptr, &result); assert(collected == 1 && result == 73);
    }
    entry = reinterpret_cast<void*>(&original);
    {
        Owner owner;
        auto failing = [](void*, void*, void*, void*, Identity&, Copy&) -> bool { throw 1; };
        assert(owner.open(&entry, original, {7, 1}, thread, 10000, 10, failing, nullptr));
        reinterpret_cast<Entry>(entry)(nullptr, nullptr, &result);
        assert(result == 73 && owner.rejected() == 1);
        assert(!owner.pop({7, 1}, event));
        assert(owner.close(true) == Cleanup::restored);
    }
    std::puts("Trace ownership: caps/expiry, GT stop, drain retention, conflict and late-call detachment passed.");
}
