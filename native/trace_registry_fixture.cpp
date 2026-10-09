#include "trace_registry.h"
#include <cassert>
#include <cstdio>
#include <thread>

using namespace e33_trace;
static void __fastcall original(void*, void*, void* result) { *static_cast<uint8_t*>(result) = 42; }
alignas(8) static void* volatile engine_entry = reinterpret_cast<void*>(&original);
struct Ops {
    struct Context { void* volatile* entry{}; };
    inline static Storage gate = Storage::ready;
    static uint32_t prepare(uint64_t, CallPacket&, const CallIdentity*, Context& context) {
        context.entry = &engine_entry; return 0;
    }
    static Storage storage(const Context&) { return gate; }
    static void* volatile* entry(const Context& context) { return context.entry; }
    static Entry expected(uint64_t, const CallPacket&) { return original; }
    static bool collect(void*, void*, void*, void* result, Identity& identity, Copy& copied) {
        identity = {1, 2, 3}; copied.size = 1; copied.bytes[0] = *static_cast<uint8_t*>(result); return true;
    }
};
static Packet request(Operation operation, uint64_t registration = 0) {
    Packet packet{};
    packet.version = 1; packet.operation = static_cast<uint32_t>(operation);
    packet.owner = 7; packet.registration = registration; packet.filter.index = -1;
    if (operation == Operation::start) {
        packet.duration_ms = 10000; packet.limit = 2;
        packet.schema.version = 1; packet.schema.target = {1, 0, 0x10000};
        packet.schema.function = {2, 0, 0x20000}; packet.schema.return_offset = 65535;
        packet.schema.function_flags = 0x400; packet.schema.entry_rva = 0x1234;
    }
    return packet;
}
int main() {
    Registry<Ops, TraceSlots<16, 4>> registry;
    assert(registry.begin(1, 2)); assert(!registry.begin(1, 2));
    auto start = request(Operation::start); registry.command(start);
    assert(!start.error && start.registration && start.state == 1);
    auto thunk = reinterpret_cast<Entry>(engine_entry);
    const auto entry_address = reinterpret_cast<uint64_t>(&engine_entry);
    const auto original_address = reinterpret_cast<uint64_t>(&original);
    const auto thunk_address = reinterpret_cast<uint64_t>(thunk);
    assert(registry.allows_entry(entry_address, original_address, thunk_address));
    assert(!registry.allows_entry(entry_address + 8, original_address, thunk_address));
    assert(!registry.allows_entry(entry_address, original_address + 1, thunk_address));
    assert(!registry.allows_entry(entry_address, original_address, original_address));
    Ops::gate = Storage::deferred;
    assert(!registry.allows_entry(entry_address, original_address, thunk_address));
    Ops::gate = Storage::ready;
    auto duplicate = request(Operation::start); registry.command(duplicate);
    assert(duplicate.error == 936 && duplicate.registration == 0);
    uint8_t result{};
    thunk(nullptr, nullptr, &result); thunk(nullptr, nullptr, &result);
    registry.maintain(); assert(engine_entry == reinterpret_cast<void*>(&original));
    assert(!registry.allows_entry(entry_address, original_address, thunk_address));
    auto other = request(Operation::drain, start.registration); other.owner = 8;
    registry.command(other); assert(other.error == 933 && !other.count);
    auto drain = request(Operation::drain, start.registration); registry.command(drain);
    assert(!drain.error && drain.count == 2 && drain.observed == 2 && drain.state == 4 && drain.cleanup == 1);
    assert(drain.events[0].bytes[0] == 42 && drain.events[1].sequence == 2);
    auto forget = request(Operation::forget, start.registration); registry.command(forget);
    assert(!forget.error && forget.state == 5);
    auto stale = request(Operation::status, start.registration); registry.command(stale); assert(stale.error == 933);
    auto second = request(Operation::start); registry.command(second);
    assert(!second.error && second.registration > start.registration);
    Ops::gate = Storage::deferred;
    auto stop = request(Operation::stop, second.registration); registry.command(stop); assert(stop.error == 934);
    assert(registry.close(false) == 934);
    Ops::gate = Storage::ready;
    assert(registry.close(false) == 0 && engine_entry == reinterpret_cast<void*>(&original));
    assert(registry.begin(1, 3));
    auto fresh = request(Operation::start); registry.command(fresh);
    assert(!fresh.error && fresh.registration > second.registration);
    thunk = reinterpret_cast<Entry>(engine_entry);
    std::thread foreign([&] { assert(registry.close(false) == 931); }); foreign.join();
    assert(registry.close(true) == 0);
    thunk(nullptr, nullptr, &result); assert(result == 42);
    auto closed = request(Operation::status, fresh.registration); registry.command(closed); assert(closed.error == 931);
    std::puts("Trace registry: ownership, duplicate rejection, cap/drain, forget, deferred close and session revocation passed.");
}
