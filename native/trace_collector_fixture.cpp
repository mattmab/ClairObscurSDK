#include "scheduling_protocol.h"
#include "fixed_invocation.h"
#include "target_trace_collector.h"
#include "trace_registration.h"
#include <array>
#include <cassert>
#include <cstdio>
#include <thread>

static void __fastcall fixture_original(void*, void*, void* result) {
    *static_cast<uint32_t*>(result) = 57;
}

int main() {
    // Synthetic registry layout, not an imported engine or a live game test.
    auto* region = static_cast<uint8_t*>(VirtualAlloc(nullptr, 0x9400000, MEM_RESERVE, PAGE_READWRITE));
    assert(region);
    for (size_t offset : {size_t(0x9272000), size_t(0x934e000), size_t(0x9361000)})
        assert(VirtualAlloc(region + offset, 4096, MEM_COMMIT, PAGE_READWRITE));
    auto put = [](void* target, auto value) { std::memcpy(target, &value, sizeof(value)); };
    const auto base = reinterpret_cast<uint64_t>(region);
    alignas(8) std::array<std::array<uint8_t, 256>, 3> objects{};
    std::array<std::array<uint8_t, 24>, 3> slots{};
    uint64_t chunk = reinterpret_cast<uint64_t>(slots.data());
    put(region + 0x9361b70, reinterpret_cast<uint64_t>(&chunk));
    put(region + 0x9361b84, int32_t(3)); put(region + 0x9361b8c, int32_t(1));
    put(region + 0x9272d30, GetCurrentThreadId());
    for (int32_t i = 0; i < 3; ++i) {
        put(objects[i].data() + 0xc, i);
        put(slots[i].data(), reinterpret_cast<uint64_t>(objects[i].data()));
        put(slots[i].data() + 0x10, i + 10);
    }
    const auto function = reinterpret_cast<uint64_t>(objects[0].data());
    const auto owner = reinterpret_cast<uint64_t>(objects[1].data());
    const auto object = reinterpret_cast<uint64_t>(objects[2].data());
    put(objects[0].data() + 0x20, owner); put(objects[2].data() + 0x10, owner);
    TargetTraceContext context{};
    context.base = base; context.function = {0, 10, function}; context.owner = {1, 11, owner};
    context.pid = GetCurrentProcessId(); context.thread = GetCurrentThreadId();
    context.plan.count = 1; context.plan.extent = 4;
    context.plan.fields[0] = {e33_trace::StorageKind::result, 0, 4, 0, 0, 4};
    std::array<uint8_t, 0xa0> frame{};
    put(frame.data() + 0x90, function);
    uint32_t result = 42;
    e33_trace::Identity identity{}; e33_trace::Copy copied{};
    auto collect = [&] { return target_trace_collect(&context, objects[2].data(), frame.data(),
                                                     &result, identity, copied); };
    assert(collect());
    assert(identity.pid == GetCurrentProcessId() && identity.index == 2 && identity.serial == 12);
    assert(copied.size == 4 && copied.bytes[0] == 42);
    auto reject = [&] {
        assert(!collect()); assert(identity.index == -1 && copied.size == 0);
        for (auto byte : copied.bytes) assert(!byte);
    };
    context.filtered = true; context.filter = {2, 12, object}; assert(collect());
    context.filter.serial = 13; reject(); context.filter.serial = 12;
    put(slots[0].data() + 0x10, int32_t(99)); reject(); put(slots[0].data() + 0x10, int32_t(10));
    put(slots[2].data(), uint64_t(0)); reject(); put(slots[2].data(), object);
    for (size_t offset : {size_t(0x9272cfc), size_t(0x934e968), size_t(0x9272cea)}) {
        region[offset] = 1; reject(); region[offset] = 0;
    }
    put(objects[2].data() + 8, uint32_t(0x40000000)); reject(); put(objects[2].data() + 8, uint32_t(0));
    put(frame.data() + 0x20, uint64_t(1)); reject(); put(frame.data() + 0x20, uint64_t(0));
    put(frame.data() + 0x90, function + 1); reject(); put(frame.data() + 0x90, function);
    std::thread foreign([&] { reject(); }); foreign.join();
    auto* forbidden = VirtualAlloc(nullptr, 4096, MEM_RESERVE | MEM_COMMIT, PAGE_NOACCESS);
    assert(forbidden);
    assert(!target_trace_collect(&context, objects[2].data(), forbidden, &result, identity, copied));
    assert(copied.size == 0 && identity.index == -1);
    assert(!target_trace_collect(&context, objects[2].data(), frame.data(), forbidden, identity, copied));
    assert(copied.size == 0 && identity.index == -1);
    assert(VirtualFree(forbidden, 0, MEM_RELEASE));
    assert(collect());
    {
        using Pool = e33_trace::TraceSlots<2, 1>;
        e33_trace::Registration<Pool, 2> registration;
        auto* entry = reinterpret_cast<void* volatile*>(objects[0].data() + 0xd8);
        *entry = reinterpret_cast<void*>(&fixture_original);
        assert(registration.open(entry, fixture_original, {1, 2}, GetCurrentThreadId(),
                                  10000, 2, target_trace_collect, &context));
        auto thunk = reinterpret_cast<e33_trace::Entry>(*entry);
        thunk(objects[2].data(), frame.data(), &result);
        e33_trace::Event event{};
        assert(registration.pop({1, 2}, event));
        assert(event.object.index == 2 && event.value.size == 4 && event.value.bytes[0] == 57);
        assert(registration.close(true) == e33_trace::Cleanup::restored);
        assert(*entry == reinterpret_cast<void*>(&fixture_original));
        thunk(objects[2].data(), frame.data(), &result);
        assert(!registration.pop({1, 2}, event));
    }
    assert(VirtualFree(region, 0, MEM_RELEASE));
    reject(); // Guard catches the now-unmapped registry read.
    std::puts("Target collector: registry identity, filter, GT/GC gates, scalar result and SEH faults passed.");
}
