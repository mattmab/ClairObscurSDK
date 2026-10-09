#include "trace_slots.h"
#include <cassert>
#include <condition_variable>
#include <mutex>
#include <thread>
#include <cstdio>

using Pool = e33_trace::TraceSlots<8, 2>;
static std::atomic<unsigned> originals{0}, posts{0};
static std::mutex gate;
static std::condition_variable changed;
static bool entered = false, released = false;
static void __fastcall first(void*, void*, void* result) { ++originals; *static_cast<int*>(result) = 17; }
static void __fastcall second(void*, void*, void* result) { ++originals; *static_cast<int*>(result) = 29; }
static void __fastcall blocking(void*, void*, void* result) {
    std::unique_lock<std::mutex> lock(gate);
    entered = true; changed.notify_all();
    changed.wait(lock, [] { return released; });
    *static_cast<int*>(result) = 31;
}
static void post(void*, void*, void*, void*) { ++posts; }
int main() {
    alignas(8) void* volatile a = reinterpret_cast<void*>(&first);
    alignas(8) void* volatile b = reinterpret_cast<void*>(&second);
    alignas(8) void* volatile c = reinterpret_cast<void*>(&blocking);
    auto one = Pool::install(&a, first, post, nullptr);
    auto two = Pool::install(&b, second, post, nullptr);
    assert(one && two && !Pool::install(&c, blocking, post, nullptr));
    auto stale = reinterpret_cast<e33_trace::Entry>(a);
    int result = 0; stale(nullptr, nullptr, &result);
    assert(result == 17 && posts == 1);
    assert(Pool::remove(one));
    auto replacement = Pool::install(&a, first, post, nullptr);
    assert(replacement && replacement != one);
    stale(nullptr, nullptr, &result);
    assert(result == 17 && posts == 1); // Old address cannot reach new storage.
    reinterpret_cast<e33_trace::Entry>(a)(nullptr, nullptr, &result);
    assert(posts == 2);
    InterlockedExchangePointer(&b, reinterpret_cast<void*>(&first));
    assert(!Pool::remove(two) && b == reinterpret_cast<void*>(&first));
    assert(Pool::remove(replacement));
    auto pending = Pool::install(&c, blocking, post, nullptr);
    assert(pending);
    auto pending_entry = reinterpret_cast<e33_trace::Entry>(c);
    std::thread worker([&] { pending_entry(nullptr, nullptr, &result); });
    { std::unique_lock<std::mutex> lock(gate); changed.wait(lock, [] { return entered; }); }
    assert(Pool::remove(pending)); // Original executes outside storage lock.
    { std::lock_guard<std::mutex> lock(gate); released = true; changed.notify_all(); }
    worker.join();
    assert(result == 31 && posts == 2);
    auto terminal = Pool::install(&a, first, post, nullptr);
    assert(terminal);
    auto terminal_entry = reinterpret_cast<e33_trace::Entry>(a);
    assert(Pool::remove(terminal));
    unsigned remaining = 0;
    while (auto handle = Pool::install(&a, first, post, nullptr)) {
        ++remaining; assert(Pool::remove(handle));
    }
    assert(remaining == 3); // Eight lifetime slots, no reuse after publication.
    Pool::detach_storage();
    terminal_entry(nullptr, nullptr, &result);
    assert(result == 17 && posts == 2);
    using FreshPool = e33_trace::TraceSlots<3, 1>;
    auto attached = FreshPool::install(&a, first, post, nullptr);
    assert(attached);
    auto detached_entry = reinterpret_cast<e33_trace::Entry>(a);
    FreshPool::detach_storage();
    detached_entry(nullptr, nullptr, &result);
    assert(result == 17 && posts == 2);
    assert(FreshPool::remove(attached));
    assert(!FreshPool::install(&a, first, post, nullptr)); // Terminal, not exhausted.
    std::puts("Trace slots: immutable forwarding, late entry, in-flight removal, conflicts, detach and exhaustion passed.");
}
