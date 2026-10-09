#include "scheduling_protocol.h"
#include "fixed_invocation.h"
#include "reflected_invocation.h"
#include "trace_slots.h"
#include <cassert>
#include <cstdio>

using Pool = e33_trace::TraceSlots<4, 1>;
static size_t trace_handle{};
static void __fastcall original(void*, void*, void*) {}
static volatile unsigned other_calls{};
static void __fastcall other(void*, void*, void*) { ++other_calls; }
static void post(void*, void*, void*, void*) {}
static bool owned(uint64_t address, uint64_t expected, uint64_t current) {
    return Pool::matches(trace_handle, reinterpret_cast<void* volatile*>(address),
        reinterpret_cast<e33_trace::Entry>(expected), reinterpret_cast<e33_trace::Entry>(current));
}
int main() {
    alignas(8) void* volatile entry = reinterpret_cast<void*>(&original);
    const auto address = reinterpret_cast<uint64_t>(&entry);
    const auto expected = reinterpret_cast<uint64_t>(&original);
    CallEntryValidation validator{owned};
    assert(call_entry_matches(address, expected, nullptr));
    trace_handle = Pool::install(&entry, original, post, nullptr); assert(trace_handle);
    const auto stale = entry;
    assert(!call_entry_matches(address, expected, nullptr));
    assert(call_entry_matches(address, expected, &validator));
    assert(!call_entry_matches(address, reinterpret_cast<uint64_t>(&other), &validator));
    alignas(8) void* volatile different_entry = entry;
    assert(!call_entry_matches(reinterpret_cast<uint64_t>(&different_entry), expected, &validator));
    entry = reinterpret_cast<void*>(&other);
    assert(!call_entry_matches(address, expected, &validator));
    assert(!Pool::remove(trace_handle));
    entry = stale;
    assert(!call_entry_matches(address, expected, &validator));
    entry = reinterpret_cast<void*>(&original);
    assert(call_entry_matches(address, expected, nullptr));
    std::puts("Invocation entry guard: exact active thunk accepted, foreign/stale/original mismatches rejected.");
}
